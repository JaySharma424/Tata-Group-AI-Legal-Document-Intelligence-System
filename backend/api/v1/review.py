import datetime
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Internal Imports
from backend.database import get_db
from backend.models import DocumentModel, ClauseModel, AuditLogModel, UserModel
# IMPORT CENTRALIZED AUTH DEPENDENCY (Fixes the 401 Unauthorized key mismatch)
from backend.api.v1.auth import get_current_user  

router = APIRouter()

# ==================== PYDANTIC SCHEMAS ====================

class ReviewActionRequest(BaseModel):
    job_id: Optional[str] = None
    document_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str  # ACCEPT, REJECT, EDIT, ESCALATE
    comment: Optional[str] = None
    comments: Optional[str] = None
    file_name: Optional[str] = "Analyzed Document"
    edited_clauses: Optional[List[Any]] = None

class AdminActionRequest(BaseModel):
    job_id: str
    action: str  # ACCEPT, REJECT, or MANUAL_REVIEW
    comments: Optional[str] = ""


# ==================== USER REVIEW & HISTORY ROUTES ====================

@router.get("/history")
async def get_review_history(
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Returns review history strictly isolated by the authenticated user's email."""
    try:
        query = db.query(AuditLogModel)
        
        # Multi-Tenant Isolation: Admin sees all records, regular users see only their own
        if current_user.role != "Admin":
            query = query.filter(AuditLogModel.user_email == current_user.email)

        audits = query.order_by(AuditLogModel.timestamp.desc()).limit(50).all()
    except Exception:
        audits = []

    history_list = []
    for idx, a in enumerate(audits, start=1):
        job_id_val = a.job_id or f"job-{idx}"
        doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id_val).first()
        file_name_val = doc.filename if doc else "Analyzed Contract.pdf"
        timestamp_str = a.timestamp.isoformat() if a.timestamp else str(datetime.datetime.utcnow())
        
        history_list.append({
            "id": str(a.id),
            "document_id": job_id_val,
            "file_name": file_name_val,
            "action": a.action.upper(),
            "timestamp": timestamp_str,
            "reviewer_email": a.user_email
        })
        
    return {"history": history_list}


