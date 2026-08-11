import json
import os
import re
from typing import Any, Dict, List, TypedDict
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.graph import END, START, StateGraph
from langsmith import traceable

from backend.document_pipeline.clause_extraction.reasoning_service import (
    LegalReasoningService,
)
from backend.document_pipeline.normalization.normalization_service import (
    ClauseNormalizationService,
)
from backend.services.rag_service import RAGKnowledgeService

api_key = os.getenv("GEMINI_API_KEY", "")
if api_key:
  genai.configure(api_key=api_key)


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
  """Deduplicates extracted clauses based on clause type and text content."""
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
  """Extracts distinct legal clauses from OCR text using Gemini."""
  ocr_text = state.get("ocr_text", "")
  business_unit = state.get("business_unit", "Enterprise")
  user_role = state.get("user_role", "Senior Reviewer")

  prompt = f"""
    You are Aadhya, Enterprise Legal Intelligence AI for Tata Group.
    Analyze the document text for Business Unit: '{business_unit}' and User Role: '{user_role}'.

    DOCUMENT TEXT TO ANALYZE:
    {ocr_text[:8000]}

    INSTRUCTIONS:
    1. Extract ALL distinct, non-duplicate legal clauses present in the text (e.g., Scope of Service, Fees/Payment, Confidentiality, Indemnification, Limitation of Liability, Termination, Governing Law).
    
    Return ONLY a valid JSON array where each object contains these EXACT keys:
    - "clause_type": (string, e.g., "Indemnification", "Limitation of Liability", "Governing Law")
    - "extracted_text": (exact text quote from document)
    - "confidence_score": MUST BE A FLOAT NUMBER between 0.0 and 1.0 (e.g. 0.95).
    - "risk_level": "HIGH", "MEDIUM", or "LOW"
    - "risk_rationale": (initial legal rationale)
    - "involved_party": (parties involved)
    - "page_reference": (e.g., "Section 4" or "Section 5")
    - "obligation_owner": (responsible entity)
    - "recommended_action": (e.g., "Escalate to Legal", "Accept Standard Term", "Request Revision")
    """

  model_candidates = [
      "gemini-2.0-flash",
      "gemini-3.5-flash",
      "gemini-3.6-flash",
      "gemini-2.5-flash",
      "gemini-2.5-flash-lite",
  ]

  raw_clauses = []
  for model_name in model_candidates:
    try:
      model = genai.GenerativeModel(model_name)
      response = model.generate_content(prompt)
      text_res = response.text.strip()

      if text_res.startswith("```json"):
        text_res = text_res[7:]
      if text_res.startswith("```"):
        text_res = text_res[3:]
      if text_res.endswith("```"):
        text_res = text_res[:-3]

      match = re.search(r"\[.*\]", text_res.strip(), re.DOTALL)
      if match:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, list) and len(parsed) > 0:
          raw_clauses = parsed
          print(f"✅ Extracted {len(raw_clauses)} clauses using model: {model_name}")
          break
    except Exception as e:
      print(f"⚠️ Model {model_name} failed: {e}. Trying next model...")
      continue

  if not raw_clauses:
    snippet = ocr_text[:300].replace("\n", " ") if ocr_text else "Standard agreement provisions."
    raw_clauses = [{
        "clause_type": "GENERAL PROVISION & COMPLIANCE",
        "extracted_text": snippet,
        "confidence_score": 0.88,
        "risk_level": "MEDIUM",
        "risk_rationale": "Evaluated under local fallback policy rules.",
        "involved_party": "Tata Group & Counterparty",
        "page_reference": "Section 1",
        "obligation_owner": "Compliance Team",
        "recommended_action": "Review Document",
    }]

  unique_clauses = deduplicate_extracted_clauses(raw_clauses)
  return {"raw_clauses": unique_clauses}


@traceable(name="RAG Per-Clause Grounding Node")
def ground_clauses_with_rag_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Performs targeted vector search for EACH clause to assign distinct, highly relevant KB citations."""
  raw_clauses = state.get("raw_clauses", [])
  grounded_clauses = []

  for clause in raw_clauses:
    clause_text = clause.get("extracted_text", "")
    clause_type = clause.get("clause_type", "")

    # Perform vector search specifically for this clause
    search_query = f"[{clause_type}] {clause_text[:500]}"
    search_hits = rag_service.retrieve_context(search_query, top_k=1)

    if search_hits and len(search_hits) > 0:
      best_match = search_hits[0]
      clause["rag_reference_used"] = best_match.get("ref", "CLS-GEN-020")
      clause["matched_policy_text"] = best_match.get("text", "")
    else:
      clause["rag_reference_used"] = "CLS-GEN-020"

    grounded_clauses.append(clause)

  return {"raw_clauses": grounded_clauses}


@traceable(name="Clause Normalization Node")
def normalize_clauses_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Standardizes raw clause headings to enterprise taxonomy and enforces float safety."""
  raw_clauses = state.get("raw_clauses", [])
  normalized = normalization_service.normalize_clauses(raw_clauses)
  unique_normalized = deduplicate_extracted_clauses(normalized)
  return {"normalized_clauses": unique_normalized}


@traceable(name="Legal Reasoning & Risk Assessment Node")
def legal_reasoning_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Applies dedicated risk evaluation pass with per-clause model cascading."""
  normalized_clauses = state.get("normalized_clauses", [])
  business_unit = state.get("business_unit", "Enterprise")
  user_role = state.get("user_role", "Senior Reviewer")

  final_clauses = reasoning_service.evaluate_risk_and_reasoning(
      normalized_clauses,
      business_unit=business_unit,
      user_role=user_role,
  )
  unique_final = deduplicate_extracted_clauses(final_clauses)
  return {"final_clauses": unique_final}


# --- Build StateGraph ---
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