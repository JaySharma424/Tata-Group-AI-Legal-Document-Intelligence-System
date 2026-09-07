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
from backend.services.llm_config import get_llm_config


class RAGKnowledgeService:
    """Production RAG service loading risk_taxonomy.csv and all *.txt knowledge base files into Qdrant."""

    def __init__(self, storage_path: str = "./backend/storage/qdrant_db"):
        # Bump to v4 to guarantee fresh, unpoisoned collection creation
        self.collection_name = "tata_legal_knowledge_v4"
        self.vector_dim = 768
        self.is_seeding = False

        # Pre-initialize variables before resolving data sources
        self.csv_path = None
        self.txt_files = []

        # Resolve Google API key dynamically
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

        # Connect to Qdrant Cloud or in-memory fallback
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if qdrant_url and qdrant_api_key:
            try:
                self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
                self.qdrant.get_collections()
                print("[OK] Connected to Qdrant Cloud cluster.")
            except Exception as e:
                print(f"[WARN] Qdrant Cloud connection failed: {e}. Using in-memory.")
                self.qdrant = QdrantClient(":memory:")
        else:
            self.qdrant = QdrantClient(":memory:")

        # Locate risk_taxonomy.csv and txt files dynamically across repo roots
        self._find_data_sources()

        # Synchronous execution: ensures Qdrant contains all policies before searches run
        self._ensure_collection_exists()

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

    def _ensure_collection_exists(self):
        try:
            collections = [c.name for c in self.qdrant.get_collections().collections]
            if self.collection_name not in collections:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE),
                )
                print(f"[INFO] Collection '{self.collection_name}' initialized. Seeding knowledge base...")
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
                time.sleep(0.5 * (attempt + 1))
        return [0.0] * self.vector_dim

    def _seed_structured_policies(self):
        if self.is_seeding:
            return
        self.is_seeding = True
        try:
            points = []

            # 1. Seed from risk_taxonomy.csv
            if self.csv_path and os.path.exists(self.csv_path):
                with open(self.csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        ref = row.get("reference_id") or f"TAX-{idx+1}"
                        clause_type = row.get("clause_type") or "General"
                        risk_level = (row.get("risk_level") or "MEDIUM").upper()
                        policy_text = row.get("policy_text") or ""
                        guidelines = row.get("handling_guidelines") or ""

                        search_text = (
                            f"Clause Type: {clause_type}. Reference ID: {ref}. "
                            f"Risk Severity: {risk_level}. Mandatory Policy: {policy_text}. "
                            f"Handling Guidelines: {guidelines}"
                        )
                        embedding = self._get_embedding(search_text)
                        deterministic_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"tax_{ref}_{idx}"))
                        points.append(
                            PointStruct(
                                id=deterministic_id,
                                vector=embedding,
                                payload={
                                    "ref": ref,
                                    "source": "risk_taxonomy.csv",
                                    "clause_type": clause_type,
                                    "risk_level": risk_level,
                                    "policy_text": policy_text,
                                    "guidelines": guidelines,
                                    "text": search_text,
                                },
                            )
                        )

            # 2. Seed from all *.txt company knowledge base files
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
                        embedding = self._get_embedding(search_text)
                        deterministic_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"kb_{ref}_{b_idx}"))
                        points.append(
                            PointStruct(
                                id=deterministic_id,
                                vector=embedding,
                                payload={
                                    "ref": ref,
                                    "source": item["source"],
                                    "clause_type": cat,
                                    "policy_text": guidance,
                                    "guidelines": guidance,
                                    "text": search_text,
                                },
                            )
                        )

            if points:
                for i in range(0, len(points), 50):
                    self.qdrant.upsert(
                        collection_name=self.collection_name,
                        points=points[i:i + 50],
                    )
                print(f"[OK] Successfully seeded {len(points)} knowledge points into Qdrant collection '{self.collection_name}'.")
        except Exception as e:
            print(f"[WARN] Knowledge seeding error: {e}")
        finally:
            self.is_seeding = False

    def semantic_search(self, query: str, top_k: int = 1, filters: Optional[Dict] = None) -> List[Dict]:
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
            return [
                {
                    "ref": r.payload.get("ref", "N/A"),
                    "text": r.payload.get("text", ""),
                    "policy_text": r.payload.get("policy_text", ""),
                    "guidelines": r.payload.get("guidelines", ""),
                    "clause_type": r.payload.get("clause_type", "General Provision"),
                    "risk_level": r.payload.get("risk_level", None),
                    "score": r.score,
                    "source": r.payload.get("source", ""),
                }
                for r in results
            ]
        except Exception as e:
            print(f"[WARN] Qdrant search error: {e}")
            return []

    def upsert_document_knowledge(self, doc_id: str, clauses: List[Dict]):
        points = []
        for i, clause in enumerate(clauses):
            text_val = (
                f"Clause Type: {clause.get('clause_type', 'General')}. "
                f"Risk: {clause.get('risk_level', 'Unspecified')}. "
                f"Text: {clause.get('extracted_text', '')[:600]}"
            )
            emb = self._get_embedding(text_val)
            deterministic_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_{i}"))
            points.append(
                PointStruct(
                    id=deterministic_id,
                    vector=emb,
                    payload={
                        "ref": clause.get("rag_reference_used", f"DOC-{doc_id[:6]}-{i+1}"),
                        "source": "analyzed_contract",
                        "doc_id": doc_id,
                        "clause_type": clause.get("clause_type", ""),
                        "risk_level": clause.get("risk_level", ""),
                        "text": text_val,
                    },
                )
            )
        if points:
            try:
                self.qdrant.upsert(collection_name=self.collection_name, points=points)
            except Exception as e:
                print(f"[WARN] Knowledge upsert error: {e}")import csv
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
from backend.services.llm_config import get_llm_config


