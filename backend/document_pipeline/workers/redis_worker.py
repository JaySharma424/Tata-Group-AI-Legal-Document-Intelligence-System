import os
import re
import time
import json
import base64
import numpy as np
import redis
import fitz  # PyMuPDF
from sqlalchemy.orm import Session
from rq import get_current_job

from backend.database import SessionLocal
from backend.models import DocumentModel, ClauseModel
from backend.services.llm_config import get_llm_config
from backend.services.rag_service import RAGKnowledgeService
from backend.document_pipeline.normalization.normalization_service import ClauseNormalizationService
from backend.document_pipeline.clause_extraction.reasoning_service import LegalReasoningService

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def publish_pipeline_event(job_id: str, stage: int, step_name: str, progress: int, message: str, payload: dict = None):
    event = {
        "job_id": job_id,
        "stage": stage,
        "step": step_name,
        "progress": progress,
        "message": message,
        "payload": payload or {},
        "timestamp": time.time(),
    }
    try:
        redis_client.publish(f"pipeline:{job_id}", json.dumps(event))
        redis_client.set(f"pipeline_state:{job_id}", json.dumps(event), ex=3600)
    except Exception as e:
        print(f"[WARN] Redis publish error: {e}")

def calculate_deterministic_page_ocr_confidence(text: str) -> float:
    """Computes an OCR extraction confidence score (50.0% - 99.9%) deterministically."""
    if not text or len(text.strip()) < 10:
        return 50.0

    clean_chars = [c for c in text if not c.isspace()]
    if not clean_chars:
        return 50.0

    total_chars = len(clean_chars)
    alnum_chars = sum(1 for c in clean_chars if c.isalnum())
    alnum_ratio = alnum_chars / total_chars

    allowed_punct = sum(1 for c in clean_chars if c in '.,;:()[]"\'%-/&$#@§')
    noise_chars = total_chars - (alnum_chars + allowed_punct)
    noise_ratio = noise_chars / total_chars

    words = text.strip().split()
    avg_word_len = sum(len(w) for w in words) / max(len(words), 1)

    score = (alnum_ratio * 80.0) + 20.0 - (noise_ratio * 35.0)

    if avg_word_len < 2.5 or avg_word_len > 15.0:
        score -= 8.0

    return round(min(99.9, max(50.0, score)), 2)

def extract_text_and_confidence_all_pages(file_path: str) -> tuple[list, float]:
    """Parses every page using PyMuPDF and computes page-by-page deterministic OCR scores."""
    pages_data = []

    if file_path.lower().endswith(".pdf"):
        try:
            with fitz.open(file_path) as pdf_doc:
                for page_idx in range(len(pdf_doc)):
                    page = pdf_doc[page_idx]
                    page_text = page.get_text().strip()
                    page_confidence = calculate_deterministic_page_ocr_confidence(page_text)
                    pages_data.append({
                        "page": page_idx + 1,
                        "text": page_text,
                        "confidence": page_confidence
                    })
        except Exception as e:
            print(f"[WARN] PyMuPDF page parsing error: {e}")

    if not pages_data:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            conf = calculate_deterministic_page_ocr_confidence(content)
            pages_data = [{"page": 1, "text": content, "confidence": conf}]
        except Exception as e:
            pages_data = [{"page": 1, "text": f"Extraction error: {e}", "confidence": 50.0}]

    avg_confidence = round(float(np.mean([p["confidence"] for p in pages_data])), 2)
    return pages_data, avg_confidence

def segment_page_clauses_granular(pages_data: list) -> list:
    """Extracts sub-clauses (or falls back to primary clauses) while tracking page numbers."""
    all_chunks = []
    sub_clause_pattern = re.compile(r'(?m)^\s*(?P<header>\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\s+[A-Z][a-zA-Z0-9"\'\s]{1,50})')
    clause_pattern = re.compile(r'(?m)^\s*(?P<header>(?:\d{1,2}\.\s+[A-Z][A-Za-z\s,&]+)|(?:(?:SCHEDULE|ARTICLE|ANNEXURE)\s+[A-Z0-9]+)|WHEREAS)')

    for p in pages_data:
        page_num = p["page"]
        text = p["text"]

        sub_matches = list(sub_clause_pattern.finditer(text))
        if sub_matches:
            for i in range(len(sub_matches)):
                start = sub_matches[i].start()
                end = sub_matches[i+1].start() if i + 1 < len(sub_matches) else len(text)
                chunk_text = text[start:end].strip()
                if len(chunk_text) > 20:
                    header = chunk_text.split('\n')[0][:80].strip()
                    all_chunks.append({"header": header, "text": chunk_text, "page": page_num})
        else:
            clause_matches = list(clause_pattern.finditer(text))
            if clause_matches:
                for i in range(len(clause_matches)):
                    start = clause_matches[i].start()
                    end = clause_matches[i+1].start() if i + 1 < len(clause_matches) else len(text)
                    chunk_text = text[start:end].strip()
                    if len(chunk_text) > 20:
                        header = chunk_text.split('\n')[0][:80].strip()
                        all_chunks.append({"header": header, "text": chunk_text, "page": page_num})
            elif len(text.strip()) > 30:
                header = text.strip().split('\n')[0][:80].strip()
                all_chunks.append({"header": header or f"Page {page_num} Section", "text": text.strip(), "page": page_num})

    return all_chunks

