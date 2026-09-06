import os
import json
import pandas as pd
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TAXONOMY_PATH = BASE_DIR / "data" / "risk_taxonomy.csv"
DEFAULT_POLICIES_PATH = BASE_DIR / "data" / "corporate_policies.json"

TAXONOMY_PATH = Path(os.getenv("RISK_TAXONOMY_PATH", DEFAULT_TAXONOMY_PATH))
POLICIES_PATH = Path(os.getenv("POLICIES_DATA_PATH", DEFAULT_POLICIES_PATH))

@router.get("/policies")
async def get_knowledge_base_policies():
    """Returns active corporate policies and risk taxonomy library without hardcoding."""
    policies = []
    if POLICIES_PATH.exists():
        try:
            with open(POLICIES_PATH, "r", encoding="utf-8") as f:
                policies = json.load(f)
        except Exception:
            policies = []

    taxonomies = []
    if TAXONOMY_PATH.exists():
        try:
            df = pd.read_csv(TAXONOMY_PATH)
            taxonomies = df.to_dict(orient="records")
        except Exception:
            taxonomies = []

    return {
        "active_policies": policies,
        "risk_taxonomy_rules": taxonomies
    }