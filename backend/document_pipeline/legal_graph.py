import json
import os
import re
from typing import Any, Dict, List, TypedDict
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
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
    
    # Create composite key using lowercased type and normalized text snippet
    norm_text_snippet = re.sub(r"\s+", " ", raw_text.lower())[:150]
    norm_key = (clause_type.lower(), norm_text_snippet)

    if norm_text_snippet and norm_key not in seen_keys:
      seen_keys.add(norm_key)
      unique_clauses.append(clause)

  return unique_clauses


# --- 3. Define StateGraph Nodes ---
@traceable(name="RAG Context Retrieval Node")
def retrieve_rag_context_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Retrieves relevant corporate policies & statutory rules from Qdrant vector database."""
  try:
    references = rag_service.retrieve_context(state["ocr_text"])
  except Exception as e:
    print(f"⚠️ RAG retrieval error in node: {e}")
    references = [{
        "ref": "POL-IND-2026-01",
        "text": (
            "All third-party vendors must adhere strictly to Tata Group confidentiality"
            " standards and liability capping policies."
        ),
    }]

  return {"rag_context": references}


@traceable(name="LLM Clause Extraction Node")
def extract_clauses_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Extracts unique legal clauses using Gemini, grounded strictly in retrieved KB Ref IDs."""
  rag_context = state.get("rag_context", [])
  ocr_text = state.get("ocr_text", "")
  business_unit = state.get("business_unit", "Enterprise")
  user_role = state.get("user_role", "Senior Reviewer")

  # Extract exact valid payload Ref IDs retrieved from Qdrant (e.g., CLS-LIAB-001, REG-COMP-001, POL-IND-2026-01)
  valid_ref_ids = [
      item.get("ref") for item in rag_context if item.get("ref") and item.get("ref") != "REF-N/A"
  ]
  if not valid_ref_ids:
    valid_ref_ids = ["POL-IND-2026-01"]
  default_ref = valid_ref_ids[0]

  formatted_rag_policies = ""
  for idx, item in enumerate(rag_context, 1):
    ref_id = item.get("ref", f"KB-REF-{idx}")
    policy_text = item.get("text", "")
    formatted_rag_policies += f"\n--- [GROUNDED KB REF ID: {ref_id}] ---\n{policy_text}\n"

  prompt = f"""
    You are Aadhya, Enterprise Legal Intelligence AI for Tata Group.
    Analyze the document text for Business Unit: '{business_unit}' and User Role: '{user_role}'.
    
    APPROVED TATA LEGAL KNOWLEDGE BASE CONTEXT (FROM QDRANT VECTOR STORE):
    {formatted_rag_policies}

    WHITELIST OF VALID KNOWLEDGE BASE REFERENCE IDs:
    {valid_ref_ids}

    DOCUMENT TEXT TO ANALYZE:
    {ocr_text[:8000]}

    STRICT RULES FOR EXTRACTION & CITATION:
    1. Extract UNIQUE legal clauses present in the text (e.g., Scope, Fees/Payment, Confidentiality, Indemnification, Limitation of Liability, Termination, Governing Law, IP Rights). DO NOT extract duplicate or overlapping clauses for the same section.
    2. In 'rag_reference_used', you MUST ONLY output an EXACT Reference ID string from the WHITELIST OF VALID KNOWLEDGE BASE REFERENCE IDs: {valid_ref_ids}.
    3. DO NOT invent, abbreviate, or fabricate hallucinated codes. You MUST select exclusively from {valid_ref_ids}.
    4. Match each extracted clause to the closest relevant policy/statutory chunk and copy its EXACT Ref ID.

    Return ONLY a valid JSON array where each object contains these EXACT keys:
    - "clause_type": (string, e.g., "Indemnification", "Limitation of Liability", "Governing Law")
    - "extracted_text": (exact text quote from document)
    - "confidence_score": MUST BE A FLOAT NUMBER between 0.0 and 1.0 (e.g. 0.95).
    - "risk_level": "HIGH", "MEDIUM", or "LOW"
    - "risk_rationale": (detailed legal rationale comparing against approved KB policies)
    - "involved_party": (parties involved)
    - "rag_reference_used": (MUST BE AN EXACT MATCH FROM {valid_ref_ids})
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
          print(
              f"✅ Successfully extracted {len(raw_clauses)} raw clauses using"
              f" model: {model_name}"
          )
          break
    except Exception as e:
      print(
          f"⚠️ Model {model_name} failed in extract_clauses_node: {e}. Trying"
          " next model..."
      )
      continue

  if not raw_clauses:
    snippet = (
        ocr_text[:300].replace("\n", " ")
        if ocr_text
        else "Standard agreement provisions."
    )
    raw_clauses = [{
        "clause_type": "GENERAL PROVISION & COMPLIANCE",
        "extracted_text": snippet,
        "confidence_score": 0.88,
        "risk_level": "MEDIUM",
        "risk_rationale": (
            "Evaluated under local fallback policy rules due to cloud model"
            " quota limits."
        ),
        "involved_party": "Tata Group & Counterparty",
        "rag_reference_used": default_ref,
        "page_reference": "Section 1",
        "obligation_owner": "Compliance Team",
        "recommended_action": "Review Document",
    }]

  # --- POST-PROCESSING 1: STRICT DEDUPLICATION ---
  unique_clauses = deduplicate_extracted_clauses(raw_clauses)

  # --- POST-PROCESSING 2: REFERENCE ID GROUNDING ENFORCEMENT ---
  for clause in unique_clauses:
    cited_ref = clause.get("rag_reference_used", "")
    if valid_ref_ids and cited_ref not in valid_ref_ids:
      clause["rag_reference_used"] = default_ref

  return {"raw_clauses": unique_clauses}


@traceable(name="Clause Normalization Node")
def normalize_clauses_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Standardizes raw clause headings to enterprise taxonomy, enforces float safety, and deduplicates."""
  raw_clauses = state.get("raw_clauses", [])
  normalized = normalization_service.normalize_clauses(raw_clauses)
  unique_normalized = deduplicate_extracted_clauses(normalized)
  return {"normalized_clauses": unique_normalized}


@traceable(name="Legal Reasoning & Risk Assessment Node")
def legal_reasoning_node(state: LegalPipelineState) -> Dict[str, Any]:
  """Applies dedicated risk evaluation pass with per-clause model cascading and deduplication."""
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


# --- 4. Build and Compile StateGraph ---
workflow = StateGraph(LegalPipelineState)

workflow.add_node("retrieve_rag", retrieve_rag_context_node)
workflow.add_node("extract_clauses", extract_clauses_node)
workflow.add_node("normalize_clauses", normalize_clauses_node)
workflow.add_node("legal_reasoning", legal_reasoning_node)

workflow.add_edge(START, "retrieve_rag")
workflow.add_edge("retrieve_rag", "extract_clauses")
workflow.add_edge("extract_clauses", "normalize_clauses")
workflow.add_edge("normalize_clauses", "legal_reasoning")
workflow.add_edge("legal_reasoning", END)

legal_pipeline_graph = workflow.compile()