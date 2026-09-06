import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuditLogModel, UserModel
from backend.api.v1.auth import get_current_user

router = APIRouter()

class ReviewActionEnum(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATE = "ESCALATE"
    EDIT = "EDIT"

class GovernanceReviewRequest(BaseModel):
    job_id: str = Field(..., description="Target document or job identifier")
    action: ReviewActionEnum = Field(..., description="Governance action taken")
    notes: Optional[str] = Field(default="", description="Reviewer feedback or notes")

@router.post("/review", status_code=status.HTTP_201_CREATED)
async def submit_review(
    payload: GovernanceReviewRequest, 
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    action_value = payload.action.value.upper()
    db_audit = AuditLogModel(
        job_id=payload.job_id,
        user_email=current_user.email,
        action=action_value,
        notes=payload.notes,
        reviewer_comment=payload.notes,
        escalation_status=(action_value == "ESCALATE"),
        timestamp=datetime.now(timezone.utc)
    )
    db.add(db_audit)
    db.commit()

    return {
        "status": "success",
        "job_id": payload.job_id,
        "action": action_value,
        "message": f"Review action '{action_value}' recorded successfully."
    }