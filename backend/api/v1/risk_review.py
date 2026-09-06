from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import DocumentModel, ClauseModel, UserModel
from backend.api.v1.auth import get_current_user
from backend.api.v1.review_2 import is_admin_user

router = APIRouter()

@router.get("/console/high-risk")
async def get_risk_review_console(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves high-risk clauses scoped by administrative or BU access."""
    query = db.query(ClauseModel, DocumentModel).join(
        DocumentModel, ClauseModel.job_id == DocumentModel.job_id
    ).filter(ClauseModel.risk_level == "HIGH")
    
    if not is_admin_user(current_user):
        query = query.filter(DocumentModel.business_unit == current_user.business_unit)
        
    records = query.all()
    return [
        {
            "job_id": doc.job_id,
            "filename": getattr(doc, 'filename', 'Contract.pdf'),
            "business_unit": doc.business_unit,
            "clause_type": clause.clause_type,
            "extracted_text": clause.extracted_text,
            "risk_rationale": clause.risk_rationale,
            "rag_reference_used": clause.rag_reference_used,
            "obligation_owner": clause.obligation_owner,
            "recommended_action": clause.recommended_action
        }
        for clause, doc in records
    ]

@router.get("/{job_id}/clause-intelligence")
async def get_clause_intelligence_panel(
    job_id: str, 
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns clause metadata secured by administrative role or BU tenancy."""
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        
    if not is_admin_user(current_user) and doc.business_unit != current_user.business_unit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied across business unit.")
        
    clauses = db.query(ClauseModel).filter(ClauseModel.job_id == job_id).all()
    
    return {
        "job_id": doc.job_id,
        "filename": getattr(doc, 'filename', 'Contract.pdf'),
        "ocr_confidence": doc.ocr_confidence,
        "requires_manual_review": doc.requires_manual_review,
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
                "page_reference": c.page_reference,
                "obligation_owner": c.obligation_owner,
                "recommended_action": c.recommended_action
            } for c in clauses
        ]
    }