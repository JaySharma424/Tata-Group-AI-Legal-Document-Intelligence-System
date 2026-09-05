import csv
import glob
import os
import re
import time
import threading
from backend.services.llm_config import get_llm_config
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


class RAGKnowledgeService:
    """Production-grade RAG service supporting Qdrant Cloud, local disk, and in-memory fallback."""

    def __init__(self, storage_path: str = "./backend/storage/qdrant_db"):
        self.collection_name = "tata_legal_knowledge_v2"
        self.vector_dim = 768  # Enforced 768-dim vector size
        self.is_seeding = False  # Prevent concurrent seeding attempts

        # --- 🚀 STRICT GOOGLE API KEY ISOLATION FOR EMBEDDINGS ---
        google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        config = get_llm_config()
        db_key = config.get("api_key", "")
        
        # Only use database key for Google embeddings if it is an actual Google API key
        if db_key and not db_key.startswith("nvapi-") and not db_key.startswith("sk-") and not db_key.startswith("gsk_"):
            google_key = db_key

        if google_key:
            try:
                self.client = genai.Client(api_key=google_key)
                self.has_api_key = True
            except Exception as e:
                print(f"[WARN] Failed to initialize Google GenAI Client: {e}")
                self.client = None
                self.has_api_key = False
        else:
            self.client = None
            self.has_api_key = False
            print("[WARN] GEMINI_API_KEY missing. Vector search will use zero-vectors.")

        # --- QDRANT CLOUD / LOCAL INITIALIZATION ---
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if qdrant_url and qdrant_api_key:
            try:
                print(f"[INFO] Connecting to Qdrant Cloud cluster at {qdrant_url[:30]}...")
                self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
                self.qdrant.get_collections()
                print("[OK] Connected to Qdrant Cloud successfully.")
            except Exception as e:
                print(f"[WARN] Failed to connect to Qdrant Cloud: {e}. Falling back to in-memory.")
                self.qdrant = QdrantClient(":memory:")
        else:
            print("[INFO] Using in-memory Qdrant for local development")
            self.qdrant = QdrantClient(":memory:")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_path = os.path.join(
            os.path.dirname(current_dir), "data", "risk_taxonomy.csv"
        )
        self.kb_dir = os.path.join(
            os.path.dirname(current_dir), "data", "knowledge_base"
        )

        # Ensure collection exists without blocking startup
        threading.Thread(target=self._ensure_collection_exists, daemon=True).start()

    def _ensure_collection_exists(self, seed_immediately: bool = False):
        """Creates collection if missing; optionally seeds it."""
        try:
            collections = self.qdrant.get_collections().collections
            names = [c.name for c in collections]
            if self.collection_name not in names:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE),
                )
                if seed_immediately:
                    print("[INFO] Seeding RAG knowledge base...")
                    self._seed_structured_policies()
                else:
                    print("[INFO] Collection created. Seeding deferred to prevent startup blocking.")
        except Exception as e:
            print(f"[WARN] Collection init error: {e}")

    def _get_embedding(self, text: str, retries: int = 3) -> List[float]:
        """Generates strictly 768-dim vector embeddings using robust fallback models."""
        if not self.has_api_key or not self.client or not text.strip():
            return [0.0] * self.vector_dim

        config = get_llm_config()
        active_embedding_model = config.get("embedding_model", "gemini-embedding-001")
        candidate_models = [active_embedding_model, "text-embedding-004", "gemini-embedding-001"]
        
        seen = set()
        candidates = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

        for model_name in candidates:
            for attempt in range(retries):
                try:
                    response = self.client.models.embed_content(
                        model=model_name, contents=text[:2000], config=types.EmbedContentConfig()
                    )
                    if response and response.embeddings and len(response.embeddings) > 0:
                        embedding = list(response.embeddings[0].values)
                        if len(embedding) == self.vector_dim:
                            return embedding
                        elif len(embedding) < self.vector_dim:
                            return embedding + [0.0] * (self.vector_dim - len(embedding))
                        else:
                            return embedding[:self.vector_dim]
                except Exception as e:
                    if attempt == retries - 1 and model_name == candidates[-1]:
                        print(f"[WARN] All embedding models failed: {e}")
                        return [0.0] * self.vector_dim
                    time.sleep(0.5 * (attempt + 1))
        return [0.0] * self.vector_dim

    def _seed_structured_policies(self):
        """Seeds the knowledge base from CSV taxonomy and KB markdown files."""
        if self.is_seeding:
            return
        self.is_seeding = True
        try:
            points = []
            point_id = 0

            # Seed from CSV taxonomy
            if os.path.exists(self.csv_path):
                with open(self.csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        ref_id = row.get("reference_id") or row.get("ref_id") or f"TAX-{point_id+1}"
                        text = f"Risk Category: {row.get('Category', '')}. Subcategory: {row.get('Subcategory', '')}. Description: {row.get('Description', '')}. Legal Basis: {row.get('Legal_Basis', '')}. Mitigation: {row.get('Mitigation', '')}"
                        embedding = self._get_embedding(text)
                        points.append(
                            PointStruct(
                                id=point_id,
                                vector=embedding,
                                payload={
                                    "ref": ref_id,
                                    "source": "risk_taxonomy",
                                    "category": row.get("Category", ""),
                                    "subcategory": row.get("Subcategory", ""),
                                    "text": text,
                                },
                            )
                        )
                        point_id += 1

            # Seed from KB markdown/txt files
            if os.path.exists(self.kb_dir):
                for file_path in glob.glob(os.path.join(self.kb_dir, "*.*")):
                    if not (file_path.endswith('.md') or file_path.endswith('.txt')):
                        continue
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    chunks = self._chunk_text(content, chunk_size=800, overlap=100)
                    for idx, chunk in enumerate(chunks):
                        ref_id = f"KB-{os.path.basename(file_path).upper()[:8]}-{idx+1}"
                        embedding = self._get_embedding(chunk)
                        points.append(
                            PointStruct(
                                id=point_id,
                                vector=embedding,
                                payload={
                                    "ref": ref_id,
                                    "source": "knowledge_base",
                                    "file": os.path.basename(file_path),
                                    "text": chunk,
                                },
                            )
                        )
                        point_id += 1

            if points:
                self.qdrant.upsert(collection_name=self.collection_name, points=points)
                print(f"[OK] Seeded {len(points)} knowledge points into Qdrant.")
        except Exception as e:
            print(f"[WARN] Seeding error: {e}")
        finally:
            self.is_seeding = False

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """Simple text chunking for KB documents."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    def semantic_search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """Performs semantic search with optional metadata filters."""
        query_vector = self._get_embedding(query[:1000])

        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            if conditions:
                qdrant_filter = Filter(must=conditions)

        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
            )
            return [
                {
                    "ref": r.payload.get("ref", "CLS-GEN-020"),
                    "text": r.payload.get("text", ""),
                    "score": r.score,
                    "source": r.payload.get("source", ""),
                    "category": r.payload.get("category", ""),
                    "file": r.payload.get("file", ""),
                }
                for r in results
            ]
        except Exception as e:
            print(f"[WARN] Search error: {e}")
            return []

    # Alias to ensure backwards compatibility with any other callers
    def retrieve_context(self, query_text: str, top_k: int = 3, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        filters = {"category": category_filter} if category_filter else None
        return self.semantic_search(query_text, top_k=top_k, filters=filters)

    def upsert_document_knowledge(self, doc_id: str, clauses: List[Dict]):
        """Upserts clause-level knowledge from analyzed documents."""
        points = []
        for i, clause in enumerate(clauses):
            text = f"Clause Type: {clause.get('clause_type', 'Unknown')}. Risk: {clause.get('risk_level', 'Unknown')}. Text: {clause.get('extracted_text', '')[:500]}"
            embedding = self._get_embedding(text)
            points.append(
                PointStruct(
                    id=hash(f"{doc_id}_{i}") % (2**31),
                    vector=embedding,
                    payload={
                        "ref": clause.get("rag_reference_used", f"DOC-{doc_id[:6]}-{i+1}"),
                        "source": "document_analysis",
                        "doc_id": doc_id,
                        "clause_type": clause.get("clause_type", ""),
                        "risk_level": clause.get("risk_level", ""),
                        "text": text,
                    },
                )
            )
        if points:
            try:
                self.qdrant.upsert(collection_name=self.collection_name, points=points)
                print(f"[OK] Upserted {len(points)} clause vectors for document {doc_id}")
            except Exception as e:
                print(f"[WARN] Upsert error: {e}")
