import os
import re
import time
import json
import base64
import hashlib
import numpy as np
import redis
import fitz  # PyMuPDF
from sqlalchemy.orm import Session
from rq import get_current_job
from google import genai
from google.genai import types

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


def resolve_gemini_client() -> genai.Client:
    config = get_llm_config()
    api_key = config.get("api_key", "")
    if not api_key or any(api_key.startswith(p) for p in ("nvapi-", "sk-", "gsk_")):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

    if not api_key:
        raise ValueError("CRITICAL: No valid Google Gemini API Key found in DB or Environment.")
    return genai.Client(api_key=api_key)


def calculate_cosine_similarity(vec1: list, vec2: list) -> float:
    v1 = np.array(vec1, dtype=float)
    v2 = np.array(vec2, dtype=float)
    norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


def extract_text_upfront(file_path: str) -> tuple[str, float, int]:
    full_text = ""
    pages = 1
    confidence = 98.5

    if file_path.lower().endswith(".pdf"):
        try:
            with fitz.open(file_path) as pdf_doc:
                pages = len(pdf_doc)
                for page in pdf_doc:
                    full_text += page.get_text() + "\n"
        except Exception as e:
            print(f"[WARN] PyMuPDF extraction: {e}")
    elif file_path.lower().endswith((".txt", ".md")):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            full_text = f.read()

    # Vision OCR fallback if scanned or image-based
    if len(full_text.strip()) < 50:
        client = resolve_gemini_client()
        uploaded = client.files.upload(file=file_path)
        while uploaded.state.name == "PROCESSING":
            time.sleep(1)
            uploaded = client.files.get(name=uploaded.name)

        if uploaded.state.name == "FAILED":
            raise ValueError("Vision OCR failed to parse document.")

        resp = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=["Extract all text and numbered legal clauses accurately.", uploaded],
        )
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass
        full_text = resp.text.strip()
        confidence = 94.0

    return full_text.strip(), confidence, pages


def get_cached_embedding(text: str, client: genai.Client) -> list:
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    cache_key = f"cache:emb:{text_hash}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    try:
        res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text[:2000],
            config=types.EmbedContentConfig(),
        )
        emb = list(res.embeddings[0].values)
        try:
            redis_client.set(cache_key, json.dumps(emb), ex=86400)
        except Exception:
            pass
        return emb
    except Exception as e:
        print(f"[WARN] Embedding error: {e}")
        return [0.0] * 768


