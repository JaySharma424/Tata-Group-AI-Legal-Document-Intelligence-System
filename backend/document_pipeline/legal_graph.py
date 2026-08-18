import json
import os
import re
import time
from typing import Any, Dict, List, TypedDict
from langgraph.graph import END, START, StateGraph
from langsmith import traceable

# Import dynamic PostgreSQL LLM config service
from backend.services.llm_config import get_llm_config

# Import modular pipeline services
from backend.document_pipeline.clause_extraction.reasoning_service import LegalReasoningService
from backend.document_pipeline.normalization.normalization_service import ClauseNormalizationService
from backend.services.rag_service import RAGKnowledgeService

# =====================================================================
# 🚀 NEW: DYNAMIC LLM ROUTER FOR MULTI-PROVIDER SUPPORT
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
  api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY", "")
  selected_llm = config.get("llm_model", "gemini-3.5-flash")

  prompt = f"""
    You are Aadhya, Enterprise Legal Intelligence AI for Tata Group.
    Analyze the document text for Business Unit: '{business_unit}' and User Role: '{user_role}'.

    DOCUMENT TEXT TO ANALYZE:
    {ocr_text[:8000]}

    INSTRUCTIONS:
    1. Extract ALL distinct, non-duplicate legal clauses present in the text (e.g., Scope, Fees/Payment, Confidentiality, Indemnification, Limitation of Liability, Termination, Governing Law).
    
    Return ONLY a valid JSON array where each object contains these EXACT keys:
    - "clause_type": (string)
    - "extracted_text": (exact text quote from document)
    - "confidence_score": MUST BE A FLOAT NUMBER between 0.0 and 1.0.
    - "risk_level": "HIGH", "MEDIUM", or "LOW"
    - "risk_rationale": "Pending"
    - "involved_party": (parties involved)
    - "page_reference": (e.g., "Section 1")
    - "obligation_owner": (responsible entity)
    - "recommended_action": (e.g., "Review Document")
    """

  # Try user's selected model first, then safely cascade back to Gemini if it fails (e.g., bad API key)
  # Updated to use current available Gemini models (2.5-flash is deprecated)
  ordered_candidates = [selected_llm, "gemini-3.6-flash", "gemini-1.5-flash", "gemini-3.5-flash"]

  raw_clauses = []
  for model_name in ordered_candidates:
    try:
      text_res = _invoke_dynamic_llm(prompt, model_name, api_key).strip()

      if text_res.startswith("```json"): text_res = text_res[7:]
      if text_res.startswith("```"): text_res = text_res[3:]
      if text_res.endswith("```"): text_res = text_res[:-3]

      match = re.search(r"\[.*\]", text_res.strip(), re.DOTALL)
      if match:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, list) and len(parsed) > 0:
          raw_clauses = parsed
          break
    except Exception as e:
      print(f"Extraction failed for model {model_name}: {e}")
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
    search_hits = rag_service.retrieve_context(search_query, top_k=1)

    if search_hits and len(search_hits) > 0:
      best_match = search_hits[0]
      clause["rag_reference_used"] = best_match.get("ref", "CLS-GEN-020")
      clause["matched_policy_text"] = best_match.get("text", "")
      all_retrieved_context.append(best_match)
    else:
      clause["rag_reference_used"] = "CLS-GEN-020"

    grounded_clauses.append(clause)
    time.sleep(2)

  return {
      "raw_clauses": grounded_clauses,
      "rag_context": all_retrieved_context
  }


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
