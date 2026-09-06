import os
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from backend.database import get_db
from backend.models import DocumentModel, ClauseModel, AuditLogModel, UserModel
from backend.api.v1.auth import get_current_user

router = APIRouter()

DEFAULT_SCORECARD_PATH = Path(__file__).resolve().parents[3] / "tests" / "ai_output_tests" / "ragas_gemini_scorecard.csv"
SCORECARD_CSV_PATH = Path(os.getenv("RAGAS_SCORECARD_PATH", DEFAULT_SCORECARD_PATH))

def execute_ragas_async():
    try:
        from tests.ai_output_tests.ragas_eval_gemini import run_evaluation
        run_evaluation()
    except Exception as e:
        print(f"[ERROR] Asynchronous RAGAS evaluation execution failed: {e}")

@router.get("/telemetry")
async def get_legal_ops_telemetry(db: Session = Depends(get_db)):
    """Aggregates live system-wide telemetry and health checks without artificial values."""
    try:
        db.execute(text("SELECT 1"))
        system_health = "Optimal (Database Connected)"
    except Exception:
        system_health = "Degraded (Database Unreachable)"

    total_documents = db.query(DocumentModel).count()
    avg_confidence = db.query(func.avg(DocumentModel.ocr_confidence)).scalar() or 0.0
    manual_review_count = db.query(DocumentModel).filter(DocumentModel.requires_manual_review == True).count()
    
    high_risk_count = db.query(ClauseModel).filter(ClauseModel.risk_level == "HIGH").count()
    med_risk_count = db.query(ClauseModel).filter(ClauseModel.risk_level == "MEDIUM").count()
    low_risk_count = db.query(ClauseModel).filter(ClauseModel.risk_level == "LOW").count()
    
    total_audits = db.query(AuditLogModel).count()
    escalations = db.query(AuditLogModel).filter(AuditLogModel.action.ilike("%ESCALATE%")).count()
    acceptances = db.query(AuditLogModel).filter(AuditLogModel.action.ilike("%ACCEPT%")).count()
    rejections = db.query(AuditLogModel).filter(AuditLogModel.action.ilike("%REJECT%")).count()

    return {
        "status": "active",
        "system_health": system_health,
        "document_metrics": {
            "total_processed": total_documents,
            "average_ocr_confidence": round(float(avg_confidence), 2),
            "requires_manual_review": manual_review_count
        },
        "risk_distribution": {
            "high": high_risk_count,
            "medium": med_risk_count,
            "low": low_risk_count
        },
        "governance_metrics": {
            "total_reviews": total_audits,
            "acceptances": acceptances,
            "rejections": rejections,
            "escalations": escalations
        }
    }

@router.post("/ragas/evaluate")
async def trigger_ragas_evaluation(
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user)
):
    background_tasks.add_task(execute_ragas_async)
    return {
        "status": "initiated",
        "message": "Evaluation process triggered in background."
    }

@router.get("/ragas/results")
async def get_ragas_results():
    if not SCORECARD_CSV_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No evaluation report found. Execute POST /api/v1/monitoring/ragas/evaluate first."
        )
    try:
        df = pd.read_csv(SCORECARD_CSV_PATH)
        records = df.to_dict(orient="records")
        metrics = ["faithfulness", "context_precision", "context_recall", "answer_relevancy"]
        avg_scores = {
            m: round(float(df[m].mean()), 4) for m in metrics if m in df and not pd.isna(df[m].mean())
        }
        return {
            "status": "success",
            "summary_averages": avg_scores,
            "total_test_cases": len(records),
            "detailed_scores": records
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read evaluation report: {e}")

@router.get("/ragas/download")
async def download_ragas_scorecard():
    if not SCORECARD_CSV_PATH.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard file does not exist.")
    return FileResponse(path=str(SCORECARD_CSV_PATH), media_type='text/csv', filename="ragas_scorecard.csv")