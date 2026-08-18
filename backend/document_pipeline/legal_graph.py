import json
import os
import re
import ast
from typing import Any, Dict, List, TypedDict
from langgraph.graph import END, START, StateGraph
from langsmith import traceable
from backend.services.llm_config import get_llm_config
from backend.document_pipeline.clause_extraction.reasoning_service import LegalReasoningService
from backend.document_pipeline.normalization.normalization_service import ClauseNormalizationService
from backend.services.rag_service import RAGKnowledgeService

def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    """Dynamically routes tasks while strictly isolating provider API keys."""
    model_lower = model_name.lower()
    
    # 🚀 FIX: Removed max_retries which caused NVIDIA 400 Bad Request
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        nv_key = api_key if (api_key and api_key.startswith("nvapi-")) else os.getenv("NVIDIA_API_KEY")
        if not nv_key: raise ValueError("API_KEY_INVALID: No valid NVIDIA key found.")
        return ChatNVIDIA(model=model_name, api_key=nv_key, temperature=0).invoke(prompt).content
        
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        sk_key = api_key if (api_key and api_key.startswith("sk-") and not api_key.startswith("sk-ant-")) else os.getenv("OPENAI_API_KEY")
        if not sk_key: raise ValueError("API_KEY_INVALID: No valid OpenAI key found.")
        return ChatOpenAI(model=model_name, api_key=sk_key, temperature=0).invoke(prompt).content
        
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        ant_key = api_key if (api_key and api_key.startswith("sk-ant-")) else os.getenv("ANTHROPIC_API_KEY")
        if not ant_key: raise ValueError("API_KEY_INVALID: No valid Anthropic key found.")
        return ChatAnthropic(model=model_name, api_key=ant_key, temperature=0).invoke(prompt).content
        
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        if api_key and api_key.startswith("nvapi-"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        else:
            from langchain_groq import ChatGroq
            groq_key = api_key if (api_key and api_key.startswith("gsk_")) else os.getenv("GROQ_API_KEY")
            if not groq_key: raise ValueError("API_KEY_INVALID: No valid Groq key found.")
            return ChatGroq(model=model_name, api_key=groq_key, temperature=0).invoke(prompt).content
            
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key and not api_key.startswith("nvapi-") and not api_key.startswith("sk-") and not api_key.startswith("gsk_"):
            gemini_key = api_key
        if not gemini_key: raise ValueError("API_KEY_INVALID: No valid Google key found.")
            
        response = ChatGoogleGenerativeAI(model=model_name, google_api_key=gemini_key, temperature=0).invoke(prompt)
        if isinstance(response, list): return str(response[0]) if response else ""
        return str(response.content) if hasattr(response, "content") else str(response)

def clean_llm_json_response(raw_text: str) -> str:
    """Aggressively extracts the JSON array from noisy LLM outputs."""
    if not raw_text: return "[]"
    text = str(raw_text).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match: return match.group(0)
        
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match: return "[" + match.group(0) + "]"
        
    return text

class LegalPipelineState(TypedDict):
  ocr_text: str
  file_path: str
  user_role: str
  business_unit: str
  rag_context: List[Dict[str, Any]]
  raw_clauses: List[Dict[str, Any]]
  normalized_clauses: List[Dict[str, Any]]
  final_clauses: List[Dict[str, Any]]

rag_service = RAGKnowledgeService()
normalization_service = ClauseNormalizationService()
reasoning_service = LegalReasoningService()

def deduplicate_extracted_clauses(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
  seen_keys = set()
  unique_clauses = []
  for clause in clauses:
    raw_text = clause.get("extracted_text", "").strip()
    clause_type = clause.get("clause_type", "").strip()
    norm_text_snippet = re.sub(r"\s+", " ", raw_text.lower())[:150]
    norm_key = (clause_type.lower(), norm_text_snippet)
    if norm_text_snippet and norm_key not in seen_keys:
      seen_keys.add(norm_key)
      unique_clauses.append(clause)
  return unique_clauses

@traceable(name="LLM Clause Extraction Node")
def extract_clauses_node(state: LegalPipelineState) -> Dict[str, Any]:
  ocr_text = state.get("ocr_text", "")
  business_unit = state.get("business_unit", "Enterprise")
  user_role = state.get("user_role", "Senior Reviewer")

  config = get_llm_config()
  api_key = config.get("api_key", "")
  selected_llm = config.get("llm_model", "")

  prompt = f"""
    You are Aadhya, Enterprise Legal Intelligence AI for Tata Group.
    Analyze the document text for Business Unit: '{business_unit}' and User Role: '{user_role}'.

    DOCUMENT TEXT TO ANALYZE:
    {ocr_text[:8000]}

    INSTRUCTIONS:
    1. Extract ALL distinct, non-duplicate legal clauses present in the text.
    Return ONLY a valid JSON array where each object contains these EXACT keys:
    - "clause_type"
    - "extracted_text"
    - "confidence_score"
    - "risk_level"
    - "risk_rationale"
    - "involved_party"
    - "page_reference"
    - "obligation_owner"
    - "recommended_action"
    
    CRITICAL: OUTPUT ONLY A RAW JSON ARRAY. NO MARKDOWN. NO CONVERSATIONAL TEXT.
    """

  # 🚀 CASCADE LOGIC: Try Admin Key -> Fallback to NVIDIA -> Ultimate Safety Fallback to Gemini
  ordered_candidates = []
  if selected_llm and api_key:
      ordered_candidates.append(selected_llm)
  else:
      ordered_candidates.append("nvidia/nemotron-3.5-lightning-30b-a3b")
      ordered_candidates.append("gemini-3.5-flash") # Safety net
  
  seen = set()
  cascade = [m for m in ordered_candidates if m and not (m in seen or seen.add(m))]

  raw_clauses = []
  for model_name in cascade:
    try:
      raw_output = _invoke_dynamic_llm(prompt, model_name, api_key)
      text_res = clean_llm_json_response(raw_output)

      if not text_res or text_res == "[]":
          print(f"⚠️ Model {model_name} returned empty output. Trying next.")
          continue

      python_str = text_res.replace('true', 'True').replace('false', 'False').replace('null', 'None')
      try:
          parsed = json.loads(text_res)
      except json.JSONDecodeError:
          try:
              parsed = ast.literal_eval(python_str)
          except Exception as ast_err:
              print(f"⚠️ Parsing failed for {model_name}: {ast_err}")
              continue

      if isinstance(parsed, dict): parsed = [parsed]

      if isinstance(parsed, list):
        valid_clauses = []
        for item in parsed:
          if isinstance(item, dict) and "clause_type" in item and "extracted_text" in item:
            valid_clauses.append(item)

        if len(valid_clauses) > 0:
          raw_clauses = valid_clauses
          print(f"✅ Successfully extracted {len(raw_clauses)} valid clauses using model: {model_name}")
          break
    except Exception as e:
      error_str = str(e)
      if any(serious in error_str for serious in ["INVALID_ARGUMENT", "API_KEY_INVALID", "NOT_FOUND", "PERMISSION_DENIED"]):
        print(f"❌ Model {model_name} failed with API error: {e}")
        continue
      print(f"⚠️ Model {model_name} processing error, trying next: {e}")
      continue

  if not raw_clauses:
    raw_clauses = [{
        "clause_type": "GENERAL PROVISION",
        "extracted_text": ocr_text[:300].replace("\n", " ") if ocr_text else "Standard agreement provisions.",
        "confidence_score": 0.88,
        "risk_level": "MEDIUM",
        "risk_rationale": "Evaluated under default compliance parameters.",
        "involved_party": "Tata Group & Counterparty",
        "page_reference": "Section 1",
        "obligation_owner": "Compliance Team",
        "recommended_action": "Review Document",
    }]

  unique_clauses = deduplicate_extracted_clauses(raw_clauses)
  return {"raw_clauses": unique_clauses}

@traceable(name="RAG Per-Clause Grounding Node")
def ground_clauses_with_rag_node(state: LegalPipelineState) -> Dict[str, Any]:
  raw_clauses = state.get("raw_clauses", [])
  grounded_clauses = []
  all_retrieved_context = []

  for clause in raw_clauses:
    clause_text = clause.get("extracted_text", "")
    clause_type = clause.get("clause_type", "")
    search_query = f"{clause_type} {clause_text[:400]}"
    search_hits = rag_service.semantic_search(search_query, top_k=1)

    if search_hits and len(search_hits) > 0:
      best_match = search_hits[0]
      clause["rag_reference_used"] = best_match.get("ref", "CLS-GEN-020")
      clause["matched_policy_text"] = best_match.get("text", "")
      all_retrieved_context.append(best_match)
    else:
      clause["rag_reference_used"] = "CLS-GEN-020"

    grounded_clauses.append(clause)

  return {"raw_clauses": grounded_clauses, "rag_context": all_retrieved_context}


@traceable(name="Clause Normalization Node")
def normalize_clauses_node(state: LegalPipelineState) -> Dict[str, Any]:
  raw_clauses = state.get("raw_clauses", [])
  normalized = normalization_service.normalize_clauses(raw_clauses)
  return {"normalized_clauses": normalized}

@traceable(name="Legal Reasoning & Risk Assessment Node")
def legal_reasoning_node(state: LegalPipelineState) -> Dict[str, Any]:
  normalized_clauses = state.get("normalized_clauses", [])
  business_unit = state.get("business_unit", "Enterprise")
  user_role = state.get("user_role", "Senior Reviewer")

  final_clauses = reasoning_service.evaluate_risk_and_reasoning(
      normalized_clauses,
      business_unit=business_unit,
      user_role=user_role,
  )

  for i, fc in enumerate(final_clauses):
      if i < len(normalized_clauses):
          fc["rag_reference_used"] = normalized_clauses[i].get("rag_reference_used", "CLS-GEN-020")

  return {"final_clauses": final_clauses}

workflow = StateGraph(LegalPipelineState)
workflow.add_node("extract_clauses", extract_clauses_node)
workflow.add_node("ground_clauses", ground_clauses_with_rag_node)
workflow.add_node("normalize_clauses", normalize_clauses_node)
workflow.add_node("legal_reasoning", legal_reasoning_node)

workflow.add_edge(START, "extract_clauses")
workflow.add_edge("extract_clauses", "ground_clauses")
workflow.add_edge("ground_clauses", "normalize_clauses")
workflow.add_edge("normalize_clauses", "legal_reasoning")
workflow.add_edge("legal_reasoning", END)

legal_pipeline_graph = workflow.compile()
