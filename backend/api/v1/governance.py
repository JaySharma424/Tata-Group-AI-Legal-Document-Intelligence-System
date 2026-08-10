from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AuditLogModel, UserModel
from backend.api.v1.auth import get_current_user
from datetime import datetime

router = APIRouter()

@router.post("/review")
async def submit_review(
    payload: dict, 
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job_id = payload.get("job_id") or payload.get("document_id")
    action = payload.get("action") # APPROVED or REJECTED
    notes = payload.get("notes") or payload.get("comments") or ""

    if not job_id or not action:
        raise HTTPException(status_code=400, detail="job_id and action are required.")

    # Create and save audit log record to PostgreSQL
    db_audit = AuditLogModel(
        job_id=job_id,
        user_email=current_user.email,
        action=action.upper(),
        notes=notes,
        reviewer_comment=notes,
        timestamp=datetime.utcnow()
    )
    db.add(db_audit)
    db.commit()

    return {
        "status": "success",
        "message": f"Review action '{action}' recorded successfully and saved to audit logs."
    }