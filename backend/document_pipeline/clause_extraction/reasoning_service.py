import json
import os
import re
from typing import Any, Dict, List

from backend.services.llm_config import get_llm_config

def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    """Dynamically routes tasks while strictly isolating provider API keys."""
    model_lower = model_name.lower()
    
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        if api_key.startswith("nvapi-"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        else:
            from langchain_groq import ChatGroq
            return ChatGroq(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not google_key and not api_key.startswith("nvapi-") and not api_key.startswith("sk-") and not api_key.startswith("gsk_"):
            google_key = api_key
            
        response = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_key, temperature=0).invoke(prompt)
        if isinstance(response, list):
            return str(response[0]) if response else ""
        return str(response.content) if hasattr(response, "content") else str(response)

def clean_llm_json_response(raw_text: str) -> str:
    """Aggressively extracts the JSON array from noisy LLM outputs."""
    text = str(raw_text).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # 🚀 FIX: Hard JSON Array locator to prevent "Extra Data" errors
    start_idx = text.find('[')
    end_idx = text.rfind(']')
    if start_idx != -1 and end_idx != -1:
        return text[start_idx:end_idx+1]
    return text

class LegalReasoningService:
  """Executes dedicated legal reasoning and risk flagging pass using Dynamic LLMs and RAG context."""

  def evaluate_risk_and_reasoning(
      self,
      normalized_clauses: List[Dict[str, Any]],
      business_unit: str,
      user_role: str,
  ) -> List[Dict[str, Any]]:
    
    if not normalized_clauses:
      return []

    config = get_llm_config()
    api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY", "")
    selected_llm = config.get("llm_model", "gemini-3.5-flash")

    clauses_json_str = json.dumps(normalized_clauses, indent=2)

    prompt = f"""
        You are Senior Legal Counsel at Tata Group evaluating contracts for the '{business_unit}' business unit from the perspective of a '{user_role}'.
        
        Analyze the following array of normalized contract clauses:
        {clauses_json_str}
        
        INSTRUCTIONS:
        Perform a rigorous legal reasoning evaluation for EVERY clause in the array:
        1. Determine the risk level strictly as: "HIGH", "MEDIUM", or "LOW".
        2. Provide a professional legal rationale explaining exposure or compliance alignment against Tata policies.
        3. Specify the appropriate RAG policy reference ID cited from the context.
        4. Suggest a recommended action (e.g., "Escalate to Legal", "Accept Standard Term", "Request Revision").
        
        Return ONLY a valid JSON array matching the exact length and order of the input clauses. Each object in the array MUST contain these exact keys:
        ["clause_type", "extracted_text", "confidence_score", "risk_level", "risk_rationale", "involved_party", "rag_reference_used", "page_reference", "obligation_owner", "recommended_action"]
        """

    # 🚀 FIX: Removed dead gemini-1.5 and 2.5 models to stop 404 infinite loops
    ordered_candidates = [
        selected_llm,
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]
    
    seen = set()
    cascade = [m for m in ordered_candidates if m and not (m in seen or seen.add(m))]

    for model_name in cascade:
      try:
        raw_output = _invoke_dynamic_llm(prompt, model_name, api_key)
        text_res = clean_llm_json_response(raw_output)

        parsed = json.loads(text_res)
        if isinstance(parsed, list):
          valid_clauses = []
          for item in parsed:
            if isinstance(item, dict) and "clause_type" in item and "extracted_text" in item:
              valid_clauses.append(item)

          if len(valid_clauses) == len(normalized_clauses):
            print(f"✅ Successfully batch-evaluated all {len(valid_clauses)} clauses in 1 call using model: {model_name}")
            return valid_clauses
          elif len(valid_clauses) > 0:
            print(f"✅ Batch evaluated {len(valid_clauses)} valid clauses using model: {model_name}")
            return valid_clauses

      except Exception as e:
        error_str = str(e)
        if any(serious in error_str for serious in ["INVALID_ARGUMENT", "API_KEY_INVALID", "NOT_FOUND", "PERMISSION_DENIED", "UNAUTHENTICATED"]):
          print(f"❌ Model {model_name} failed with serious error: {e}")
          continue
        print(f"⚠️ Model {model_name} transient error, trying next: {e}")
        continue

    print("⚡ All reasoning models rate-limited or unavailable. Retaining normalized clause defaults.")
    return normalized_clauses
