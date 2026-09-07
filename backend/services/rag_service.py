import csv
import glob
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sqlalchemy import text
from backend.database import SessionLocal, Base, engine
from backend.models import KnowledgeBaseModel
from backend.services.llm_config import get_llm_config


class RAGKnowledgeService:
    def __init__(self, storage_path: str = "./backend/storage/qdrant_db"):
        self.collection_name = "tata_legal_knowledge_v4"
        self.vector_dim = 768

        # Auto-migration: Ensure table exists and add risk_level column if missing
        try:
            Base.metadata.create_all(bind=engine)
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS risk_level VARCHAR DEFAULT 'MEDIUM';"))
        except Exception as e:
            print(f"[WARN] Postgres migration error: {e}")

        google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        config = get_llm_config()
        db_key = config.get("api_key", "")
        if db_key and not any(db_key.startswith(p) for p in ("nvapi-", "sk-", "gsk_")):
            google_key = db_key

        if google_key:
            try:
                self.client = genai.Client(api_key=google_key)
                self.has_api_key = True
            except Exception:
                self.client = None
                self.has_api_key = False
        else:
            self.client = None
            self.has_api_key = False

        qdrant_url = (os.getenv("QDRANT_URL") or "").strip()
        qdrant_api_key = (os.getenv("QDRANT_API_KEY") or "").strip()

        if qdrant_url and qdrant_api_key:
            if not qdrant_url.startswith("http"):
                qdrant_url = f"https://{qdrant_url}"
            try:
                self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=25)
            except Exception:
                self.qdrant = QdrantClient(":memory:")
        else:
            self.qdrant = QdrantClient(":memory:")

    def _get_embedding(self, text_input: str, retries: int = 2) -> List[float]:
        if not self.has_api_key or not self.client or not text_input.strip():
            return [0.0] * self.vector_dim

        for attempt in range(retries):
            try:
                response = self.client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=text_input[:2000],
                    config=types.EmbedContentConfig(output_dimensionality=768),
                )
                if response and response.embeddings:
                    emb = list(response.embeddings[0].values)
                    if len(emb) > 768:
                        emb = emb[:768]
                    elif len(emb) < 768:
                        emb = emb + [0.0] * (768 - len(emb))
                    return emb
            except Exception:
                time.sleep(0.2 * (attempt + 1))
        return [0.0] * self.vector_dim

    def semantic_search(self, query: str, top_k: int = 3, filters: Optional[Dict] = None) -> List[Dict]:
        query_vector = self._get_embedding(query[:1500])
        has_vector = any(v != 0.0 for v in query_vector)
        candidates = []

        # 1. Vector Search in Qdrant Cloud
        if has_vector:
            try:
                results = self.qdrant.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                )
                if results:
                    db = SessionLocal()
                    try:
                        for r in results:
                            matched_uuid = str(r.id)
                            pg_record = db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == matched_uuid).first()
                            
                            base_risk = pg_record.risk_level if (pg_record and getattr(pg_record, "risk_level", None)) else r.payload.get("risk_level", "MEDIUM")

                            candidates.append({
                                "uuid": matched_uuid,
                                "ref": pg_record.reference_id if pg_record else r.payload.get("ref", "N/A"),
                                "title": pg_record.title if pg_record else r.payload.get("title", ""),
                                "clause_type": pg_record.category if pg_record else r.payload.get("clause_type", "General Provision"),
                                "policy_text": pg_record.guidance if pg_record else r.payload.get("policy_text", ""),
                                "guidelines": pg_record.guidance if pg_record else r.payload.get("guidelines", ""),
                                "source": pg_record.source_file if pg_record else r.payload.get("source", "Knowledge Base"),
                                "text": pg_record.search_text if pg_record else r.payload.get("text", ""),
                                "risk_level": base_risk,
                                "score": round(float(r.score), 2),
                            })
                    finally:
                        db.close()
            except Exception as e:
                print(f"[WARN] Qdrant search error: {e}")

        # 2. Resilient Database Search
        if not candidates or candidates[0]["score"] < 0.20:
            db = SessionLocal()
            try:
                q_clean = re.sub(r'[^\w\s]', ' ', query.lower())
                tokens = set(w for w in q_clean.split() if len(w) > 3)
                all_policies = db.query(KnowledgeBaseModel).all()

                scored_policies = []
                for p in all_policies:
                    p_clean = re.sub(r'[^\w\s]', ' ', (p.search_text or "").lower())
                    p_tokens = set(p_clean.split())
                    
                    overlap = len(tokens & p_tokens)
                    total = len(tokens | p_tokens) or 1
                    sim_score = round(min(0.85, max(0.12, (overlap / total) * 2.2)), 2)

                    scored_policies.append({
                        "uuid": p.id,
                        "ref": p.reference_id,
                        "title": p.title,
                        "clause_type": p.category,
                        "policy_text": p.guidance,
                        "guidelines": p.guidance,
                        "source": p.source_file,
                        "text": p.search_text,
                        "risk_level": getattr(p, "risk_level", "MEDIUM") or "MEDIUM",
                        "score": sim_score,
                    })

                scored_policies.sort(key=lambda x: x["score"], reverse=True)
                candidates = scored_policies[:top_k]
            finally:
                db.close()
        return candidates

    def upsert_document_knowledge(self, doc_id: str, clauses: List[Dict]):
        pass
