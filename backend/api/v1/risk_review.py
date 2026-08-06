from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import DocumentModel, ClauseModel, UserModel
from backend.api.v1.auth import get_current_user  # <-- Import the JWT Auth Dependency

router = APIRouter()

@router.get("/console/high-risk")
async def get_risk_review_console(
    current_user: UserModel = Depends(get_current_user), # <-- Route Protected
    db: Session = Depends(get_db)
):
    """Returns all high-risk clauses securely for the authenticated user."""
    # Ensure the user only sees risks for their business unit (unless Admin)
    query = db.query(ClauseModel, DocumentModel).join(
        DocumentModel, ClauseModel.job_id == DocumentModel.job_id
    ).filter(ClauseModel.risk_level == "HIGH")
    
    if current_user.role != "Admin":
        query = query.filter(DocumentModel.business_unit == current_user.business_unit)
        
    high_risk_clauses = query.all()
    
    results = []
    for clause, doc in high_risk_clauses:
        results.append({
            "job_id": doc.job_id,
            "filename": doc.filename,
            "business_unit": doc.business_unit,
            "clause_type": clause.clause_type,
            "extracted_text": clause.extracted_text,
            "risk_rationale": clause.risk_rationale,
            "rag_reference_used": clause.rag_reference_used,
            "obligation_owner": clause.obligation_owner,
            "recommended_action": clause.recommended_action
        })
    return results

@router.get("/{job_id}/clause-intelligence")
async def get_clause_intelligence_panel(
    job_id: str, 
    current_user: UserModel = Depends(get_current_user), # <-- Route Protected
    db: Session = Depends(get_db)
):
    """Returns deep clause intelligence metrics, protected by user business unit."""
    doc = db.query(DocumentModel).filter(DocumentModel.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    # Security check: User must be in the same business unit to view
    if current_user.role != "Admin" and doc.business_unit != current_user.business_unit:
        raise HTTPException(status_code=403, detail="Access denied. Document belongs to a different business unit.")
        
    clauses = db.query(ClauseModel).filter(ClauseModel.job_id == job_id).all()
    
    return {
        "job_id": doc.job_id,
        "filename": doc.filename,
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