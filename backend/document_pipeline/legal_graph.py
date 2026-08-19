import json
import ast
from typing import Dict, Any
from langsmith import traceable
# Assuming these services are in the same folder or properly accessible
from backend.document_pipeline.reasoning_service import _invoke_dynamic_llm, clean_llm_json_response, deduplicate_extracted_clauses
from backend.services.llm_config import get_llm_config

@traceable(name="LLM Clause Extraction Node")
def extract_clauses_node(state: Dict[str, Any]) -> Dict[str, Any]:
    ocr_text = state.get("ocr_text", "")
    business_unit = state.get("business_unit", "Enterprise")
    user_role = state.get("user_role", "Senior Reviewer")

    config = get_llm_config()
    api_key = config.get("api_key", "")
    selected_llm = config.get("llm_model", "")

    # Optimized prompt length to save RAM
    prompt = f"""
    You are Aadhya, Enterprise Legal Intelligence AI for Tata Group.
    Analyze the document text for Business Unit: '{business_unit}' and User Role: '{user_role}'.

    DOCUMENT TEXT TO ANALYZE:
    {ocr_text[:8000]} 

    INSTRUCTIONS:
    1. Extract ALL distinct, non-duplicate legal clauses.
    2. MUST extract multiple distinct clauses (3-8). 
    3. Output JSON array ONLY. No markdown, no preambles.
    
    Keys required: "clause_type", "extracted_text", "confidence_score", "risk_level", "risk_rationale", "involved_party", "page_reference", "obligation_owner", "recommended_action", "proposed_redline".
    """

    raw_clauses = []
    
    if selected_llm and api_key:
        try:
            raw_output = _invoke_dynamic_llm(prompt, selected_llm, api_key)
            text_res = clean_llm_json_response(raw_output)

            if text_res and text_res != "[]":
                # Clean up string to be parsable JSON
                python_str = text_res.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                try:
                    parsed = json.loads(text_res)
                except json.JSONDecodeError:
                    try:
                        parsed = ast.literal_eval(python_str)
                    except Exception as ast_err:
                        print(f"⚠️ Parsing failed: {ast_err}")
                        parsed = None

                if isinstance(parsed, dict): parsed = [parsed]

                if isinstance(parsed, list):
                    valid_clauses = []
                    for item in parsed:
                        if isinstance(item, dict) and ("clause_type" in item or "type" in item):
                            normalized_item = {
                                "clause_type": item.get("clause_type") or item.get("type") or "GENERAL PROVISION",
                                "extracted_text": item.get("extracted_text") or item.get("text") or "",
                                "confidence_score": item.get("confidence_score", 0.92),
                                "risk_level": item.get("risk_level", "MEDIUM"),
                                "risk_rationale": item.get("risk_rationale", "Evaluated under enterprise compliance."),
                                "involved_party": item.get("involved_party", "Tata Group & Counterparty"),
                                "page_reference": item.get("page_reference", "Section 1"),
                                "obligation_owner": item.get("obligation_owner", "Compliance Team"),
                                "recommended_action": item.get("recommended_action", "Review"),
                                "proposed_redline": item.get("proposed_redline", None)
                            }
                            valid_clauses.append(normalized_item)
                    
                    if valid_clauses:
                        raw_clauses = valid_clauses
                        print(f"✅ Successfully extracted {len(raw_clauses)} clauses.")

        except Exception as e:
            print(f"❌ Model failed: {e}")

    # Fallback to simple paragraph splitter if extraction failed or only found 1 clause
    if not raw_clauses or len(raw_clauses) <= 1:
        print("⚡ Triggering paragraph-based fallback to ensure multi-clause output...")
        paragraphs = [p.strip() for p in ocr_text.split("\n\n") if len(p.strip()) > 50]
        if len(paragraphs) > 1:
            raw_clauses = []
            for idx, para in enumerate(paragraphs[:5]): # Limit to 5 for memory safety
                raw_clauses.append({
                    "clause_type": f"SECTION {idx+1}",
                    "extracted_text": para[:400],
                    "confidence_score": 0.85,
                    "risk_level": "MEDIUM",
                    "risk_rationale": "Extracted via structural fallback.",
                    "involved_party": "Tata Group & Counterparty",
                    "page_reference": "N/A",
                    "obligation_owner": "Assigned Owner",
                    "recommended_action": "Review",
                    "proposed_redline": None
                })
        else:
            # Absolute default
            raw_clauses = [{
                "clause_type": "GENERAL PROVISION",
                "extracted_text": ocr_text[:300],
                "confidence_score": 0.80,
                "risk_level": "LOW",
                "risk_rationale": "Fallback extraction.",
                "involved_party": "N/A",
                "page_reference": "N/A",
                "obligation_owner": "N/A",
                "recommended_action": "Review",
                "proposed_redline": None
            }]

    unique_clauses = deduplicate_extracted_clauses(raw_clauses)
    return {"final_clauses": unique_clauses}
