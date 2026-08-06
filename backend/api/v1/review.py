from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from backend.database import get_db
from backend.models import DocumentModel, ClauseModel, AuditLogModel, UserModel
import datetime
import jwt
import os

# Change this:
# SECRET_KEY = os.getenv("SECRET_KEY", "tata-enterprise-super-secret-key-2026") -> Check length

# To a strictly safe, long secret key (more than 32 characters):
SECRET_KEY = "tata_enterprise_secure_legal_intelligence_platform_secret_key_2026_safe"
ALGORITHM = "HS256"
router = APIRouter()
security = HTTPBearer()

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


# ==================== JWT AUTH DEPENDENCY ====================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Extracts and validates user identity securely from the Bearer JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        # Decodes using the 32+ byte secure key
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except Exception as e:
        print(f"JWT Decoding Error: {e}") # Yeh aapko backend terminal mein exact reason bata dega
        raise credentials_exception
        
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user is None:
        raise credentials_exception
    return user


# ==================== REVIEW & HISTORY ROUTES ====================

@router.get("/history")
@router.get("/history")
async def get_review_history(
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Returns review history strictly isolated by the authenticated user's email from the JWT token."""
    try:
        order_col = getattr(AuditLogModel, "created_at", None) or getattr(AuditLogModel, "timestamp", None) or AuditLogModel.id
        query = db.query(AuditLogModel)
        
        # Strict Multi-Tenant Isolation: Filter by current_user.email unless Admin
        if current_user.role != "Admin":
            if hasattr(AuditLogModel, "user_email"):
                query = query.filter(AuditLogModel.user_email == current_user.email)
            elif hasattr(AuditLogModel, "reviewer_email"):
                query = query.filter(AuditLogModel.reviewer_email == current_user.email)

        audits = query.order_by(order_col.desc()).limit(50).all()
    except Exception:
        audits = []

    history_list = []
    for idx, a in enumerate(audits, start=1):
        job_id_val = getattr(a, "job_id", None) or getattr(a, "document_id", None) or f"job-{idx}"
        
        doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id_val).first()
        file_name_val = getattr(a, "file_name", None) or (doc.filename if doc else None) or "Analyzed Contract.pdf"

        timestamp_val = getattr(a, "created_at", None) or getattr(a, "timestamp", None)
        timestamp_str = timestamp_val.isoformat() if timestamp_val and hasattr(timestamp_val, "isoformat") else str(datetime.datetime.utcnow())
        
        history_list.append({
            "id": str(getattr(a, "id", idx)),
            "document_id": job_id_val,
            "file_name": file_name_val,
            "action": getattr(a, "action", "ACCEPT").upper(),
            "timestamp": timestamp_str,
            "reviewer_email": getattr(a, "user_email", None) or getattr(a, "reviewer_email", current_user.email)
        })
        
    return {"history": history_list}


@router.post("/actions")
async def process_review_action(
    payload: ReviewActionRequest, 
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Processes compliance review actions securely using the verified JWT user session."""
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
            document_type="Unknown",              
            ocr_confidence=95.0,
            uploaded_by=current_user.email
        )
        db.add(doc)
        db.commit()
    elif payload.file_name and hasattr(doc, "filename"):
        doc.filename = payload.file_name
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

    audit_kwargs = {
        "job_id": target_job_id,
        "user_email": current_user.email,
        "action": action_upper,
        "notes": comment_text
    }
    
    if hasattr(AuditLogModel, "reviewer_comment"):
        audit_kwargs["reviewer_comment"] = comment_text

    audit_entry = AuditLogModel(**audit_kwargs)
    db.add(audit_entry)
    
    if action_upper == "ESCALATE":
        if hasattr(doc, "requires_manual_review"):
            doc.requires_manual_review = True
        if hasattr(doc, "review_priority"):
            doc.review_priority = "HIGH"

    db.commit()

    return {
        "status": "success",
        "job_id": target_job_id,
        "action_recorded": action_upper,
        "message": f"Successfully processed review action '{action_upper}'."
    }


@router.get("/{job_id}/audit-trail")
async def get_audit_trail(
    job_id: str, 
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Retrieves full audit trail history for a specific document job."""
    try:
        audits = db.query(AuditLogModel).filter(AuditLogModel.job_id == job_id).all()
    except Exception:
        audits = []
        
    return [
        {
            "reviewer": getattr(a, "user_email", current_user.email),
            "action": getattr(a, "action", "REVIEW"),
            "comment": getattr(a, "notes", None) or getattr(a, "reviewer_comment", "") or "",
            "timestamp": getattr(a, "timestamp", None).isoformat() if hasattr(a, "timestamp") and getattr(a, "timestamp") else str(datetime.datetime.utcnow())
        }
        for a in audits
    ]