@router.post("/actions")
async def process_review_action(
    payload: ReviewActionRequest, 
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Processes user review actions (ACCEPT, REJECT, EDIT, ESCALATE) and saves to database."""
    target_job_id = payload.job_id or payload.document_id
    if not target_job_id:
        latest_doc = db.query(DocumentModel).order_by(DocumentModel.created_at.desc()).first()
        target_job_id = latest_doc.job_id if latest_doc else f"job-{int(datetime.datetime.utcnow().timestamp())}"
    
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == target_job_id).first()
    if not doc:
        doc = DocumentModel(
            job_id=target_job_id, 
            filename=payload.file_name or "uploaded_contract.pdf", 
            business_unit=current_user.business_unit, 
            document_category="Vendor Agreement", 
            document_type="Master Services Agreement",              
            ocr_confidence=95.0,
            uploaded_by=current_user.email
        )
        db.add(doc)
        db.commit()
    
    action_upper = payload.action.upper()
    if action_upper not in ["ACCEPT", "EDIT", "REJECT", "ESCALATE"]:
        action_upper = "ACCEPT"

    comment_text = payload.comment or payload.comments or f"Document reviewed with status: {action_upper}"

    if action_upper == "EDIT" and payload.edited_clauses:
        for updated_clause in payload.edited_clauses:
            clause_id = updated_clause.get("id")
            new_text = updated_clause.get("extracted_text")
            if clause_id and new_text:
                db_clause = db.query(ClauseModel).filter(ClauseModel.id == clause_id, ClauseModel.job_id == target_job_id).first()
                if db_clause:
                    db_clause.extracted_text = new_text
                    db_clause.edited_text = new_text
                    db_clause.edited_at = datetime.datetime.utcnow()
                    db_clause.edited_by = current_user.id

    # Create Audit Log Entry
    audit_entry = AuditLogModel(
        job_id=target_job_id,
        user_email=current_user.email,
        action=action_upper,
        notes=comment_text,
        reviewer_comment=comment_text,
        escalation_status=(action_upper == "ESCALATE"),
        timestamp=datetime.datetime.utcnow()
    )
    db.add(audit_entry)
    
    if action_upper == "ESCALATE":
        doc.requires_manual_review = True
        doc.review_priority = "HIGH"

    db.commit()

    return {
        "status": "success",
        "job_id": target_job_id,
        "action_recorded": action_upper,
        "message": f"Successfully processed review action '{action_upper}'."
    }


# ==================== ADMIN GOVERNANCE ENDPOINTS ====================

@router.get("/admin/documents")
async def get_admin_all_documents(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all documents across ALL users with complete metadata and audit trails."""
    if current_user.role not in ["Admin", "General Counsel", "Senior Reviewer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin credentials required."
        )

    documents = db.query(DocumentModel).order_by(DocumentModel.created_at.desc()).all()

    result = []
    for doc in documents:
        audit_logs = db.query(AuditLogModel).filter(AuditLogModel.job_id == doc.job_id).order_by(AuditLogModel.timestamp.desc()).all()
        latest_action = audit_logs[0].action if audit_logs else "PENDING_REVIEW"

        high_risk_count = db.query(ClauseModel).filter(
            ClauseModel.job_id == doc.job_id, 
            ClauseModel.risk_level == "HIGH"
        ).count()
        total_clauses = db.query(ClauseModel).filter(ClauseModel.job_id == doc.job_id).count()

        result.append({
            "job_id": doc.job_id,
            "file_name": doc.filename,
            "uploader_email": doc.uploaded_by or "Unknown User",
            "business_unit": doc.business_unit,
            "document_category": doc.document_category,
            "document_type": doc.document_type,
            "confidentiality_level": doc.confidentiality_level,
            "review_priority": doc.review_priority,
            "requires_manual_review": doc.requires_manual_review,
            "created_at": doc.created_at.isoformat() if doc.created_at else str(datetime.datetime.utcnow()),
            "status": latest_action,
            "ocr_confidence": doc.ocr_confidence,
            "page_count": doc.pages,
            "high_risk_count": high_risk_count,
            "total_clauses": total_clauses,
            "audit_trail": [
                {
                    "id": log.id,
                    "action": log.action,
                    "user_email": log.user_email,
                    "notes": log.notes or log.reviewer_comment or "",
                    "timestamp": log.timestamp.isoformat() if log.timestamp else str(datetime.datetime.utcnow())
                } for log in audit_logs
            ]
        })

    return {"total_documents": len(result), "documents": result}


@router.post("/admin/review/action")
async def execute_admin_review_action(
    payload: AdminActionRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Executes Accept, Reject, or Manual Review on any user document and saves to database."""
    if current_user.role not in ["Admin", "General Counsel", "Senior Reviewer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin credentials required."
        )

    action_upper = payload.action.upper()
    if action_upper not in ["ACCEPT", "REJECT", "MANUAL_REVIEW"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be ACCEPT, REJECT, or MANUAL_REVIEW"
        )

    doc = db.query(DocumentModel).filter(DocumentModel.job_id == payload.job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if action_upper == "MANUAL_REVIEW":
        doc.requires_manual_review = True
        doc.review_priority = "HIGH"
    elif action_upper == "ACCEPT":
        doc.requires_manual_review = False

    comment_text = payload.comments or f"Admin ({current_user.email}) action executed: {action_upper}"
    
    audit_entry = AuditLogModel(
        job_id=payload.job_id,
        user_email=current_user.email,
        action=f"ADMIN_{action_upper}",
        notes=comment_text,
        reviewer_comment=comment_text,
        escalation_status=(action_upper == "MANUAL_REVIEW"),
        timestamp=datetime.datetime.utcnow()
    )

    db.add(audit_entry)
    db.commit()

    return {
        "status": "success",
        "job_id": doc.job_id,
        "action_recorded": f"ADMIN_{action_upper}",
        "requires_manual_review": doc.requires_manual_review,
        "message": f"Admin action '{action_upper}' saved to database successfully."
    }