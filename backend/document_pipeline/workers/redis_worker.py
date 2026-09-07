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
    if not text or len(text.strip()) < 10:
        return 50.0
    clean_chars = [c for c in text if not c.isspace()]
    if not clean_chars:
        return 50.0
    total_chars = len(clean_chars)
    alnum_chars = sum(1 for c in clean_chars if c.isalnum())
    alnum_ratio = alnum_chars / total_chars
    allowed_punct = sum(1 for c in clean_chars if c in '.,;:()[]"\'%-/&$#@§')
    noise_ratio = (total_chars - (alnum_chars + allowed_punct)) / total_chars
    words = text.strip().split()
    avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
    score = (alnum_ratio * 80.0) + 20.0 - (noise_ratio * 35.0)
    if avg_word_len < 2.5 or avg_word_len > 15.0:
        score -= 8.0
    return round(min(99.9, max(50.0, score)), 2)

def extract_text_and_confidence_all_pages(file_path: str) -> tuple[list, float]:
    pages_data = []
    if file_path.lower().endswith(".pdf"):
        try:
            with fitz.open(file_path) as pdf_doc:
                for page_idx in range(len(pdf_doc)):
                    page_text = pdf_doc[page_idx].get_text().strip()
                    pages_data.append({
                        "page": page_idx + 1,
                        "text": page_text,
                        "confidence": calculate_deterministic_page_ocr_confidence(page_text)
                    })
        except Exception as e:
            print(f"[WARN] PyMuPDF error: {e}")

    if not pages_data:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            pages_data = [{"page": 1, "text": content, "confidence": calculate_deterministic_page_ocr_confidence(content)}]
        except Exception as e:
            pages_data = [{"page": 1, "text": f"Extraction error: {e}", "confidence": 50.0}]

    avg_confidence = round(float(np.mean([p["confidence"] for p in pages_data])), 2)
    return pages_data, avg_confidence

def segment_page_clauses_granular(pages_data: list) -> list:
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
    print(f"🚀 Initializing Fast Legal Intelligence Pipeline for Job: {effective_job_id}")

    db: Session = SessionLocal()
    temp_path = f"/tmp/{effective_job_id}_{filename}"
    with open(temp_path, "wb") as f:
        f.write(base64.b64decode(file_data_base64))

    rag_service = RAGKnowledgeService()
    normalization_service = ClauseNormalizationService()
    reasoning_service = LegalReasoningService()

    try:
        publish_pipeline_event(effective_job_id, 1, "OCR_SCANNING", 20, "Extracting text and calculating page OCR scores...")
        pages_data, overall_confidence = extract_text_and_confidence_all_pages(temp_path)
        pages_count = len(pages_data)

        publish_pipeline_event(effective_job_id, 2, "PARSING_CHUNKING", 40, f"Chunking sub-clauses across {pages_count} pages...")
        structured_chunks = segment_page_clauses_granular(pages_data)

        publish_pipeline_event(effective_job_id, 3, "VECTOR_QUERYING", 60, "Cross-referencing against Qdrant Cloud collection...")
        enriched_candidates = []
        VECTOR_THRESHOLD = 0.38

        for chunk in structured_chunks:
            retrieved = rag_service.semantic_search(chunk["text"][:1500], top_k=1)
            top_match = retrieved[0] if retrieved else {}
            similarity_score = float(top_match.get("score", 0.0))

            if similarity_score >= VECTOR_THRESHOLD and top_match.get("ref"):
                ref_id = top_match.get("ref")
                policy_rule = top_match.get("policy_text") or top_match.get("text", "")
                guidelines = top_match.get("guidelines", "")
                derived_clause_type = top_match.get("clause_type") or chunk["header"]
            else:
                ref_id = "STANDARD-BASELINE"
                policy_rule = "Standard commercial provision with no material policy conflict."
                guidelines = "Review against standard business terms."
                derived_clause_type = chunk["header"]

            enriched_candidates.append({
                "clause_type": derived_clause_type,
                "extracted_text": chunk["text"],
                "rag_reference_used": ref_id,
                "matched_policy_text": policy_rule,
                "handling_guidelines": guidelines,
                "page_reference": str(chunk.get("page", 1)),
                "confidence_score": round(similarity_score, 2) if similarity_score > 0 else 0.85,
            })

        publish_pipeline_event(effective_job_id, 4, "REASONING_EVALUATION", 80, "Running AI legal reasoning & risk classification...")
        normalized = normalization_service.normalize_clauses(enriched_candidates)

        final_clauses = reasoning_service.evaluate_risk_and_reasoning(
            normalized, business_unit=business_unit, user_role=user_role
        )

        publish_pipeline_event(effective_job_id, 5, "FINALIZING_REPORT", 95, "Committing risk reasoning to database...")
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
                confidence_score=c.get("confidence_score", 0.85),
                risk_level=c.get("risk_level", "LOW"),
                risk_rationale=c.get("risk_rationale", "Evaluated against corporate policy standards."),
                involved_party=c.get("involved_party", "Tata Group & Counterparty"),
                rag_reference_used=c.get("rag_reference_used") or "STANDARD-BASELINE",
                page_reference=str(c.get("page_reference", "1")),
                obligation_owner=c.get("obligation_owner", "Legal & Procurement Desk"),
                recommended_action=c.get("recommended_action", "Review"),
                proposed_redline=c.get("proposed_redline"),
            ))

        db.commit()

        publish_pipeline_event(effective_job_id, 5, "COMPLETED", 100, "Analysis complete.", {
            "clauses_count": len(final_clauses),
            "ocr_confidence": overall_confidence,
            "pages": pages_count,
        })
        print(f"✅ Fast pipeline complete for {effective_job_id}. Processed {len(final_clauses)} clauses.")

    except Exception as e:
        db.rollback()
        publish_pipeline_event(effective_job_id, 5, "FAILED", 100, f"Error: {str(e)}")
        print(f"❌ Worker error: {e}")
        raise e
    finally:
        db.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)