import json
import os
import re
import ast
from typing import Any, Dict, List

from backend.services.llm_config import get_llm_config

def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    model_lower = model_name.lower()
    
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        nv_key = api_key if (api_key and api_key.startswith("nvapi-")) else os.getenv("NVIDIA_API_KEY")
        if not nv_key: raise ValueError("API_KEY_INVALID: No valid NVIDIA key found.")
        return ChatNVIDIA(model=model_name, api_key=nv_key, temperature=0, max_retries=1).invoke(prompt).content
        
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        sk_key = api_key if (api_key and api_key.startswith("sk-") and not api_key.startswith("sk-ant-")) else os.getenv("OPENAI_API_KEY")
        if not sk_key: raise ValueError("API_KEY_INVALID: No valid OpenAI key found.")
        return ChatOpenAI(model=model_name, api_key=sk_key, temperature=0, max_retries=1).invoke(prompt).content
        
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        ant_key = api_key if (api_key and api_key.startswith("sk-ant-")) else os.getenv("ANTHROPIC_API_KEY")
        if not ant_key: raise ValueError("API_KEY_INVALID: No valid Anthropic key found.")
        return ChatAnthropic(model=model_name, api_key=ant_key, temperature=0, max_retries=1).invoke(prompt).content
        
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        if api_key and api_key.startswith("nvapi-"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0, max_retries=1).invoke(prompt).content
        else:
            from langchain_groq import ChatGroq
            groq_key = api_key if (api_key and api_key.startswith("gsk_")) else os.getenv("GROQ_API_KEY")
            if not groq_key: raise ValueError("API_KEY_INVALID: No valid Groq key found.")
            return ChatGroq(model=model_name, api_key=groq_key, temperature=0, max_retries=1).invoke(prompt).content
            
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key and not api_key.startswith("nvapi-") and not api_key.startswith("sk-") and not api_key.startswith("gsk_"):
            gemini_key = api_key
        if not gemini_key: raise ValueError("API_KEY_INVALID: No valid Google key found.")
            
        response = ChatGoogleGenerativeAI(model=model_name, google_api_key=gemini_key, temperature=0, max_retries=1).invoke(prompt)
        if isinstance(response, list): return str(response[0]) if response else ""
        return str(response.content) if hasattr(response, "content") else str(response)

def clean_llm_json_response(raw_text: str) -> str:
    if not raw_text: return "[]"
    text = str(raw_text).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match: return match.group(0)
        
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match: return "[" + match.group(0) + "]"
        
    return text

class LegalReasoningService:
  def evaluate_risk_and_reasoning(
      self,
      normalized_clauses: List[Dict[str, Any]],
      business_unit: str,
      user_role: str,
  ) -> List[Dict[str, Any]]:
    
    if not normalized_clauses: return []

    config = get_llm_config()
    api_key = config.get("api_key", "")
    selected_llm = config.get("llm_model", "")

    clauses_json_str = json.dumps(normalized_clauses, indent=2)

    prompt = f"""
        You are Aadhya a Senior Legal Counsel at Tata Group evaluating contracts for the '{business_unit}' business unit from the perspective of a '{user_role}'.
        Analyze the following array of normalized contract clauses:
        {clauses_json_str}
        
        INSTRUCTIONS:
        1. Determine the risk level strictly as: "HIGH", "MEDIUM", or "LOW".
        2. Provide a professional legal rationale explaining exposure.
        3. Specify the appropriate RAG policy reference ID cited from the context.
        4. Suggest a recommended action.
        
        Return ONLY a valid JSON array matching the exact length and order of the input clauses. Each object in the array MUST contain these exact keys:
        ["clause_type", "extracted_text", "confidence_score", "risk_level", "risk_rationale", "involved_party", "rag_reference_used", "page_reference", "obligation_owner", "recommended_action"]
        
        CRITICAL: OUTPUT ONLY A RAW JSON ARRAY. NO MARKDOWN. NO CONVERSATIONAL TEXT.
        """

    # 🚀 GOAL 1: If Admin Key exists, use it. Otherwise, default to NVIDIA via Render Env.
    ordered_candidates = []
    if selected_llm and api_key:
        ordered_candidates.append(selected_llm)
    else:
        ordered_candidates.append("nvidia/nemotron-3.5-lightning-30b-a3b")
    
    seen = set()
    cascade = [m for m in ordered_candidates if m and not (m in seen or seen.add(m))]

    for model_name in cascade:
      try:
        raw_output = _invoke_dynamic_llm(prompt, model_name, api_key)
        text_res = clean_llm_json_response(raw_output)

        if not text_res or text_res == "[]":
            print(f"⚠️ Model {model_name} returned empty output. Trying next.")
            continue

        python_str = text_res.replace('true', 'True').replace('false', 'False').replace('null', 'None')
        try:
            evaluated_array = json.loads(text_res)
        except json.JSONDecodeError:
            try:
                evaluated_array = ast.literal_eval(python_str)
            except Exception as ast_err:
                print(f"⚠️ Parsing failed for {model_name}: {ast_err}")
                continue
            
        if isinstance(evaluated_array, dict): evaluated_array = [evaluated_array]

        if isinstance(evaluated_array, list):
          valid_clauses = []
          for item in evaluated_array:
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
        if any(serious in error_str for serious in ["INVALID_ARGUMENT", "API_KEY_INVALID", "NOT_FOUND", "PERMISSION_DENIED"]):
          print(f"❌ Model {model_name} failed with API error: {e}")
          continue
        print(f"⚠️ Model {model_name} processing error, trying next: {e}")
        continue

    print("⚡ All reasoning models rate-limited or unavailable. Retaining normalized clause defaults.")
    return normalized_clauses
