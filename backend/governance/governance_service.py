import datetime
import json
import os
from typing import Dict, List, Optional
from pydantic import BaseModel

AUDIT_LOG_PATH = "backend/storage/audit_logs.json"

class ReviewAction(BaseModel):
    job_id: str
    reviewer_name: str
    action: str  # "APPROVED", "REJECTED", "MODIFIED"
    modified_clauses: Optional[List[Dict]] = None
    notes: Optional[str] = None

class GovernanceService:
    def __init__(self):
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        if not os.path.exists(AUDIT_LOG_PATH):
            with open(AUDIT_LOG_PATH, "w") as f:
                json.dump([], f)

    def log_review(self, review: ReviewAction) -> dict:
        """Records a compliance audit event for human-in-the-loop actions."""
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "job_id": review.job_id,
            "reviewer_name": review.reviewer_name,
            "action": review.action,
            "modified_clauses": review.modified_clauses,
            "notes": review.notes
        }

        try:
            with open(AUDIT_LOG_PATH, "r+") as f:
                logs = json.load(f)
                logs.append(entry)
                f.seek(0)
                json.dump(logs, f, indent=4)
            return {"status": "success", "audit_logged": True, "entry": entry}
        except Exception as e:
            raise RuntimeError(f"Failed to write audit log: {str(e)}")

    def get_audit_trail(self, job_id: str) -> List[dict]:
        """Retrieves the complete compliance history for a specific document job."""
        if not os.path.exists(AUDIT_LOG_PATH):
            return []
        
        with open(AUDIT_LOG_PATH, "r") as f:
            logs = json.load(f)
            return [log for log in logs if log["job_id"] == job_id]