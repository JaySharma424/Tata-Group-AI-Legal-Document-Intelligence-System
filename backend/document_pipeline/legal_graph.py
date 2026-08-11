import json
import os
import re
from typing import Any, Dict, List, TypedDict
import google.generativeai as genai
from langgraph.graph import END, START, StateGraph
from langsmith import traceable

# Import modular pipeline services
from backend.document_pipeline.clause_extraction.reasoning_service import (
    LegalReasoningService,
)
from backend.document_pipeline.normalization.normalization_service import (
    ClauseNormalizationService,
)
from backend.services.rag_service import RAGKnowledgeService

# Configure Gemini API key if present
api_key = os.getenv("GEMINI_API_KEY", "")
if api_key:
  genai.configure(api_key=api_key)


# --- 1. Define Graph State Schema ---
class LegalPipelineState(TypedDict):
  ocr_text: str
  file_path: str
  user_role: str
  business_unit: str
  rag_context: List[Dict[str, Any]]
  raw_clauses: List[Dict[str, Any]]
  normalized_clauses: List[Dict[str, Any]]
  final_clauses: List[Dict[str, Any]]


# --- 2. Instantiate Singleton Pipeline Services ---
rag_service = RAGKnowledgeService()
normalization_service = ClauseNormalizationService()
reasoning_service = LegalReasoningService()


def deduplicate_extracted_clauses(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
  """Deduplicates extracted clauses based on normalized clause type and text content."""
  seen_keys = set()
  unique_clauses = []

  for clause in clauses:
    raw_text = clause.get("extracted_text", "").strip()
    clause_type = clause.get("clause_type", "").strip()
    
    # Create normalized key to catch near-duplicates
    norm_text_snippet = re.sub(r"\s+", " ", raw_text.lower())[:150]
    norm_key = (clause_type.lower(), norm_text_snippet)

    if norm_text_snippet and norm_key not in seen_keys:
      seen_keys.add(norm_key)
      unique_clauses.append(clause)

  return unique_clauses


# --- 3. Define StateGraph Nodes ---

@traceable(name="LLM Clause Extraction Node")
def extract_clauses_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Step 1: Extract distinct clauses FIRST (without worrying about RAG citations yet)."""
  ocr_text = state.get("ocr_text", "")
  business_unit = state.get("business_unit", "Enterprise")
  user_role = state.get("user_role", "Senior Reviewer")

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
    - "confidence_score": MUST BE A FLOAT NUMBER between 0.0 and 1.0 (e.g. 0.95).
    - "risk_level": "HIGH", "MEDIUM", or "LOW"
    - "risk_rationale": "Pending Reasoning"
    - "involved_party": (parties involved)
    - "rag_reference_used": "PENDING"
    - "page_reference": (e.g., "Section 4" or "Section 5")
    - "obligation_owner": (responsible entity)
    - "recommended_action": (e.g., "Review Document")
    """

  model_candidates = ["gemini-2.0-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]

  raw_clauses = []
  for model_name in model_candidates:
    try:
      model = genai.GenerativeModel(model_name)
      response = model.generate_content(prompt)
      text_res = response.text.strip()

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
      continue

  if not raw_clauses:
    raw_clauses = [{
        "clause_type": "GENERAL PROVISION",
        "extracted_text": ocr_text[:300].replace("\n", " "),
        "confidence_score": 0.88,
        "risk_level": "MEDIUM",
        "risk_rationale": "Evaluated under default compliance parameters.",
        "rag_reference_used": "PENDING",
    }]

  unique_clauses = deduplicate_extracted_clauses(raw_clauses)
  return {"raw_clauses": unique_clauses}


@traceable(name="RAG Per-Clause Grounding Node")
def ground_clauses_with_rag_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Step 2: Perform targeted Qdrant Vector search for EACH individual clause to get unique IDs."""
  raw_clauses = state.get("raw_clauses", [])
  grounded_clauses = []
  all_retrieved_context = []

  for clause in raw_clauses:
    clause_text = clause.get("extracted_text", "")
    clause_type = clause.get("clause_type", "")

    # Query Qdrant with THIS specific clause text
    search_query = f"[{clause_type}] {clause_text[:400]}"
    search_hits = rag_service.retrieve_context(search_query, top_k=1)

    if search_hits and len(search_hits) > 0:
      best_match = search_hits[0]
      # Lock in the EXACT Qdrant database ID (e.g., CLS-LIAB-001, TAX-1)
      clause["rag_reference_used"] = best_match.get("ref", "TAX-1")
      clause["matched_policy_text"] = best_match.get("text", "")
      all_retrieved_context.append(best_match)
    else:
      clause["rag_reference_used"] = "TAX-1"

    grounded_clauses.append(clause)

  return {
      "raw_clauses": grounded_clauses,
      "rag_context": all_retrieved_context
  }


@traceable(name="Clause Normalization Node")
def normalize_clauses_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Step 3: Standardize headings to enterprise taxonomy."""
  raw_clauses = state.get("raw_clauses", [])
  normalized = normalization_service.normalize_clauses(raw_clauses)
  unique_normalized = deduplicate_extracted_clauses(normalized)
  return {"normalized_clauses": unique_normalized}


@traceable(name="Legal Reasoning & Risk Assessment Node")
def legal_reasoning_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Step 4: Execute LLM risk evaluation AND forcefully apply the Citation Lock."""
  normalized_clauses = state.get("normalized_clauses", [])
  business_unit = state.get("business_unit", "Enterprise")
  user_role = state.get("user_role", "Senior Reviewer")

  # The reasoning_service runs its own LLM prompt and will hallucinate IDs
  final_clauses = reasoning_service.evaluate_risk_and_reasoning(
      normalized_clauses,
      business_unit=business_unit,
      user_role=user_role,
  )

  # --- THE CITATION LOCK ---
  # Build a map of the exact IDs we retrieved from Qdrant in Step 2
  grounding_map = {}
  for nc in normalized_clauses:
      key = re.sub(r"\s+", " ", nc.get("extracted_text", "").lower())[:100]
      grounding_map[key] = nc.get("rag_reference_used", "TAX-1")

  # Forcefully overwrite the hallucinated ID with our locked Qdrant ID
  for fc in final_clauses:
      key = re.sub(r"\s+", " ", fc.get("extracted_text", "").lower())[:100]
      if key in grounding_map:
          fc["rag_reference_used"] = grounding_map[key]
      elif not fc.get("rag_reference_used") or fc.get("rag_reference_used") == "PENDING":
          fc["rag_reference_used"] = "TAX-1"

  unique_final = deduplicate_extracted_clauses(final_clauses)
  return {"final_clauses": unique_final}


# --- 4. Build and Compile StateGraph ---
workflow = StateGraph(LegalPipelineState)

# Notice we removed the global "retrieve_rag_context_node" entirely
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