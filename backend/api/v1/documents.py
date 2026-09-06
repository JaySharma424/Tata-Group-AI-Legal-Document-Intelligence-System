from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue
import jwt
import os
import uuid
import datetime
import base64
from typing import Optional

from backend.database import get_db
from backend.models import DocumentModel, ClauseModel, AuditLogModel, UserModel
from backend.api.v1.auth import get_current_user, SECRET_KEY, ALGORITHM
from backend.services.llm_config import get_llm_config
from backend.document_pipeline.reporting.docx_remediation_service import DocxRemediationService
from backend.document_pipeline.reporting.report_service import ReportService

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)
task_queue = Queue('document_processing', connection=redis_conn)

router = APIRouter()
docx_remediation_service = DocxRemediationService()
report_service = ReportService()

UPLOAD_DIR = "backend/storage/uploads"
REPORTS_DIR = "backend/storage/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

def sanitize_text(val: str) -> str:
    if isinstance(val, str):
        return val.replace('\x00', '')
    return val

def mask_key_suffix(key_str: str) -> str:
    if not key_str or len(key_str) < 4:
        return "...N/A"
    return f"...{key_str[-4:]}"

MAX_FILE_SIZE = 10 * 1024 * 1024

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    business_unit: str = Form(...),
    document_category: str = Form(...),
    confidentiality_level: str = Form(...),
    review_priority: str = Form(...),
    document_type: str = Form("Unknown"),
    counterparty: Optional[str] = Form(None),
    jurisdiction: Optional[str] = Form(None),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    active_config = get_llm_config()
    active_key = active_config.get("api_key", "")
    
    if not active_key:
        raise HTTPException(status_code=400, detail="The system is offline because the Administrator has not configured the AI API keys.")

    active_model = active_config.get("llm_model", "gemini-3.5-flash")
    active_key_suffix = mask_key_suffix(active_key)

    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File size exceeds maximum allowed ({MAX_FILE_SIZE // (1024*1024)}MB)")

    clean_filename = sanitize_text(file.filename)
    file_path = os.path.join(upload_dir, f"{job_id}_{clean_filename}")
    with open(file_path, "wb") as f:
        f.write(contents)
        
    encoded_file_data = base64.b64encode(contents).decode('utf-8')

    db_doc = DocumentModel(
        job_id=job_id,
        filename=clean_filename,
        business_unit=sanitize_text(business_unit),
        document_category=sanitize_text(document_category),
        document_type=sanitize_text(document_type),
        counterparty=sanitize_text(counterparty),
        jurisdiction=sanitize_text(jurisdiction),
        confidentiality_level=sanitize_text(confidentiality_level),
        review_priority=sanitize_text(review_priority),
        uploaded_by=current_user.email,
        llm_model_used=active_model,       
        api_key_masked=active_key_suffix,
        ocr_confidence=0.0, 
        pages=0, 
        entities_detected=0, 
    )
    db.add(db_doc)
    db.commit()

    try:
        task_queue.enqueue(
            'backend.document_pipeline.workers.redis_worker.process_document',
            job_id,
            encoded_file_data,
            clean_filename,
            current_user.email,
            current_user.role,
            business_unit,
            job_id=job_id,
            job_timeout='1h'
        )
    except Exception as e:
        print(f"Error dispatching Redis task: {e}")

    return {
        "message": "Document uploaded successfully. Processing in background.",
        "job_id": job_id,
        "status": "processing"
    }

@router.get("/status/{job_id}")
async def get_document_status(job_id: str, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    is_complete = getattr(doc, "ocr_confidence", 0.0) > 0.0

    return {
        "job_id": doc.job_id,
        "status": "completed" if is_complete else "processing",
        "filename": doc.filename
    }

@router.get("/history")
async def get_document_history(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(DocumentModel)
    if current_user.role != "Admin":
        query = query.filter(DocumentModel.uploaded_by == current_user.email)
    
    documents = query.order_by(DocumentModel.created_at.desc()).all()
    return [
        {
            "job_id": doc.job_id,
            "filename": doc.filename,
            "business_unit": doc.business_unit,
            "document_category": doc.document_category,
            "confidentiality_level": doc.confidentiality_level,
            "ocr_confidence": doc.ocr_confidence,
            "pages": doc.pages,
            "entities_detected": doc.entities_detected,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "llm_model_used": getattr(doc, "llm_model_used", "gemini-3.5-flash"),
            "api_key_masked": getattr(doc, "api_key_masked", "...N/A"),
            "ragas_scores": {
                "faithfulness": getattr(doc, "ragas_faithfulness", 0.0),
                "answer_relevancy": getattr(doc, "ragas_answer_relevancy", 0.0),
                "context_precision": getattr(doc, "ragas_context_precision", 0.0),
                "context_recall": getattr(doc, "ragas_context_recall", 0.0)
            }
        }
        for doc in documents
    ]

@router.get("/{document_id}")
async def get_document_details(document_id: str, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        doc = db.query(DocumentModel).filter(DocumentModel.job_id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        clauses = db.query(ClauseModel).filter(ClauseModel.job_id == document_id).all()

        return {
            "document": {
                "job_id": doc.job_id,
                "filename": doc.filename,
                "business_unit": doc.business_unit,
                "category": doc.document_category,
                "created_at": str(doc.created_at),
                "ocr_confidence": doc.ocr_confidence,
                "pages_processed": doc.pages,
                "llm_model_used": getattr(doc, "llm_model_used", "gemini-3.5-flash"), 
                "api_key_masked": getattr(doc, "api_key_masked", "...N/A"),           
                "ragas_faithfulness": getattr(doc, "ragas_faithfulness", 0.0),
                "ragas_answer_relevancy": getattr(doc, "ragas_answer_relevancy", 0.0),
                "ragas_context_precision": getattr(doc, "ragas_context_precision", 0.0),
                "ragas_context_recall": getattr(doc, "ragas_context_recall", 0.0)
            },
            "clauses": [
                {
                    "id": getattr(c, "id", None),
                    "clause_type": getattr(c, "clause_type", "General Clause"),
                    "extracted_text": getattr(c, "extracted_text", ""),
                    "confidence_score": getattr(c, "confidence_score", 0.95),
                    "risk_level": getattr(c, "risk_level", "MEDIUM"),
                    "risk_rationale": getattr(c, "risk_rationale", "Evaluated against compliance rules."),
                    "involved_party": getattr(c, "involved_party", "Both Parties"),
                    "rag_reference_used": (getattr(c, "rag_reference_used", None) or "TAX-1"),
                    "page_reference": getattr(c, "page_reference", "Section 1"),
                    "obligation_owner": getattr(c, "obligation_owner", "Both Parties"),
                    "recommended_action": getattr(c, "recommended_action", "Review"),
                    "proposed_redline": getattr(c, "proposed_redline", None)
                } for c in clauses
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}/export-remediation-docx")
async def export_remediation_docx(job_id: str, token: Optional[str] = Query(None), current_user: Optional[UserModel] = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        if not current_user and token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                email = payload.get("sub")
                current_user = db.query(UserModel).filter(UserModel.email == email).first()
            except Exception:
                pass

        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")
            
        if current_user.role != "Admin" and doc.uploaded_by != current_user.email:
             raise HTTPException(status_code=403, detail="Access denied.")
        
        clauses = db.query(ClauseModel).filter(ClauseModel.job_id == job_id).all()

        doc_data = {
            "job_id": doc.job_id,
            "filename": doc.filename,
        }
        
        clause_list = []
        for c in clauses:
            ref_val = (
                getattr(c, 'rag_reference_used', None) or 
                getattr(c, 'rag_reference', None) or 
                getattr(c, 'policy_citation', None) or 
                getattr(c, 'reference_id', None) or 
                "TAX-1"
            )
            clause_list.append({
                "clause_type": getattr(c, 'clause_type', 'General Provision'),
                "extracted_text": getattr(c, 'extracted_text', ''),
                "risk_level": getattr(c, 'risk_level', 'LOW'),
                "risk_rationale": getattr(c, 'risk_rationale', 'N/A'),
                "rag_reference_used": ref_val,
                "proposed_redline": getattr(c, 'proposed_redline', None)
            })

        base_name = doc.filename
        for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.docx', '.txt']:
            if base_name.lower().endswith(ext):
                base_name = base_name[:-len(ext)]
                break
        
        safe_filename = sanitize_text(base_name).replace(" ", "_")
        docx_path = os.path.join(REPORTS_DIR, f"Schedule_of_Deviations_{safe_filename}.docx")
        
        docx_remediation_service.generate_schedule_of_deviations(doc_data, clause_list, docx_path)

        return FileResponse(
            docx_path, 
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
            filename=f"Schedule_of_Deviations_{safe_filename}.docx"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate remediation report: {str(e)}")

@router.get("/{job_id}/export-pdf")
async def export_document_pdf(job_id: str, token: Optional[str] = Query(None), current_user: Optional[UserModel] = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user and token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            current_user = db.query(UserModel).filter(UserModel.email == email).first()
        except Exception:
            pass

    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if current_user.role != "Admin" and doc.uploaded_by != current_user.email:
         raise HTTPException(status_code=403, detail="Access denied.")
    
    clauses = db.query(ClauseModel).filter(ClauseModel.job_id == job_id).all()
    audits = db.query(AuditLogModel).filter(AuditLogModel.job_id == job_id).all()

    doc_data = {
        "job_id": doc.job_id,
        "filename": doc.filename,
        "business_unit": doc.business_unit,
        "ocr_confidence": doc.ocr_confidence,
        "pages": doc.pages
    }
    
    clause_list = [
        {
            "clause_type": c.clause_type,
            "extracted_text": c.extracted_text,
            "risk_level": c.risk_level,
            "risk_rationale": c.risk_rationale
        } for c in clauses
    ]

    audit_list = [{"reviewer": a.user_email, "action": a.action} for a in audits]

    base_name = doc.filename
    for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.docx', '.txt']:
        if base_name.lower().endswith(ext):
            base_name = base_name[:-len(ext)]
            break
    
    safe_filename = sanitize_text(base_name).replace(" ", "_")
    pdf_path = os.path.join(REPORTS_DIR, f"Audit_Report_{safe_filename}.pdf")
    
    report_service.generate_compliance_pdf(doc_data, clause_list, audit_list, pdf_path)

    return FileResponse(
        pdf_path, 
        media_type='application/pdf', 
        filename=f"Audit_Report_{safe_filename}.pdf"
    )