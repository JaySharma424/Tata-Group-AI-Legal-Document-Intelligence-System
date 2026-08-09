import json
import os
import re
from typing import Any, Dict, List
import google.generativeai as genai


class LegalReasoningService:
  """Executes dedicated legal reasoning and risk flagging pass using Gemini and RAG context.

  Uses batch prompt evaluation to process all clauses in a single API call,
  dramatically reducing quota consumption.
  """

  def __init__(self):
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
      genai.configure(api_key=api_key)

  def evaluate_risk_and_reasoning(
      self,
      normalized_clauses: List[Dict[str, Any]],
      business_unit: str,
      user_role: str,
  ) -> List[Dict[str, Any]]:
    """Applies legal reasoning to all normalized clauses in a single batch LLM call."""
    if not normalized_clauses:
      return []

    # 1. Prepare Batch Prompt containing all clauses
    clauses_json_str = json.dumps(normalized_clauses, indent=2)

    prompt = f"""
        You are Senior Legal Counsel at Tata Group evaluating contracts for the '{business_unit}' business unit from the perspective of a '{user_role}'.
        
        Analyze the following array of normalized contract clauses:
        {clauses_json_str}
        
        INSTRUCTIONS:
        Perform a rigorous legal reasoning evaluation for EVERY clause in the array:
        1. Determine the risk level strictly as: "HIGH", "MEDIUM", or "LOW".
        2. Provide a professional legal rationale explaining exposure or compliance alignment against Tata policies.
        3. Specify the appropriate RAG policy reference ID cited from the context (e.g., "CLS-LIAB-001", "RISK-IND-101", "CLS-NDA-003", "LAW-MUM-001", or "POL-IND-2026-01").
        4. Suggest a recommended action (e.g., "Escalate to Legal", "Accept Standard Term", "Request Revision").
        
        Return ONLY a valid JSON array matching the exact length and order of the input clauses. Each object in the array MUST contain these exact keys:
        ["clause_type", "extracted_text", "confidence_score", "risk_level", "risk_rationale", "involved_party", "rag_reference_used", "page_reference", "obligation_owner", "recommended_action"]
        """

    # 2. Active Model Candidates Cascade
    model_candidates = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.6-flash"
    ]

    for model_name in model_candidates:
      try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        text_res = response.text.strip()

        # Clean markdown code blocks if present
        if text_res.startswith("```json"):
          text_res = text_res[7:]
        if text_res.startswith("```"):
          text_res = text_res[3:]
        if text_res.endswith("```"):
          text_res = text_res[:-3]

        match = re.search(r"\[.*\]", text_res.strip(), re.DOTALL)
        if match:
          evaluated_array = json.loads(match.group(0))

          if (
              isinstance(evaluated_array, list)
              and len(evaluated_array) == len(normalized_clauses)
          ):
            print(
                f"✅ Successfully batch-evaluated all {len(evaluated_array)}"
                f" clauses in 1 call using model: {model_name}"
            )
            return evaluated_array
          elif isinstance(evaluated_array, list) and len(evaluated_array) > 0:
            print(
                f"✅ Batch evaluated {len(evaluated_array)} clauses using"
                f" model: {model_name}"
            )
            return evaluated_array
      except Exception as e:
        print(
            f"⚠️ Batch reasoning model {model_name} failed: {e}. Trying next"
            " candidate in cascade..."
        )
        continue

    # 3. Local Fallback if cloud APIs fail
    print(
        "⚡ All reasoning models rate-limited or unavailable. Retaining"
        " normalized clause defaults."
    )
    return normalized_clauses