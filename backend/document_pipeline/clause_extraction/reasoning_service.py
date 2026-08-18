import json
import os
import re
from typing import Any, Dict, List

# Import dynamic PostgreSQL LLM config service
from backend.services.llm_config import get_llm_config

# =====================================================================
# 🚀 NEW: DYNAMIC LLM ROUTER
# =====================================================================
def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    """Dynamically routes tasks while strictly isolating provider API keys."""
    import os
    model_lower = model_name.lower()
    
    # 1. NVIDIA ROUTING
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        
    # 2. OPENAI ROUTING
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        
    # 3. ANTHROPIC ROUTING
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        
    # 4. GROQ ROUTING (For open-source Llama/Mixtral)
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        # If user passed an NVIDIA key, route open-source models to NVIDIA NIM instead of Groq
        if api_key.startswith("nvapi-"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        else:
            from langchain_groq import ChatGroq
            return ChatGroq(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
            
    # 5. GEMINI ROUTING (DEFAULT FALLBACK)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        # 🛑 CRITICAL ISOLATION: Never send an NVIDIA or OpenAI key to Gemini.
        # Force the fallback to use the hardcoded Google API key from Render Environment.
        google_key = os.getenv("GEMINI_API_KEY") 
        if not google_key and not api_key.startswith("nvapi-") and not api_key.startswith("sk-"):
            google_key = api_key
            
        response = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_key, temperature=0).invoke(prompt)
        # Handle both string and list responses from newer langchain versions
        if isinstance(response, list):
            return str(response[0]) if response else ""
        return str(response.content) if hasattr(response, "content") else str(response)
# =====================================================================

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

    # Get Active Admin LLM Settings
    config = get_llm_config()
    api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY", "")
    selected_llm = config.get("llm_model", "gemini-2.0-flash-lite")

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

    # Model Cascade: Tries the Admin-selected model, then falls back to reliable defaults if it fails
    # Ordered by: user preference -> NVIDIA (best free tier for legal) -> Gemini flash-lite (fast) -> Gemini flash (fallback)
    model_candidates = [selected_llm, "nvidia/nemotron-3-ultra", "gemini-2.0-flash-lite", "gemini-2.0-flash"]

    for model_name in model_candidates:
      try:
        text_res = _invoke_dynamic_llm(prompt, model_name, api_key).strip()

        if text_res.startswith("```json"):
          text_res = text_res[7:]
        if text_res.startswith("```"):
          text_res = text_res[3:]
        if text_res.endswith("```"):
          text_res = text_res[:-3]

        match = re.search(r"\[.*\]", text_res.strip(), re.DOTALL)
        if match:
          evaluated_array = json.loads(match.group(0))

          # Validate that all elements are dicts with required keys
          if isinstance(evaluated_array, list):
            valid_clauses = []
            for item in evaluated_array:
              if isinstance(item, dict) and "clause_type" in item and "extracted_text" in item:
                valid_clauses.append(item)
              elif isinstance(item, str):
                print(f"⚠️ Skipping string item in response: {item[:100]}")
                continue

            if len(valid_clauses) == len(normalized_clauses):
              print(f"✅ Successfully batch-evaluated all {len(valid_clauses)} clauses in 1 call using model: {model_name}")
              return valid_clauses
            elif len(valid_clauses) > 0:
              print(f"✅ Batch evaluated {len(valid_clauses)} valid clauses using model: {model_name}")
              return valid_clauses

      except Exception as e:
        error_str = str(e)
        # Only skip model if it's a SERIOUS error (invalid key, model not found, auth error)
        # Don't skip for rate limits (429) - those are temporary
        if any(serious in error_str for serious in ["INVALID_ARGUMENT", "API_KEY_INVALID", "NOT_FOUND", "PERMISSION_DENIED", "UNAUTHENTICATED", "model not found", "does not exist"]):
          print(f"❌ Model {model_name} has serious error, skipping: {e}")
          continue
        # For rate limits (429) and other transient errors, log but continue to next model
        print(f"⚠️ Model {model_name} transient error, trying next: {e}")
        continue

    print("⚡ All reasoning models rate-limited or unavailable. Retaining normalized clause defaults.")
    return normalized_clauses