class RAGKnowledgeService:
    """Production RAG service loading risk_taxonomy.csv and all *.txt knowledge base files into Qdrant."""

    def __init__(self, storage_path: str = "./backend/storage/qdrant_db"):
        # Bump to v4 to guarantee fresh, unpoisoned collection creation
        self.collection_name = "tata_legal_knowledge_v4"
        self.vector_dim = 768
        self.is_seeding = False

        # Pre-initialize variables before resolving data sources
        self.csv_path = None
        self.txt_files = []

        # Resolve Google API key dynamically
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

        # Connect to Qdrant Cloud or in-memory fallback
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if qdrant_url and qdrant_api_key:
            try:
                self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
                self.qdrant.get_collections()
                print("[OK] Connected to Qdrant Cloud cluster.")
            except Exception as e:
                print(f"[WARN] Qdrant Cloud connection failed: {e}. Using in-memory.")
                self.qdrant = QdrantClient(":memory:")
        else:
            self.qdrant = QdrantClient(":memory:")

        # Locate risk_taxonomy.csv and txt files dynamically across repo roots
        self._find_data_sources()

        # Synchronous execution: ensures Qdrant contains all policies before searches run
        self._ensure_collection_exists()

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

    def _ensure_collection_exists(self):
        try:
            collections = [c.name for c in self.qdrant.get_collections().collections]
            if self.collection_name not in collections:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE),
                )
                print(f"[INFO] Collection '{self.collection_name}' initialized. Seeding knowledge base...")
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
                time.sleep(0.5 * (attempt + 1))
        return [0.0] * self.vector_dim

    def _seed_structured_policies(self):
        if self.is_seeding:
            return
        self.is_seeding = True
        try:
            points = []

            # 1. Seed from risk_taxonomy.csv
            if self.csv_path and os.path.exists(self.csv_path):
                with open(self.csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        ref = row.get("reference_id") or f"TAX-{idx+1}"
                        clause_type = row.get("clause_type") or "General"
                        risk_level = (row.get("risk_level") or "MEDIUM").upper()
                        policy_text = row.get("policy_text") or ""
                        guidelines = row.get("handling_guidelines") or ""

                        search_text = (
                            f"Clause Type: {clause_type}. Reference ID: {ref}. "
                            f"Risk Severity: {risk_level}. Mandatory Policy: {policy_text}. "
                            f"Handling Guidelines: {guidelines}"
                        )
                        embedding = self._get_embedding(search_text)
                        deterministic_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"tax_{ref}_{idx}"))
                        points.append(
                            PointStruct(
                                id=deterministic_id,
                                vector=embedding,
                                payload={
                                    "ref": ref,
                                    "source": "risk_taxonomy.csv",
                                    "clause_type": clause_type,
                                    "risk_level": risk_level,
                                    "policy_text": policy_text,
                                    "guidelines": guidelines,
                                    "text": search_text,
                                },
                            )
                        )

            # 2. Seed from all *.txt company knowledge base files
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
                        embedding = self._get_embedding(search_text)
                        deterministic_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"kb_{ref}_{b_idx}"))
                        points.append(
                            PointStruct(
                                id=deterministic_id,
                                vector=embedding,
                                payload={
                                    "ref": ref,
                                    "source": item["source"],
                                    "clause_type": cat,
                                    "policy_text": guidance,
                                    "guidelines": guidance,
                                    "text": search_text,
                                },
                            )
                        )

            if points:
                for i in range(0, len(points), 50):
                    self.qdrant.upsert(
                        collection_name=self.collection_name,
                        points=points[i:i + 50],
                    )
                print(f"[OK] Successfully seeded {len(points)} knowledge points into Qdrant collection '{self.collection_name}'.")
        except Exception as e:
            print(f"[WARN] Knowledge seeding error: {e}")
        finally:
            self.is_seeding = False

    def semantic_search(self, query: str, top_k: int = 1, filters: Optional[Dict] = None) -> List[Dict]:
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
            return [
                {
                    "ref": r.payload.get("ref", "N/A"),
                    "text": r.payload.get("text", ""),
                    "policy_text": r.payload.get("policy_text", ""),
                    "guidelines": r.payload.get("guidelines", ""),
                    "clause_type": r.payload.get("clause_type", "General Provision"),
                    "risk_level": r.payload.get("risk_level", None),
                    "score": r.score,
                    "source": r.payload.get("source", ""),
                }
                for r in results
            ]
        except Exception as e:
            print(f"[WARN] Qdrant search error: {e}")
            return []

    def upsert_document_knowledge(self, doc_id: str, clauses: List[Dict]):
        points = []
        for i, clause in enumerate(clauses):
            text_val = (
                f"Clause Type: {clause.get('clause_type', 'General')}. "
                f"Risk: {clause.get('risk_level', 'Unspecified')}. "
                f"Text: {clause.get('extracted_text', '')[:600]}"
            )
            emb = self._get_embedding(text_val)
            deterministic_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_{i}"))
            points.append(
                PointStruct(
                    id=deterministic_id,
                    vector=emb,
                    payload={
                        "ref": clause.get("rag_reference_used", f"DOC-{doc_id[:6]}-{i+1}"),
                        "source": "analyzed_contract",
                        "doc_id": doc_id,
                        "clause_type": clause.get("clause_type", ""),
                        "risk_level": clause.get("risk_level", ""),
                        "text": text_val,
                    },
                )
            )
        if points:
            try:
                self.qdrant.upsert(collection_name=self.collection_name, points=points)
            except Exception as e:
                print(f"[WARN] Knowledge upsert error: {e}")