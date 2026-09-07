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
from backend.database import SessionLocal, Base, engine
from backend.models import KnowledgeBaseModel
from backend.services.llm_config import get_llm_config


class RAGKnowledgeService:
    """Production service syncing knowledge base into PostgreSQL and Qdrant Cloud cluster."""

    def __init__(self, storage_path: str = "./backend/storage/qdrant_db"):
        self.collection_name = "tata_legal_knowledge_v4"
        self.vector_dim = 768
        self.is_seeding = False
        self.csv_path = None
        self.txt_files = []

        # Ensure database tables exist in PostgreSQL
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"[WARN] Postgres table creation error: {e}")

        # Resolve Google API key for vector embeddings
        google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        config = get_llm_config()
        db_key = config.get("api_key", "")
        if db_key and not any(db_key.startswith(p) for p in ("nvapi-", "sk-", "gsk_")):
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

        # Connect strictly to Qdrant Cloud cluster
        qdrant_url = (os.getenv("QDRANT_URL") or "").strip()
        qdrant_api_key = (os.getenv("QDRANT_API_KEY") or "").strip()

        if qdrant_url and qdrant_api_key:
            if not qdrant_url.startswith("http"):
                qdrant_url = f"https://{qdrant_url}"
            try:
                self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=60)
                self.qdrant.get_collections()
                print(f"[OK] Connected to Qdrant Cloud cluster at: {qdrant_url}")
            except Exception as e:
                print(f"[ERROR] Failed to connect to Qdrant Cloud: {e}. Falling back to in-memory.")
                self.qdrant = QdrantClient(":memory:")
        else:
            print("[WARN] QDRANT_URL or QDRANT_API_KEY missing from environment. Using in-memory fallback.")
            self.qdrant = QdrantClient(":memory:")

        self._find_data_sources()

    def _find_data_sources(self):
        csv_candidates = [
            os.path.join("backend", "data", "risk_taxonomy.csv"),
            os.path.join("data", "risk_taxonomy.csv"),
            "risk_taxonomy.csv",
        ]
        self.csv_path = next((p for p in csv_candidates if os.path.exists(p)), None)

        kb_dirs = [
            os.path.join("backend", "data", "knowledge_base"),
            os.path.join("backend", "data"),
            os.path.join("data", "knowledge_base"),
            "data",
            ".",
        ]
        self.txt_files = []
        for d in kb_dirs:
            if os.path.exists(d):
                for f in glob.glob(os.path.join(d, "*.txt")):
                    base = os.path.basename(f)
                    if base != "requirements.txt" and base not in [os.path.basename(x) for x in self.txt_files]:
                        self.txt_files.append(f)

    def ensure_seeded(self):
        """Ensures the collection exists, syncs into PostgreSQL, and seeds Qdrant."""
        try:
            collections = [c.name for c in self.qdrant.get_collections().collections]
            collection_needs_points = False

            if self.collection_name not in collections:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE),
                )
                collection_needs_points = True
            else:
                col_info = self.qdrant.get_collection(self.collection_name)
                if (col_info.points_count or 0) == 0:
                    collection_needs_points = True

            if collection_needs_points:
                print(f"[INFO] Seeding PostgreSQL and Qdrant collection '{self.collection_name}'...")
                self._seed_structured_policies()
        except Exception as e:
            print(f"[WARN] Collection initialization error: {e}")

    def _get_embedding(self, text: str, retries: int = 3) -> List[float]:
        if not self.has_api_key or not self.client or not text.strip():
            return [0.0] * self.vector_dim

        for attempt in range(retries):
            try:
                response = self.client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=text[:2000],
                    config=types.EmbedContentConfig(),
                )
                if response and response.embeddings:
                    emb = list(response.embeddings[0].values)
                    if len(emb) == self.vector_dim:
                        return emb
                    return emb[:self.vector_dim] if len(emb) > self.vector_dim else emb + [0.0] * (self.vector_dim - len(emb))
            except Exception:
                time.sleep(0.3 * (attempt + 1))
        return [0.0] * self.vector_dim

    def _seed_structured_policies(self):
        if self.is_seeding:
            return
        self.is_seeding = True
        db = SessionLocal()
        try:
            parsed_entries = []

            # 1. Parse risk_taxonomy.csv
            if self.csv_path and os.path.exists(self.csv_path):
                with open(self.csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        ref = row.get("reference_id") or f"TAX-{idx+1}"
                        clause_type = row.get("clause_type") or "General"
                        policy_text = row.get("policy_text") or ""
                        guidelines = row.get("handling_guidelines") or ""
                        search_text = (
                            f"Clause Type: {clause_type}. Reference ID: {ref}. "
                            f"Mandatory Policy: {policy_text}. Handling Guidelines: {guidelines}"
                        )
                        parsed_entries.append({
                            "ref": ref,
                            "title": f"{clause_type} Compliance Rule",
                            "category": clause_type,
                            "jurisdiction": "Global",
                            "guidance": policy_text or guidelines,
                            "source": "risk_taxonomy.csv",
                            "search_text": search_text
                        })

            # 2. Parse all *.txt Knowledge Base files
            for tf in self.txt_files:
                with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                raw_blocks = re.split(r'\n\s*\n(?=TITLE:)|(?<=\n)(?=TITLE:)', content.strip())
                for b_idx, block in enumerate(raw_blocks):
                    block = block.strip()
                    if not block.startswith("TITLE:"):
                        continue
                    item = {"source": os.path.basename(tf)}
                    for line in block.split("\n"):
                        line = line.strip()
                        if line.startswith("TITLE:"):
                            item["title"] = line[len("TITLE:"):].strip()
                        elif line.startswith("CATEGORY:"):
                            item["category"] = line[len("CATEGORY:"):].strip()
                        elif line.startswith("REFERENCE_ID:"):
                            item["ref"] = line[len("REFERENCE_ID:"):].strip()
                        elif line.startswith("JURISDICTION:"):
                            item["jurisdiction"] = line[len("JURISDICTION:"):].strip()
                        elif line.startswith("GUIDANCE:"):
                            item["guidance"] = line[len("GUIDANCE:"):].strip()

                    ref = item.get("ref")
                    if ref:
                        cat = item.get("category", "General Provision")
                        guidance = item.get("guidance", "")
                        search_text = (
                            f"Policy Title: {item.get('title', '')}. Category: {cat}. "
                            f"Reference ID: {ref}. Jurisdiction: {item.get('jurisdiction', 'Global')}. "
                            f"Guidance Rule: {guidance}"
                        )
                        parsed_entries.append({
                            "ref": ref,
                            "title": item.get("title", f"Policy {ref}"),
                            "category": cat,
                            "jurisdiction": item.get("jurisdiction", "Global"),
                            "guidance": guidance,
                            "source": item["source"],
                            "search_text": search_text
                        })

            points = []
            for entry in parsed_entries:
                ref = entry["ref"]
                deterministic_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"tata_kb_{ref}"))

                # Step A: Persist in PostgreSQL
                existing_record = db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == deterministic_uuid).first()
                if not existing_record:
                    db.add(KnowledgeBaseModel(
                        id=deterministic_uuid,
                        reference_id=ref,
                        title=entry["title"],
                        category=entry["category"],
                        jurisdiction=entry["jurisdiction"],
                        guidance=entry["guidance"],
                        source_file=entry["source"],
                        search_text=entry["search_text"]
                    ))

                # Step B: Generate Embedding & Prepare Qdrant Cloud Point
                embedding = self._get_embedding(entry["search_text"])
                points.append(
                    PointStruct(
                        id=deterministic_uuid,
                        vector=embedding,
                        payload={
                            "uuid": deterministic_uuid,
                            "ref": ref,
                            "title": entry["title"],
                            "clause_type": entry["category"],
                            "category": entry["category"],
                            "jurisdiction": entry["jurisdiction"],
                            "policy_text": entry["guidance"],
                            "guidelines": entry["guidance"],
                            "source": entry["source"],
                            "text": entry["search_text"],
                        }
                    )
                )

            db.commit()
            print(f"[OK] Synced {len(parsed_entries)} knowledge records into PostgreSQL table 'knowledge_base'.")

            # Step C: Upsert into Qdrant Cloud
            if points:
                for i in range(0, len(points), 50):
                    self.qdrant.upsert(
                        collection_name=self.collection_name,
                        points=points[i:i + 50],
                    )
                print(f"[OK] Upserted {len(points)} vectors into Qdrant Cloud cluster collection '{self.collection_name}'.")

        except Exception as e:
            db.rollback()
            print(f"[WARN] Knowledge seeding error: {e}")
        finally:
            db.close()
            self.is_seeding = False

    def semantic_search(self, query: str, top_k: int = 1, filters: Optional[Dict] = None) -> List[Dict]:
        """Performs vector search in Qdrant and retrieves verified policy records via UUID."""
        self.ensure_seeded()
        query_vector = self._get_embedding(query[:1500])
        qdrant_filter = None
        if filters:
            conditions = [FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filters.items()]
            if conditions:
                qdrant_filter = Filter(must=conditions)

        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
            )

            db = SessionLocal()
            matched_items = []
            try:
                for r in results:
                    matched_uuid = str(r.id)
                    # Cross-verify against PostgreSQL using UUID
                    pg_record = db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == matched_uuid).first()

                    matched_items.append({
                        "uuid": matched_uuid,
                        "ref": pg_record.reference_id if pg_record else r.payload.get("ref", "N/A"),
                        "title": pg_record.title if pg_record else r.payload.get("title", ""),
                        "clause_type": pg_record.category if pg_record else r.payload.get("clause_type", "General Provision"),
                        "policy_text": pg_record.guidance if pg_record else r.payload.get("policy_text", ""),
                        "guidelines": pg_record.guidance if pg_record else r.payload.get("guidelines", ""),
                        "source": pg_record.source_file if pg_record else r.payload.get("source", ""),
                        "text": pg_record.search_text if pg_record else r.payload.get("text", ""),
                        "score": r.score,
                    })
            finally:
                db.close()

            return matched_items

        except Exception as e:
            print(f"[WARN] Qdrant search error: {e}")
            return []