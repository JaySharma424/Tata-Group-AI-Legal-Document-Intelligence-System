import json
import os
import re
import ast
from typing import Any, Dict, List
from backend.services.llm_config import get_llm_config


def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    nvidia_env_key = os.getenv("NVIDIA_API_KEY")

    if api_key.startswith("nvapi-") or (nvidia_env_key and nvidia_env_key.startswith("nvapi-")):
        active_key = api_key if api_key.startswith("nvapi-") else nvidia_env_key
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            api_key=active_key,
            temperature=0,
            max_tokens=5000,
            timeout=25
        ).invoke(prompt).content

    elif api_key.startswith("gsk_") or os.getenv("GROQ_API_KEY"):
        active_key = api_key if api_key.startswith("gsk_") else os.getenv("GROQ_API_KEY")
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.3-70b-versatile", api_key=active_key, temperature=0, max_retries=1).invoke(prompt).content

    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        target_model = model_name if "gemini" in model_name.lower() else "gemini-1.5-flash"
        try:
            response = ChatGoogleGenerativeAI(model=target_model, google_api_key=api_key, temperature=0, max_retries=0).invoke(prompt)
            if isinstance(response, list):
                return str(response[0]) if response else ""
            return str(response.content) if hasattr(response, "content") else str(response)
        except Exception as e:
            if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "410" in str(e)) and nvidia_env_key:
                from langchain_nvidia_ai_endpoints import ChatNVIDIA
                return ChatNVIDIA(
                    model="meta/llama-3.3-70b-instruct",
                    api_key=nvidia_env_key,
                    temperature=0,
                    max_tokens=3000,
                    timeout=25
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
                "matched_reference_id": c.get("rag_reference_used", "MISSING-POLICY"),
                "retrieved_policy_rule": c.get("matched_policy_text", "Standard enterprise terms."),
                "baseline_taxonomy_risk": c.get("taxonomy_risk", "MEDIUM"),
                "vector_similarity": float(c.get("confidence_score", 0.50))
            })

        prompt = f"""
You are Senior Legal Counsel at Tata Group evaluating contractual clauses for '{business_unit}'.
Evaluate risks strictly based on the provided Knowledge Base rules and risk taxonomy guidelines.

CONTRACT CLAUSES & RETRIEVED POLICIES:
{json.dumps(clauses_context, indent=2)}

INSTRUCTIONS:
1. If 'matched_reference_id' is 'MISSING-POLICY':
   - Classify 'risk_level' as "HIGH".
   - In 'risk_rationale': "Missing Policy: No approved corporate policy covers this clause (similarity < 20%). Represents an unmapped legal exposure."
   - In 'proposed_redline': Provide a compliant enterprise replacement clause.
2. Otherwise, evaluate the clause against 'retrieved_policy_rule' taking into account 'baseline_taxonomy_risk':
   - "HIGH": Unlimited liability, uncapped customer indemnity, late payment interest > 18% annual, multi-year lock-in without convenience termination, foreign governing law/venue.
   - "MEDIUM": Exclusivity restrictions, non-standard confidentiality survival (>5 years), liability caps > 1x ACV without GC approval.
   - "LOW": Standard reciprocal terms, standard SLAs, insurance baselines, or mutual non-solicitation fully compliant with policy.
3. In 'risk_rationale', write 2 sentences explaining why the clause passes or violates the policy, citing 'matched_reference_id'.
4. CRITICAL: Maintain the exact 'matched_reference_id' in 'rag_reference_used'.
5. Set 'confidence_score' to the exact numeric value from 'vector_similarity'.
6. In 'proposed_redline': If HIGH or MEDIUM, write a redline amending the clause into full compliance. If LOW, set to null.

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

        # Grounded Fallback: Inherits true taxonomy risk level directly from Knowledge Base
        fallback_results = []
        for c in normalized_clauses:
            ref_id = c.get("rag_reference_used") or "MISSING-POLICY"
            policy_text = c.get("matched_policy_text") or "Standard enterprise contracting guidelines."
            derived_type = c.get("clause_type") or "General Provision"
            score = float(c.get("confidence_score", 0.50))
            level = c.get("taxonomy_risk") or ("HIGH" if ref_id == "MISSING-POLICY" or score < 0.20 else "LOW")

            if level == "HIGH":
                action = "Negotiate Amendment (High Policy Deviation)"
                rationale = f"Policy Deviation [{ref_id}]: Term conflicts with mandatory Tata compliance rules for '{derived_type}'. Policy: {policy_text[:120]}..."
            elif level == "MEDIUM":
                action = "Procurement Review Required"
                rationale = f"Policy Reference [{ref_id}]: Non-standard commercial term detected under '{derived_type}'. Policy: {policy_text[:120]}..."
            else:
                action = "Accept Standard Provision"
                rationale = f"Policy Reference [{ref_id}]: Provision adheres to approved enterprise standard for '{derived_type}'."

            fallback_results.append({
                "clause_type": derived_type,
                "extracted_text": c.get("extracted_text", ""),
                "confidence_score": score,
                "risk_level": level,
                "risk_rationale": rationale,
                "involved_party": "Tata Group & Counterparty",
                "rag_reference_used": ref_id,
                "page_reference": str(c.get("page_reference", "1")),
                "obligation_owner": "Legal & Procurement Desk",
                "recommended_action": action,
                "proposed_redline": None,
            })

        return fallback_results