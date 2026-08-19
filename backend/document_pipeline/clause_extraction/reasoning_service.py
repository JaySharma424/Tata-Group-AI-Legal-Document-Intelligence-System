import json
import os
import re
import ast
from typing import Any, Dict, List

from backend.services.llm_config import get_llm_config

def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    if not api_key or not model_name:
        raise ValueError("ADMIN_CONFIG_MISSING: No API Key or Model found in Admin Settings.")
        
    model_lower = model_name.lower()
    
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0, max_tokens=4096, timeout=120).invoke(prompt).content
        
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0, max_retries=0).invoke(prompt).content
        
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0, max_retries=0).invoke(prompt).content
        
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        if api_key.startswith("nvapi-"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0, max_tokens=4096, timeout=120).invoke(prompt).content
        else:
            from langchain_groq import ChatGroq
            return ChatGroq(model=model_name, api_key=api_key, temperature=0, max_retries=0).invoke(prompt).content
            
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        response = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0, max_retries=0).invoke(prompt)
        if isinstance(response, list): return str(response[0]) if response else ""
        return str(response.content) if hasattr(response, "content") else str(response)

def robust_json_harvester(raw_text: str) -> List[Dict[str, Any]]:
    if not raw_text: return []
    text = re.sub(r"<think>.*?</think>", "", str(raw_text), flags=re.DOTALL)
    md_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if md_match: text = md_match.group(1)

    extracted_objects = []
    depth = 0
    start_idx = -1
    
    for i, char in enumerate(text):
        if char == '{':
            if depth == 0: start_idx = i
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start_idx != -1:
                obj_str = text[start_idx:i+1].replace('\n', ' ').replace('\r', ' ')
                try:
                    parsed = json.loads(obj_str)
                    extracted_objects.append(parsed)
                except json.JSONDecodeError:
                    try:
                        python_str = obj_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                        parsed = ast.literal_eval(python_str)
                        if isinstance(parsed, dict):
                            extracted_objects.append(parsed)
                    except Exception:
                        continue 
    return extracted_objects

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
        You are Senior Legal Counsel at Tata Group evaluating contracts for the '{business_unit}' business unit from the perspective of a '{user_role}'.
        Analyze the following array of normalized contract clauses and their matched corporate RAG guidelines:
        {clauses_json_str}
        
        INSTRUCTIONS:
        1. Determine the risk level strictly as: "HIGH", "MEDIUM", or "LOW".
        2. Provide a professional legal rationale explaining exposure.
        3. Specify the appropriate RAG policy reference ID cited from the context.
        4. Suggest a recommended action.
        5. **AUTOMATED REMEDIATION:** If risk level is HIGH or MEDIUM, draft a precise "proposed_redline" contract clause written in formal legal English that fully complies with Tata corporate policies. If risk is LOW, set "proposed_redline" to null or repeat the original text.
        
        Return ONLY a valid JSON array matching the exact length and order of the input clauses. Each object in the array MUST contain these exact keys:
        ["clause_type", "extracted_text", "confidence_score", "risk_level", "risk_rationale", "involved_party", "rag_reference_used", "page_reference", "obligation_owner", "recommended_action", "proposed_redline"]
        
        CRITICAL INSTRUCTION: You are a JSON parser. Output NOTHING but the raw JSON array. NO explanations, NO thinking process, NO markdown.
        """

    if selected_llm and api_key:
      try:
        raw_output = _invoke_dynamic_llm(prompt, selected_llm, api_key)
        parsed_list = robust_json_harvester(raw_output)

        valid_clauses = [item for item in parsed_list if isinstance(item, dict) and "clause_type" in item and "extracted_text" in item]

        if len(valid_clauses) == len(normalized_clauses):
            print(f"✅ Successfully batch-evaluated all {len(valid_clauses)} clauses in 1 call using model: {selected_llm}")
            return valid_clauses
        elif len(valid_clauses) > 0:
            print(f"✅ Batch evaluated {len(valid_clauses)} valid clauses using model: {selected_llm}")
            return valid_clauses

      except Exception as e:
          print(f"❌ Model {selected_llm} failed with API error: {e}")

    print("⚡ Admin LLM configuration invalid or failed. Retaining normalized clause defaults.")
    return normalized_clauses
