import os
import uuid
import base64
import asyncio
import json
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue

from backend.database import get_db
from backend.models import DocumentModel, ClauseModel, AuditLogModel, UserModel
from backend.api.v1.auth import get_current_user
from backend.services.llm_config import get_llm_config
from backend.document_pipeline.reporting.docx_remediation_service import DocxRemediationService
from backend.document_pipeline.reporting.report_service import ReportService

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(REDIS_URL)
redis_async = Redis.from_url(REDIS_URL, decode_responses=True)
task_queue = Queue('document_processing', connection=redis_conn)

router = APIRouter()
docx_remediation_service = DocxRemediationService()
report_service = ReportService()

UPLOAD_DIR = "backend/storage/uploads"
REPORTS_DIR = "backend/storage/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

MAX_FILE_SIZE = 15 * 1024 * 1024

def sanitize_text(val: str) -> str:
    return val.replace('\x00', '') if isinstance(val, str) else val

# ---------------------------------------------------------
# REAL-TIME WEBSOCKET STREAMING GATEWAY
# ---------------------------------------------------------
@router.websocket("/ws/{job_id}")
async def websocket_pipeline_endpoint(websocket: WebSocket, job_id: str):
    """Streams live Redis pipeline events directly to PipelineVisualizer."""
    await websocket.accept()
    pubsub = redis_async.pubsub()
    await asyncio.to_thread(pubsub.subscribe, f"pipeline:{job_id}")

    initial_state = await asyncio.to_thread(redis_async.get, f"pipeline_state:{job_id}")
    if initial_state:
        try:
            await websocket.send_text(initial_state)
        except Exception:
            pass

    try:
        while True:
            message = await asyncio.to_thread(pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("data"):
                data = message["data"]
                try:
                    await websocket.send_text(data)
                except Exception:
                    break
                try:
                    parsed = json.loads(data)
                    if parsed.get("step") in ["COMPLETED", "FAILED"]:
                        break
                except Exception:
                    pass
            await asyncio.sleep(0.5)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        try:
            await asyncio.to_thread(pubsub.unsubscribe, f"pipeline:{job_id}")
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass

# ---------------------------------------------------------
# DOCUMENT UPLOAD & INGESTION
# ---------------------------------------------------------
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
    active_model = active_config.get("llm_model", "gemini-3.5-flash")

    job_id = str(uuid.uuid4())
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds maximum 15MB limit.")

    clean_filename = sanitize_text(file.filename)
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
        api_key_masked=f"...{active_key[-4:]}" if len(active_key) > 4 else "...N/A",
        ocr_confidence=0.0,
        pages=0,
        entities_detected=0,
    )
    db.add(db_doc)
    db.commit()

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

    return {
        "message": "Document uploaded successfully. Processing in V2 background pipeline.",
        "job_id": job_id,
        "status": "processing"
    }

@router.get("/status/{job_id}")
async def get_document_status(job_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    is_complete = getattr(doc, "ocr_confidence", 0.0) > 0.0
    return {
        "job_id": doc.job_id,
        "status": "completed" if is_complete else "processing",
        "filename": doc.filename,
        "ocr_confidence": doc.ocr_confidence
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
            "llm_model_used": doc.llm_model_used,
            "api_key_masked": doc.api_key_masked,
            "ragas_scores": {
                "faithfulness": doc.ragas_faithfulness or 0.0,
                "answer_relevancy": doc.ragas_answer_relevancy or 0.0,
                "context_precision": doc.ragas_context_precision or 0.0,
                "context_recall": doc.ragas_context_recall or 0.0
            }
        }
        for doc in documents
    ]

@router.get("/{document_id}")
async def get_document_details(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    clauses = db.query(ClauseModel).filter(ClauseModel.job_id == document_id).all()

    page_breakdown = []
    try:
        cached_pages = redis_async.get(f"pipeline_pages:{document_id}")
        if cached_pages:
            page_breakdown = json.loads(cached_pages)
    except Exception:
        page_breakdown = []

    return {
        "document": {
            "job_id": doc.job_id,
            "filename": doc.filename,
            "business_unit": doc.business_unit,
            "category": doc.document_category,
            "created_at": str(doc.created_at),
            "ocr_confidence": doc.ocr_confidence,
            "pages_processed": doc.pages,
            "llm_model_used": doc.llm_model_used,
            "api_key_masked": doc.api_key_masked,
            "ragas_faithfulness": doc.ragas_faithfulness,
            "ragas_answer_relevancy": doc.ragas_answer_relevancy,
            "ragas_context_precision": doc.ragas_context_precision,
            "ragas_context_recall": doc.ragas_context_recall,
            "page_breakdown": page_breakdown
        },
        "clauses": [
            {
                "id": c.id,
                "clause_type": c.clause_type,
                "extracted_text": c.extracted_text,
                "confidence_score": c.confidence_score,
                "risk_level": c.risk_level,
                "risk_rationale": c.risk_rationale,
                "involved_party": c.involved_party,
                "rag_reference_used": c.rag_reference_used,
                "page_reference": str(c.page_reference or "1"),
                "obligation_owner": c.obligation_owner,
                "recommended_action": c.recommended_action,
                "proposed_redline": c.proposed_redline
            }
            for c in clauses
        ]
    }

@router.get("/{job_id}/export-remediation-docx")
async def export_remediation_docx(job_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    clauses = db.query(ClauseModel).filter(ClauseModel.job_id == job_id).all()

    doc_data = {"job_id": doc.job_id, "filename": doc.filename}
    clause_list = [
        {
            "clause_type": c.clause_type,
            "extracted_text": c.extracted_text,
            "risk_level": c.risk_level,
            "risk_rationale": c.risk_rationale,
            "rag_reference_used": c.rag_reference_used or "POL-IND-2026-01",
            "proposed_redline": c.proposed_redline
        }
        for c in clauses
    ]

    safe_filename = sanitize_text(doc.filename).replace(" ", "_")
    docx_path = os.path.join(REPORTS_DIR, f"Schedule_of_Deviations_{safe_filename}.docx")
    docx_remediation_service.generate_schedule_of_deviations(doc_data, clause_list, docx_path)

    return FileResponse(
        docx_path,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=f"Schedule_of_Deviations_{safe_filename}.docx"
    )

@router.get("/{job_id}/export-pdf")
async def export_document_pdf(job_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    clauses = db.query(ClauseModel).filter(ClauseModel.job_id == job_id).all()
    audits = db.query(AuditLogModel).filter(AuditLogModel.job_id == job_id).all()

    doc_data = {
        "job_id": doc.job_id,
        "filename": doc.filename,
        "business_unit": doc.business_unit,
        "ocr_confidence": doc.ocr_confidence,
        "pages": doc.pages
    }
    clause_list = [{"clause_type": c.clause_type, "extracted_text": c.extracted_text, "risk_level": c.risk_level, "risk_rationale": c.risk_rationale} for c in clauses]
    audit_list = [{"reviewer": a.user_email, "action": a.action} for a in audits]

    safe_filename = sanitize_text(doc.filename).replace(" ", "_")
    pdf_path = os.path.join(REPORTS_DIR, f"Audit_Report_{safe_filename}.pdf")
    report_service.generate_compliance_pdf(doc_data, clause_list, audit_list, pdf_path)

    return FileResponse(pdf_path, media_type='application/pdf', filename=f"Audit_Report_{safe_filename}.pdf")