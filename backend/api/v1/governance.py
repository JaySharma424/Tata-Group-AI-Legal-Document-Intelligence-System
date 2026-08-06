from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AuditLogModel
from datetime import datetime

router = APIRouter()

@router.post("/review")
async def submit_review(payload: dict, db: Session = Depends(get_db)):
    job_id = payload.get("job_id")
    reviewer_name = payload.get("reviewer_name", "Senior Legal Counsel")
    action = payload.get("action") # APPROVED or REJECTED
    notes = payload.get("notes", "")

    if not job_id or not action:
        raise HTTPException(status_code=400, detail="job_id and action are required.")

    # Create and save audit log record to PostgreSQL
    db_audit = AuditLogModel(
        job_id=job_id,
        reviewer_name=reviewer_name,
        action=action,
        notes=notes,
        timestamp=datetime.utcnow()
    )
    db.add(db_audit)
    db.commit()

    return {
        "status": "success",
        "message": f"Review action '{action}' recorded successfully and saved to audit logs."
    }