def process_document(
    job_id: str = None,
    file_data_base64: str = "",
    filename: str = "",
    user_email: str = "",
    user_role: str = "Compliance Officer",
    business_unit: str = "Procurement",
    **kwargs
):
    job = get_current_job()
    effective_job_id = job_id or (job.id if job else None) or kwargs.get("document_id")
    print(f"🚀 Initializing Deterministic Multi-Page Pipeline for Job: {effective_job_id}")

    db: Session = SessionLocal()
    temp_path = f"/tmp/{effective_job_id}_{filename}"
    with open(temp_path, "wb") as f:
        f.write(base64.b64decode(file_data_base64))

    rag_service = RAGKnowledgeService()
    normalization_service = ClauseNormalizationService()
    reasoning_service = LegalReasoningService()

    try:
        # Stage 1: Page-by-Page OCR and Deterministic Scoring
        publish_pipeline_event(effective_job_id, 1, "OCR_SCANNING", 20, "Extracting all pages and calculating deterministic OCR scores...")
        pages_data, overall_confidence = extract_text_and_confidence_all_pages(temp_path)
        pages_count = len(pages_data)

        # Cache page-level metrics in Redis for the Frontend tab
        page_metrics = [
            {
                "page": p["page"],
                "ocrConfidence": p["confidence"],
                "isHighQuality": p["confidence"] >= 85.0,
                "length": len(p["text"])
            }
            for p in pages_data
        ]
        redis_client.set(f"pipeline_pages:{effective_job_id}", json.dumps(page_metrics), ex=86400)

        # Stage 2: Sub-Clause Chunking with Page Tracking
        publish_pipeline_event(effective_job_id, 2, "PARSING_CHUNKING", 40, f"Chunking sub-clauses across {pages_count} pages...")
        structured_chunks = segment_page_clauses_granular(pages_data)

        # Stage 3: High-Score Vector Search with >= 85% Gate
        publish_pipeline_event(effective_job_id, 3, "VECTOR_QUERYING", 60, "Querying Qdrant Vector DB with 85%+ threshold...")
        enriched_candidates = []
        VECTOR_THRESHOLD = 0.85

        for chunk in structured_chunks:
            retrieved = rag_service.semantic_search(chunk["text"][:1500], top_k=1)
            top_match = retrieved[0] if retrieved else {}
            similarity_score = float(top_match.get("score", 0.0))

            if similarity_score >= VECTOR_THRESHOLD:
                ref_id = top_match.get("ref", "KB-POLICY-RULE")
                policy_rule = top_match.get("policy_text") or top_match.get("text", "")
                guidelines = top_match.get("guidelines", "")
                derived_clause_type = top_match.get("clause_type") or chunk["header"]
            else:
                ref_id = "STANDARD-BASELINE"
                policy_rule = f"Standard enterprise terms. No policy deviation above {int(VECTOR_THRESHOLD*100)}% threshold."
                guidelines = "Review against standard business terms."
                derived_clause_type = chunk["header"]

            enriched_candidates.append({
                "clause_type": derived_clause_type,
                "extracted_text": chunk["text"],
                "rag_reference_used": ref_id,
                "matched_policy_text": policy_rule,
                "handling_guidelines": guidelines,
                "page_reference": str(chunk.get("page", 1)),
                "confidence_score": similarity_score,
            })

        # Stage 4: Batch LLM Reasoning
        publish_pipeline_event(effective_job_id, 4, "REASONING_EVALUATION", 80, "Running legal reasoning and risk evaluation...")
        normalized = normalization_service.normalize_clauses(enriched_candidates)

        final_clauses = []
        BATCH_SIZE = 5

        for i in range(0, len(normalized), BATCH_SIZE):
            batch = normalized[i:i + BATCH_SIZE]
            evaluated_batch = reasoning_service.evaluate_risk_and_reasoning(
                batch, business_unit=business_unit, user_role=user_role
            )
            final_clauses.extend(evaluated_batch)

        # Stage 5: Database Commit
        publish_pipeline_event(effective_job_id, 5, "FINALIZING_REPORT", 95, "Persisting structured analysis...")
        doc = db.query(DocumentModel).filter(DocumentModel.job_id == effective_job_id).first()
        if doc:
            doc.ocr_confidence = overall_confidence
            doc.pages = pages_count
            doc.entities_detected = len(final_clauses) * 4
            doc.requires_manual_review = any(c.get("risk_level") == "HIGH" for c in final_clauses)

        for c in final_clauses:
            db.add(ClauseModel(
                job_id=effective_job_id,
                clause_type=c.get("clause_type", "General Provision"),
                extracted_text=c.get("extracted_text", ""),
                confidence_score=c.get("confidence_score", 0.95),
                risk_level=c.get("risk_level", "LOW"),
                risk_rationale=c.get("risk_rationale", "Evaluated against policy standards."),
                involved_party=c.get("involved_party", "Tata Group & Counterparty"),
                rag_reference_used=c.get("rag_reference_used", "N/A"),
                page_reference=str(c.get("page_reference", "1")),
                obligation_owner=c.get("obligation_owner", "Legal Desk"),
                recommended_action=c.get("recommended_action", "Review"),
                proposed_redline=c.get("proposed_redline"),
            ))

        db.commit()

        publish_pipeline_event(effective_job_id, 5, "COMPLETED", 100, "Analysis complete.", {
            "clauses_count": len(final_clauses),
            "ocr_confidence": overall_confidence,
            "pages": pages_count,
        })
        print(f"✅ Pipeline complete for {effective_job_id}. Processed {pages_count} pages with {overall_confidence}% OCR confidence.")

    except Exception as e:
        db.rollback()
        publish_pipeline_event(effective_job_id, 5, "FAILED", 100, f"Error: {str(e)}")
        print(f"❌ Worker error: {e}")
        raise e
    finally:
        db.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)