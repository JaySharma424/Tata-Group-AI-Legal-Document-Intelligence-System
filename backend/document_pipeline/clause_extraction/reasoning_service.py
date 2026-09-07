import json
import os
import re
import ast
from typing import Any, Dict, List
from backend.services.llm_config import get_llm_config


def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    nvidia_env_key = os.getenv("NVIDIA_API_KEY")

    # Priority 1: NVIDIA Routing using reliable high-speed model
    if api_key.startswith("nvapi-") or (nvidia_env_key and nvidia_env_key.startswith("nvapi-")):
        active_key = api_key if api_key.startswith("nvapi-") else nvidia_env_key
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(
            model="meta/llama-3.3-70b-instruct",
            api_key=active_key,
            temperature=0,
            max_tokens=3000,
            timeout=30
        ).invoke(prompt).content

    # Priority 2: Groq Routing
    elif api_key.startswith("gsk_") or os.getenv("GROQ_API_KEY"):
        active_key = api_key if api_key.startswith("gsk_") else os.getenv("GROQ_API_KEY")
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.1-70b-versatile", api_key=active_key, temperature=0, max_retries=1).invoke(prompt).content

    # Priority 3: Google Gemini with automatic fallback to NVIDIA on 429
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        target_model = model_name if "gemini" in model_name.lower() else "gemini-1.5-flash"
        try:
            response = ChatGoogleGenerativeAI(model=target_model, google_api_key=api_key, temperature=0, max_retries=0).invoke(prompt)
            if isinstance(response, list):
                return str(response[0]) if response else ""
            return str(response.content) if hasattr(response, "content") else str(response)
        except Exception as e:
            if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and nvidia_env_key:
                from langchain_nvidia_ai_endpoints import ChatNVIDIA
                return ChatNVIDIA(
                    model="meta/llama-3.3-70b-instruct",
                    api_key=nvidia_env_key,
                    temperature=0,
                    max_tokens=3000,
                    timeout=30
                ).invoke(prompt).content
            raise e


def robust_json_harvester(raw_text: str) -> List[Dict[str, Any]]:
    if not raw_text:
        return []
    text = re.sub(r"<think>.*?</think>", "", str(raw_text), flags=re.DOTALL)
    md_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if md_match:
        text = md_match.group(1)

    extracted = []
    depth = 0
    start_idx = -1
    for i, char in enumerate(text):
        if char == '{':
            if depth == 0:
                start_idx = i
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start_idx != -1:
                obj_str = text[start_idx:i+1].replace('\n', ' ').replace('\r', ' ')
                try:
                    parsed = json.loads(obj_str)
                    extracted.append(parsed)
                except json.JSONDecodeError:
                    try:
                        clean_str = obj_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                        parsed = ast.literal_eval(clean_str)
                        if isinstance(parsed, dict):
                            extracted.append(parsed)
                    except Exception:
                        continue
    return extracted


class LegalReasoningService:
    def evaluate_risk_and_reasoning(
        self,
        normalized_clauses: List[Dict[str, Any]],
        business_unit: str = "Procurement",
        user_role: str = "Compliance Officer",
    ) -> List[Dict[str, Any]]:
        if not normalized_clauses:
            return []

        config = get_llm_config()
        api_key = config.get("api_key", "") or os.getenv("NVIDIA_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        selected_llm = "meta/llama-3.3-70b-instruct"

        clauses_context = []
        for idx, c in enumerate(normalized_clauses, start=1):
            clauses_context.append({
                "item_index": idx,
                "clause_type": c.get("clause_type", "General Provision"),
                "extracted_text": c.get("extracted_text", ""),
                "page_reference": str(c.get("page_reference", "1")),
                "matched_reference_id": c.get("rag_reference_used", "STANDARD-BASELINE"),
                "retrieved_policy_rule": c.get("matched_policy_text", "Standard enterprise terms."),
                "handling_guidelines": c.get("handling_guidelines", "Review against business terms.")
            })

        prompt = f"""
You are Senior Legal Counsel at Tata Group evaluating contractual clauses for the '{business_unit}' division.
You must analyze each clause against the vector-matched policy rule retrieved from our knowledge base (6 policy files + risk_taxonomy.csv).

RETRIEVED CONTRACT CLAUSES & KNOWLEDGE BASE POLICIES:
{json.dumps(clauses_context, indent=2)}

EVALUATION INSTRUCTIONS:
1. Examine each clause against its specific 'retrieved_policy_rule' and 'handling_guidelines'.
2. Classify 'risk_level' strictly as:
   - "HIGH": Direct conflict with policy (e.g., unlimited liability, uncapped indemnity, excessive interest penalties, unilateral lock-in, non-Indian jurisdiction).
   - "MEDIUM": Ambiguous terms, non-standard payment windows, or missing governance safeguards.
   - "LOW": Standard definitions, recitals, or provisions fully compliant with policy.
3. In 'risk_rationale', provide 2-3 sentences of legal reasoning explaining why the clause passes or deviates from policy, explicitly citing the matched reference ID.
4. CRITICAL: Set 'rag_reference_used' to the exact 'matched_reference_id' provided in the context (e.g., CLS-LIAB-001, CLS-IND-002, TAX-04). If standard with no deviation, set to 'STANDARD-BASELINE'.
5. In 'proposed_redline': If risk is HIGH or MEDIUM, write a revised clause that brings the term into full compliance with Tata policy. If risk is LOW, set to null.

Return ONLY a valid JSON array of objects with these exact keys:
["clause_type", "extracted_text", "confidence_score", "risk_level", "risk_rationale", "involved_party", "rag_reference_used", "page_reference", "obligation_owner", "recommended_action", "proposed_redline"]
"""

        if api_key:
            try:
                raw_output = _invoke_dynamic_llm(prompt, selected_llm, api_key)
                parsed = robust_json_harvester(raw_output)
                valid = [
                    item for item in parsed
                    if isinstance(item, dict) and "clause_type" in item and "extracted_text" in item
                ]
                if valid:
                    return valid
            except Exception as e:
                print(f"[WARN] LLM evaluation error: {e}")

        # Fallback maintaining true retrieved metadata and citations
        fallback_results = []
        for c in normalized_clauses:
            text_lower = c.get("extracted_text", "").lower()
            ref_id = c.get("rag_reference_used", "STANDARD-BASELINE")
            policy_text = c.get("matched_policy_text", "Standard enterprise guidelines.")

            is_high = any(k in text_lower for k in [
                "unlimited", "penalty of 5%", "may not terminate",
                "laws of the state of new york", "without any cap"
            ])
            fallback_results.append({
                "clause_type": c.get("clause_type", "General Provision"),
                "extracted_text": c.get("extracted_text", ""),
                "confidence_score": c.get("confidence_score", 0.85),
                "risk_level": "HIGH" if is_high else "LOW",
                "risk_rationale": f"Evaluated against [{ref_id}]: {policy_text}",
                "involved_party": "Tata Group & Counterparty",
                "rag_reference_used": ref_id,
                "page_reference": str(c.get("page_reference", "1")),
                "obligation_owner": "Legal & Procurement Desk",
                "recommended_action": "Modify terms to align with Tata standard baseline" if is_high else "Accept as standard",
                "proposed_redline": None,
            })
        return fallback_results