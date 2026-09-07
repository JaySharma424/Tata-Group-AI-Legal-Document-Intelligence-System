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

def rephrase_clause_for_policy_retrieval(header: str, text: str) -> str:
    """
    Granular topic routing mapping clauses to their distinct enterprise policy domain.
    Prevents operational, SLA, insurance, retention, and security terms from defaulting to jurisdiction.
    """
    h = header.lower()
    t = text.lower()

    # 1. Operational SLAs, Warranties & Service Credits
    if any(k in h or k in t for k in ["sla", "service level", "availability", "99.9", "uptime", "service credit", "incident record", "rto", "rpo"]):
        if any(k in h or k in t for k in ["business continuity", "disaster recovery", "rto", "rpo", "bcdr"]):
            return "Category: OPERATIONS. Policy Title: Business Continuity and Disaster Recovery Plan. Reference ID: POL-BCDR-017. Guidance Rule: Operational continuity and recovery time objectives."
        return "Category: PERFORMANCE & SERVICE. Policy Title: Warranties and Service Level Agreements SLAs. Reference ID: CLS-SLA-017. Guidance Rule: Operational availability 99.9% uptime, bug-free deliverables, financial remedies."

    # 2. Insurance & Risk Coverage
    elif any(k in h or k in t for k in ["insurance", "cyber liability", "errors and omissions", "commercial general insurance"]):
        return "Category: RISK & INSURANCE. Policy Title: Mandatory Insurance Coverage Limits. Reference ID: CLS-INS-016. Guidance Rule: Minimum thresholds of Professional Liability and Cyber Insurance."

    # 3. Subcontracting & Third-Party Sourcing
    elif any(k in h or k in t for k in ["subcontract", "subprocessor"]):
        return "Category: VENDOR MANAGEMENT. Policy Title: Subcontracting Approval Mandate. Reference ID: CLS-SUB-012. Guidance Rule: Prohibit subcontracting without prior written consent and enforce full liability flow-down."

    # 4. Records, Retention & Archival
    elif any(k in h or k in t for k in ["record retention", "billing records", "archival", "retain evidence"]):
        return "Category: LEGAL OPERATIONS. Policy Title: Record Retention and Document Archival Policy. Reference ID: POL-RET-019. Guidance Rule: Preservation periods and secure destruction protocols for commercial records."

    # 5. Cybersecurity & Incident Notification
    elif any(k in h or k in t for k in ["vulnerabilit", "security incident", "cert-in", "patching", "mfa", "access review"]):
        if "cert-in" in t or "incident notification" in t or "24 hours" in t:
            return "Category: CYBER REGULATION. Policy Title: CERT-In Cyber Security Incident Directives. Reference ID: REG-CERT-021. Guidance Rule: Mandate logging and immediate reporting of security incidents."
        return "Category: CYBERSECURITY. Policy Title: Group Information Security Policy GISP. Reference ID: POL-SEC-002. Guidance Rule: Mandatory security baselines, encryption, and vulnerability remediation."

    # 6. Intellectual Property & Deliverables
    elif any(k in h or k in t for k in ["background ip", "deliverable", "work made for hire", "open-source", "patent", "copyright"]):
        return "Category: INTELLECTUAL PROPERTY. Policy Title: Intellectual Property Ownership Work Made for Hire. Reference ID: CLS-IP-006. Guidance Rule: Deliverables and created code vest exclusively with Tata Group."

    # 7. Brand, Publicity & Marketing
    elif any(k in h or k in t for k in ["publicity", "press release", "brand", "trademark", "marketing reference", "spokesperson", "logo"]):
        return "Category: BRAND & MARKETING. Policy Title: Brand Usage and Publicity Restrictions. Reference ID: CLS-BRD-022. Guidance Rule: Prohibit unauthorized public announcements and use of Tata trademarks."

    # 8. Anti-Bribery, Ethics & Conflicts
    elif any(k in h or k in t for k in ["anti-bribery", "corruption", "abac", "conflict of interest", "fcpa"]):
        return "Category: ETHICS & COMPLIANCE. Policy Title: Anti-Bribery and Anti-Corruption Clause. Reference ID: CLS-ETH-013. Guidance Rule: Zero tolerance for bribery, illicit payments, and conflict disclosures."

    # 9. Personnel & Non-Solicitation
    elif any(k in h or k in t for k in ["non-solicit", "solicit", "personnel", "employment"]):
        return "Category: HUMAN RESOURCES. Policy Title: Mutual Non-Solicitation of Employees. Reference ID: CLS-SOL-014. Guidance Rule: Restrict solicitation during contract term and for 1 year post-termination."

    # 10. Audit & Regulatory Inspection
    elif any(k in h or k in t for k in ["audit", "inspection", "independent assurance", "regulat"]):
        return "Category: GOVERNANCE & AUDIT. Policy Title: Audit and Inspection Rights. Reference ID: CLS-AUD-015. Guidance Rule: Grant unconditional access to inspect financial records and facilities."

    # 11. Force Majeure
    elif any(k in h or k in t for k in ["force majeure"]):
        return "Category: RISK MANAGEMENT. Policy Title: Force Majeure Scope and Notification. Reference ID: CLS-FM-011. Guidance Rule: Define force majeure events and require written notice within 48 hours."

    # 12. Indemnification & Third-Party Defense
    elif any(k in h or k in t for k in ["indemn", "hold harmless", "defense of claim"]):
        return "Category: INDEMNIFICATION & LIABILITY. Policy Title: Comprehensive Indemnification for IP Infringement. Reference ID: CLS-IND-002. Guidance Rule: Vendor must fully indemnify against third-party claims; avoid uncapped client indemnity."

    # 13. Limitation of Liability
    elif any(k in h or k in t for k in ["liability", "consequential damage", "lost profit", "super-cap", "aggregate liability"]):
        return "Category: INDEMNIFICATION & LIABILITY. Policy Title: Limitation of Liability Cap Standard. Reference ID: CLS-LIAB-001. Guidance Rule: Vendor liability capped at 100% of ACV, mutual indirect damage exclusions."

    # 14. Financial, Pricing & Payment Terms
    elif any(k in h or k in t for k in ["payment", "fee", "invoice", "pricing", "disputed amount", "withhold payment"]):
        return "Category: FINANCIAL & PAYMENT. Policy Title: Standard Commercial Payment Terms. Reference ID: CLS-PAY-007. Guidance Rule: Standard payment cycles Net 45 or Net 60 days, invoice dispute protocol."

    # 15. Termination & Exit Management
    elif any(k in h or k in t for k in ["terminat", "cure period", "material breach", "convenience", "transition assistance", "exit management"]):
        if any(k in h or k in t for k in ["transition", "exit management", "data migration"]):
            return "Category: TERMINATION & EXIT. Policy Title: Exit Management and Transition Assistance. Reference ID: CLS-EXIT-018. Guidance Rule: Obligate vendor to provide operational support and data return upon expiration."
        return "Category: TERMINATION & EXIT. Policy Title: Termination for Convenience Clause. Reference ID: CLS-TERM-004. Guidance Rule: Unilateral right to terminate for convenience on 30 to 60 days advance written notice."

    # 16. Confidentiality & Data Protection
    elif any(k in h or k in t for k in ["confidential", "proprietary information", "trade secret", "data protection", "customer data"]):
        return "Category: CONFIDENTIALITY & PRIVACY. Policy Title: Mutual Confidentiality and NDA Terms. Reference ID: CLS-NDA-003. Guidance Rule: Mandatory survival period of 3 to 5 years post-termination, proprietary data encryption."

    # 17. Governing Law, Venue & Arbitration
    elif any(k in h or k in t for k in ["governing law", "jurisdiction", "arbitrat", "dispute resolution", "courts"]):
        if any(k in h or k in t for k in ["arbitrat", "mcia", "siac"]):
            return "Category: DISPUTE RESOLUTION. Policy Title: Dispute Resolution and Institutional Arbitration. Reference ID: CLS-DIS-009. Guidance Rule: Binding institutional arbitration under MCIA or SIAC rules in Mumbai."
        return "Category: LEGAL & JURISDICTION. Policy Title: Governing Law and Exclusive Jurisdiction. Reference ID: CLS-LAW-008. Guidance Rule: Laws of India, exclusive jurisdiction designated in Mumbai courts."

    # 18. General Legal Boilerplate (Precedence, Assignment, Severability, Counterparts)
    elif any(k in h or k in t for k in ["order of precedence", "severability", "waiver", "assignment", "counterpart", "entire agreement", "headings"]):
        if "assignment" in h or "assignment" in t:
            return "Category: GENERAL PROVISIONS. Policy Title: Assignment and Transfer Restrictions. Reference ID: CLS-ASG-021. Guidance Rule: Prohibit transfer of rights without prior written consent."
        return "Category: GENERAL PROVISIONS. Policy Title: Severability and Waiver Documentation. Reference ID: CLS-GEN-020. Guidance Rule: Invalidating one clause does not void entire agreement; formal written waivers required."

    clean_header = re.sub(r'^\d+(\.\d+)*\s*', '', header).strip()
    return f"Policy Title: {clean_header}. Category: General Provision. Reference ID: CLS-GEN-020. Guidance Rule: Standard corporate contracting policy guidelines for {clean_header}."

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
    print(f"🚀 Initializing Precision Legal Intelligence Pipeline for Job: {effective_job_id}")

    db: Session = SessionLocal()
    temp_path = f"/tmp/{effective_job_id}_{filename}"
    with open(temp_path, "wb") as f:
        f.write(base64.b64decode(file_data_base64))

    rag_service = RAGKnowledgeService()
    normalization_service = ClauseNormalizationService()
    reasoning_service = LegalReasoningService()

    try:
        # Stage 1: Text & OCR scanning
        publish_pipeline_event(effective_job_id, 1, "OCR_SCANNING", 20, "Extracting text and calculating page OCR scores...")
        pages_data, overall_confidence = extract_text_and_confidence_all_pages(temp_path)
        pages_count = len(pages_data)

        # Stage 2: Sub-clause chunking
        publish_pipeline_event(effective_job_id, 2, "PARSING_CHUNKING", 40, f"Chunking sub-clauses across {pages_count} pages...")
        structured_chunks = segment_page_clauses_granular(pages_data)

        # Stage 3: Dynamic Multi-File Knowledge Base Retrieval
        publish_pipeline_event(effective_job_id, 3, "VECTOR_QUERYING", 60, "Retrieving policy citations across Knowledge Base...")
        enriched_candidates = []  # <-- ENSURE THIS LINE IS PRESENT
        SIMILARITY_FLOOR = 0.20

        for chunk in structured_chunks:
            policy_query = rephrase_clause_for_policy_retrieval(chunk["header"], chunk["text"])
            candidates = rag_service.semantic_search(policy_query, top_k=1)
            top_match = candidates[0] if candidates else {}
            score = float(top_match.get("score", 0.0))

            if not top_match or score < SIMILARITY_FLOOR:
                ref_id = "MISSING-POLICY"
                derived_clause_type = chunk["header"]
                policy_rule = "Unapproved contractual provision: No matching approved standard found in Knowledge Base (similarity < 20%)."
                guidelines = "Clause represents an unmapped risk exposure. Requires explicit legal review and policy drafting."
                taxonomy_risk = "HIGH"
                final_score = max(0.08, score)
            else:
                ref_id = top_match.get("ref", "CLS-GEN-020")
                derived_clause_type = top_match.get("clause_type") or chunk["header"]
                policy_rule = top_match.get("policy_text") or top_match.get("text", "")
                guidelines = top_match.get("guidelines", "")
                final_score = score
                
                # Extract taxonomy risk level from payload
                taxonomy_risk = top_match.get("risk_level", "LOW")
                t = chunk["text"].lower()
                if any(kw in t for kw in ["unlimited", "without any cap", "penalty of 5%", "may not terminate", "laws of the state of new york"]):
                    taxonomy_risk = "HIGH"
                elif any(kw in t for kw in ["exclusive", "ten (10) years", "4 times the fees", "four (4) times"]):
                    taxonomy_risk = "MEDIUM"

            enriched_candidates.append({
                "clause_type": derived_clause_type,
                "extracted_text": chunk["text"],
                "rag_reference_used": ref_id,
                "matched_policy_text": policy_rule,
                "handling_guidelines": guidelines,
                "taxonomy_risk": taxonomy_risk,
                "page_reference": str(chunk.get("page", 1)),
                "confidence_score": round(final_score, 2),
            })

        # Stage 4: Batch in chunks of 6 to prevent timeouts
        normalized = normalization_service.normalize_clauses(enriched_candidates)
        final_clauses = []
        BATCH_SIZE = 6
        for i in range(0, len(normalized), BATCH_SIZE):
            batch = normalized[i:i + BATCH_SIZE]
            final_clauses.extend(reasoning_service.evaluate_risk_and_reasoning(
                batch, business_unit=business_unit, user_role=user_role
            ))
            final_clauses.extend(evaluated_batch)

        # Stage 5: Database Commit
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
                confidence_score=float(c.get("confidence_score", 0.50)),
                risk_level=c.get("risk_level", "LOW"),
                risk_rationale=c.get("risk_rationale", "Evaluated against corporate policy standards."),
                involved_party=c.get("involved_party", "Tata Group & Counterparty"),
                rag_reference_used=c.get("rag_reference_used") or "MISSING-POLICY",
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