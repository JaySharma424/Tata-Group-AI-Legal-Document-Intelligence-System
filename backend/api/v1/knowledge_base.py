from fastapi import APIRouter
import os
import pandas as pd

router = APIRouter()

@router.get("/policies")
async def get_knowledge_base_policies():
    """Returns the active corporate policies and risk taxonomy library used for RAG grounding."""
    taxonomy_path = os.path.join("backend", "data", "risk_taxonomy.csv")
    
    policies = [
        {
            "policy_id": "POL-IND-2026-01",
            "category": "Statutory & Compliance",
            "description": "Standard Tata Group supplier code of conduct and regulatory alignment.",
            "status": "Active"
        },
        {
            "policy_id": "POL-IND-2026-02",
            "category": "Limitation of Liability",
            "description": "Mandatory liability caps tied to annual contract valuation.",
            "status": "Active"
        },
        {
            "policy_id": "POL-IND-2026-03",
            "category": "Data Privacy & Confidentiality",
            "description": "Strict enterprise data protection and cross-border data transfer protocols.",
            "status": "Active"
        }
    ]

    if os.path.exists(taxonomy_path):
        try:
            df = pd.read_csv(taxonomy_path)
            taxonomies = df.to_dict(orient="records")
        except Exception:
            taxonomies = []
    else:
        taxonomies = [
            {"risk_level": "HIGH", "trigger": "Unlimited Liability / No Cap", "action": "Escalate to Legal"},
            {"risk_level": "MEDIUM", "trigger": "Unilateral Termination without Notice", "action": "Request Revision"},
            {"risk_level": "LOW", "trigger": "Standard Governing Law (India/UK)", "action": "Accept Standard Term"}
        ]

    return {
        "active_policies": policies,
        "risk_taxonomy_rules": taxonomies
    }