def segment_contract_clauses(text: str) -> list:
    """Segments contract text along structural boundaries using hierarchical regex matching."""
    # Matches: 1. DEFINITIONS, 1.1, ARTICLE 1, SCHEDULE A, WHEREAS
    pattern = re.compile(
        r'(?m)^(?P<header>'
        r'(?:WHEREAS|NOW\s+THEREFORE|IN\s+WITNESS\s+WHEREOF)|'
        r'(?:(?:ARTICLE|CLAUSE|SECTION)\s+\d+(?:\.\d+)*)|'
        r'(?:\d+\.(?:\d+)*\s+[A-Z][A-Za-z\s]{2,40})|'
        r'(?:SCHEDULE|ANNEXURE|EXHIBIT)\s+[A-Z0-9]+'
        r')[:\.\-\s]'
    )
    
    splits = [m.start() for m in pattern.finditer(text)]
    if not splits:
        return [{"header": "General Provision", "text": p.strip()} for p in text.split('\n\n') if len(p.strip()) > 50]
        
    chunks = []
    if splits[0] > 0:
        preamble = text[0:splits[0]].strip()
        if len(preamble) > 50:
            chunks.append({"header": "Preamble / Recitals", "text": preamble})
            
    for i in range(len(splits)):
        start = splits[i]
        end = splits[i+1] if i + 1 < len(splits) else len(text)
        chunk_text = text[start:end].strip()
        if len(chunk_text) > 40:
            header = chunk_text.split('\n')[0][:60].strip()
            chunks.append({"header": header, "text": chunk_text})
            
    # Merge excessively small chunks to preserve LLM context and prevent rate-limiting
    merged_chunks = []
    current_text, current_header = "", ""
    
    for c in chunks:
        if len(current_text) + len(c["text"]) < 1000:
            current_text += "\n" + c["text"]
            if not current_header: current_header = c["header"]
        else:
            if current_text:
                merged_chunks.append({"header": current_header, "text": current_text.strip()})
            current_text = c["text"]
            current_header = c["header"]
            
    if current_text:
        merged_chunks.append({"header": current_header, "text": current_text.strip()})
        
    return merged_chunks


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
    print(f"🚀 Initializing Dynamic Pipeline for Job: {effective_job_id}")

    db: Session = SessionLocal()
    temp_path = f"/tmp/{effective_job_id}_{filename}"
    with open(temp_path, "wb") as f:
        f.write(base64.b64decode(file_data_base64))

    rag_service = RAGKnowledgeService()
    normalization_service = ClauseNormalizationService()
    reasoning_service = LegalReasoningService()

    try:
        # Stage 1: Text extraction
        publish_pipeline_event(effective_job_id, 1, "OCR_SCANNING", 20, "Extracting text and structure...")
        full_text, conf, pages = extract_text_upfront(temp_path)

        # Stage 2: Context-aware chunking
        publish_pipeline_event(effective_job_id, 2, "PARSING_CHUNKING", 40, "Segmenting contract clauses...")
        structured_chunks = segment_contract_clauses(full_text)

        # Stage 3: Dynamic Vector DB Retrieval (Searching Qdrant for policies from CSV & TXT)
        publish_pipeline_event(effective_job_id, 3, "VECTOR_QUERYING", 60, "Retrieving matching policies from Vector DB...")
        enriched_candidates = []
        VECTOR_THRESHOLD = 0.90

        for chunk in structured_chunks:
            retrieved = rag_service.semantic_search(chunk["text"][:1500], top_k=1)
            top_match = retrieved[0] if retrieved else {}
            similarity_score = float(top_match.get("score", 0.0))

            if similarity_score >= VECTOR_THRESHOLD:
                ref_id = top_match.get("ref", "TAXONOMY-RULE")
                policy_rule = top_match.get("policy_text") or top_match.get("text", "")
                guidelines = top_match.get("guidelines", "")
                derived_clause_type = top_match.get("clause_type") or chunk["header"]
            else:
                # Below threshold: Do not force an artificial policy violation
                ref_id = "STANDARD-BASELINE"
                policy_rule = "No material corporate policy deviation detected above 90% threshold."
                guidelines = "Review against standard business terms."
                derived_clause_type = chunk["header"]

            enriched_candidates.append({
                "clause_type": derived_clause_type,
                "extracted_text": chunk["text"],
                "rag_reference_used": ref_id,
                "matched_policy_text": policy_rule,
                "handling_guidelines": guidelines,
                "confidence_score": similarity_score if similarity_score > 0 else 0.95,
            })

        # Stage 4: Batch LLM Reasoning grounded strictly in Vector DB context
        publish_pipeline_event(effective_job_id, 4, "REASONING_EVALUATION", 80, "Evaluating risks and detecting missing clauses...")
        normalized = normalization_service.normalize_clauses(enriched_candidates)
        final_clauses = reasoning_service.evaluate_risk_and_reasoning(
            normalized, business_unit=business_unit, user_role=user_role
        )

        # Stage 4.5: Missing Clause Detection
        clause_types_found = " ".join([c.get("clause_type", "") for c in final_clauses]).lower()
        missing_clauses = []
        
        if "indemn" not in clause_types_found and "defend" not in full_text.lower():
            missing_clauses.append({
                "clause_type": "MISSING: Indemnification",
                "extracted_text": "No indemnification protections found in the document.",
                "confidence_score": 0.99,
                "risk_level": "HIGH",
                "risk_rationale": "Failure to include standard IP and third-party indemnification exposes the Enterprise to uncapped legal liability.",
                "rag_reference_used": "RISK-IND-101",
                "page_reference": "Document Wide",
                "obligation_owner": "Legal Counsel",
                "recommended_action": "ESCALATE",
                "proposed_redline": "Vendor shall defend, indemnify and hold harmless the Enterprise from any third-party claims alleging intellectual property infringement or bodily injury."
            })
            
        if "liability" not in clause_types_found and "cap" not in full_text.lower():
            missing_clauses.append({
                "clause_type": "MISSING: Limitation of Liability",
                "extracted_text": "No limitation of liability caps found in the document.",
                "confidence_score": 0.99,
                "risk_level": "HIGH",
                "risk_rationale": "Missing liability caps result in unlimited financial exposure. Policy mandates capping vendor liability at 100% of ACV.",
                "rag_reference_used": "RISK-CAP-99",
                "page_reference": "Document Wide",
                "obligation_owner": "Legal Counsel",
                "recommended_action": "ESCALATE",
                "proposed_redline": "Neither Party's aggregate liability shall exceed 100% of the annual contract value, excluding breaches of confidentiality or gross negligence."
            })
            
        final_clauses.extend(missing_clauses)

        # Stage 5: Database Persistence
        publish_pipeline_event(effective_job_id, 5, "FINALIZING_REPORT", 95, "Committing evaluated clauses...")
        doc = db.query(DocumentModel).filter(DocumentModel.job_id == effective_job_id).first()
        if doc:
            doc.ocr_confidence = conf
            doc.pages = pages
            doc.entities_detected = len(final_clauses) * 4
            doc.requires_manual_review = any(c.get("risk_level") == "HIGH" for c in final_clauses)

        for c in final_clauses:
            db.add(ClauseModel(
                job_id=effective_job_id,
                clause_type=c.get("clause_type", "General Provision"),
                extracted_text=c.get("extracted_text", ""),
                confidence_score=c.get("confidence_score", 0.95),
                risk_level=c.get("risk_level", "LOW"),
                risk_rationale=c.get("risk_rationale", "Evaluated against corporate policy standards."),
                involved_party=c.get("involved_party", "Tata Group & Counterparty"),
                rag_reference_used=c.get("rag_reference_used", "N/A"),
                page_reference=c.get("page_reference", "Section 1"),
                obligation_owner=c.get("obligation_owner", "Legal Desk"),
                recommended_action=c.get("recommended_action", "Review"),
                proposed_redline=c.get("proposed_redline"),
            ))

        db.commit()

        # Update Qdrant index with new contract knowledge
        try:
            rag_service.upsert_document_knowledge(effective_job_id, final_clauses)
        except Exception as e:
            print(f"[WARN] Document knowledge indexing error: {e}")

        publish_pipeline_event(effective_job_id, 5, "COMPLETED", 100, "Analysis complete.", {
            "clauses_count": len(final_clauses),
            "ocr_confidence": conf,
            "pages": pages,
        })
        print(f"✅ Pipeline complete for {effective_job_id}. Extracted {len(final_clauses)} dynamic clauses.")

    except Exception as e:
        db.rollback()
        publish_pipeline_event(effective_job_id, 5, "FAILED", 100, f"Error: {str(e)}")
        print(f"❌ Worker error: {e}")
        raise e
    finally:
        db.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)