import os
from datetime import datetime, timezone
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models import DocumentModel, ClauseModel, AuditLogModel, UserModel
from backend.api.v1.auth import get_current_user

router = APIRouter()

def is_admin_user(user: UserModel) -> bool:
    """Evaluates role-based and environment-configured admin privileges."""
    admin_roles = set(os.getenv("ADMIN_ROLES", "Admin,General Counsel,Senior Reviewer").split(","))
    admin_emails = set(e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip())
    
    has_role = user.role in admin_roles
    has_email = bool(user.email and user.email.lower() in admin_emails)
    return has_role or has_email

class ReviewActionRequest(BaseModel):
    job_id: str
    action: str = Field(..., regex="^(ACCEPT|REJECT|EDIT|ESCALATE)$")
    comment: Optional[str] = None
    edited_clauses: Optional[List[dict]] = None

class AdminActionRequest(BaseModel):
    job_id: str
    action: str = Field(..., regex="^(ACCEPT|REJECT|MANUAL_REVIEW)$")
    comments: Optional[str] = ""

@router.get("/history")
async def get_review_history(
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    audits = db.query(AuditLogModel).filter(
        AuditLogModel.user_email == current_user.email
    ).order_by(AuditLogModel.timestamp.desc()).limit(50).all()

    history = []
    for log in audits:
        doc = db.query(DocumentModel).filter(DocumentModel.job_id == log.job_id).first()
        history.append({
            "id": str(log.id),
            "document_id": log.job_id,
            "file_name": getattr(doc, 'filename', "Contract.pdf") if doc else "Contract.pdf",
            "action": log.action.upper(),
            "timestamp": log.timestamp.isoformat() if log.timestamp else datetime.now(timezone.utc).isoformat(),
            "reviewer_email": log.user_email
        })
    return {"history": history}

@router.post("/actions")
async def process_review_action(
    payload: ReviewActionRequest, 
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == payload.job_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Document with job_id '{payload.job_id}' not found."
        )

    action_upper = payload.action.upper()
    comment_text = payload.comment or f"Action: {action_upper}"

    if action_upper == "EDIT" and payload.edited_clauses:
        for item in payload.edited_clauses:
            clause_id = item.get("id")
            new_text = item.get("extracted_text")
            if clause_id and new_text:
                clause = db.query(ClauseModel).filter(
                    ClauseModel.id == clause_id, 
                    ClauseModel.job_id == payload.job_id
                ).first()
                if clause:
                    clause.extracted_text = new_text
                    clause.edited_text = new_text
                    clause.edited_at = datetime.now(timezone.utc)
                    clause.edited_by = current_user.id

    doc.status = action_upper
    if action_upper == "ESCALATE":
        doc.requires_manual_review = True
        doc.review_priority = "HIGH"

    audit_entry = AuditLogModel(
        job_id=payload.job_id,
        user_email=current_user.email,
        action=action_upper,
        notes=comment_text,
        reviewer_comment=comment_text,
        escalation_status=(action_upper == "ESCALATE"),
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_entry)
    db.commit()

    return {"status": "success", "job_id": payload.job_id, "action": action_upper}

@router.get("/admin/documents")
async def get_admin_all_documents(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not is_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required.")

    documents = db.query(DocumentModel).order_by(DocumentModel.created_at.desc()).all()
    results = []
    
    for doc in documents:
        audit_logs = db.query(AuditLogModel).filter(
            AuditLogModel.job_id == doc.job_id
        ).order_by(AuditLogModel.timestamp.desc()).all()

        high_risk_count = db.query(ClauseModel).filter(
            ClauseModel.job_id == doc.job_id, 
            ClauseModel.risk_level == "HIGH"
        ).count()
        total_clauses = db.query(ClauseModel).filter(ClauseModel.job_id == doc.job_id).count()

        results.append({
            "job_id": doc.job_id,
            "file_name": getattr(doc, 'filename', "Contract.pdf"),
            "uploader_email": getattr(doc, 'uploaded_by', ""),
            "business_unit": getattr(doc, 'business_unit', ""),
            "document_category": getattr(doc, 'document_category', ""),
            "document_type": getattr(doc, 'document_type', ""),
            "review_priority": getattr(doc, 'review_priority', "Normal"),
            "requires_manual_review": getattr(doc, 'requires_manual_review', False),
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "status": doc.status or (audit_logs[0].action if audit_logs else "PENDING"),
            "ocr_confidence": getattr(doc, 'ocr_confidence', 0.0),
            "high_risk_count": high_risk_count,
            "total_clauses": total_clauses,
            "audit_trail": [
                {
                    "id": log.id,
                    "action": log.action,
                    "user_email": log.user_email,
                    "notes": log.notes or "",
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                } for log in audit_logs
            ]
        })

    return {"total_documents": len(results), "documents": results}

@router.post("/admin/review/action")
async def execute_admin_review_action(
    payload: AdminActionRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not is_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required.")

    doc = db.query(DocumentModel).filter(DocumentModel.job_id == payload.job_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target document not found.")

    action_upper = payload.action.upper()
    doc.status = f"ADMIN_{action_upper}"
    doc.requires_manual_review = (action_upper == "MANUAL_REVIEW")
    if action_upper == "MANUAL_REVIEW":
        doc.review_priority = "HIGH"

    comment = payload.comments or f"Admin action recorded: {action_upper}"
    audit_entry = AuditLogModel(
        job_id=payload.job_id,
        user_email=current_user.email,
        action=f"ADMIN_{action_upper}",
        notes=comment,
        reviewer_comment=comment,
        escalation_status=(action_upper == "MANUAL_REVIEW"),
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_entry)
    db.commit()

    return {"status": "success", "job_id": doc.job_id, "action": f"ADMIN_{action_upper}"}