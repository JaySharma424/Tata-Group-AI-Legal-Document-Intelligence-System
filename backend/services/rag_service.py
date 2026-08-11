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
  """Production-grade RAG service using the modern Google GenAI SDK."""

  def __init__(self, storage_path: str = "./backend/storage/qdrant_db"):
    self.collection_name = "tata_legal_knowledge_v2"
    self.vector_dim = 768  # Enforced 768-dim vector size
    self.is_seeding = False # Prevent concurrent seeding attempts
    
    # --- DYNAMIC LLM CONFIGURATION ---
    config = get_llm_config()
    api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY")
    
    if api_key:
      self.client = genai.Client(api_key=api_key)
      self.has_api_key = True
    else:
      self.client = None
      self.has_api_key = False
      print("⚠️ GEMINI_API_KEY missing. Vector search will use zero-vectors.")

    os.makedirs(storage_path, exist_ok=True)
    try:
      self.qdrant = QdrantClient(path=storage_path)
      self.qdrant.get_collections()
    except Exception as e:
      if "AlreadyLocked" in str(e) or "already accessed" in str(e):
        print("⚠️ Qdrant disk locked. Falling back to in-memory Qdrant instance.")
        self.qdrant = QdrantClient(location=":memory:")
      else:
        raise e

    current_dir = os.path.dirname(os.path.abspath(__file__))
    self.csv_path = os.path.join(
        os.path.dirname(current_dir), "data", "risk_taxonomy.csv"
    )
    self.kb_dir = os.path.join(
        os.path.dirname(current_dir), "data", "knowledge_base"
    )

    # 🛑 CRITICAL FIX: Ensure collection exists, but DO NOT block startup by seeding here.
    self._ensure_collection_exists(seed_immediately=False)

  def _ensure_collection_exists(self, seed_immediately: bool = True):
    """Creates vector collection if missing or recreates it if vector size mismatches."""
    try:
      collections = [c.name for c in self.qdrant.get_collections().collections]
      if self.collection_name in collections:
        info = self.qdrant.get_collection(self.collection_name)
        existing_dim = info.config.params.vectors.size
        if existing_dim != self.vector_dim:
          print(
              f"⚠️ Dimension mismatch ({existing_dim} vs {self.vector_dim})."
              " Recreating Qdrant collection..."
          )
          self.qdrant.delete_collection(self.collection_name)
          collections.remove(self.collection_name)
    except Exception:
      collections = []

    if self.collection_name not in collections:
      self.qdrant.create_collection(
          collection_name=self.collection_name,
          vectors_config=VectorParams(
              size=self.vector_dim, distance=Distance.COSINE
          ),
      )
      if seed_immediately:
          print("🌱 Seeding RAG knowledge base...")
          self._seed_structured_policies()
      else:
          print("ℹ️ Collection created. Seeding deferred to prevent startup blocking.")

  def _get_embedding(self, text: str, retries: int = 3) -> List[float]:
    """Generates strictly 768-dim vector embeddings using robust fallback models."""
    if not self.has_api_key or not text.strip():
      return [0.0] * self.vector_dim

    # Pull active embedding model from dynamic config
    config = get_llm_config()
    active_embedding_model = config.get("embedding_model", "gemini-embedding-001")
    candidate_models = [active_embedding_model, "gemini-embedding-001"]

    for model_name in candidate_models:
      for attempt in range(retries):
        try:
          response = self.client.models.embed_content(
              model=model_name,
              contents=text[:2000],
              config=types.EmbedContentConfig(
                  output_dimensionality=self.vector_dim
              ),
          )
          if response.embeddings and len(response.embeddings) > 0:
            values = list(response.embeddings[0].values)
            if len(values) > self.vector_dim:
              values = values[: self.vector_dim]
            elif len(values) < self.vector_dim:
              values += [0.0] * (self.vector_dim - len(values))
            return values
        except Exception as e:
          err_msg = str(e)
          if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            wait_time = 2 * (attempt + 1)
            print(f"⏳ Gemini Rate Limit hit. Backing off for {wait_time}s...")
            time.sleep(wait_time)
            continue
          else:
            print(f"⚠️ Embedding failed for {model_name}: {err_msg}. Trying next model...")
            break 

    print("❌ All embedding models failed. Returning zero-vector fallback.")
    return [0.0] * self.vector_dim

  def _parse_structured_policy_file(
      self, file_path: str
  ) -> List[Dict[str, Any]]:
    records = []
    filename = os.path.basename(file_path)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
      content = f.read()

    blocks = re.split(r"\n(?=TITLE:)", content.strip())

    for idx, block in enumerate(blocks):
      if not block.strip():
        continue

      title_match = re.search(r"TITLE:\s*(.*)", block)
      category_match = re.search(r"CATEGORY:\s*(.*)", block)
      ref_match = re.search(r"REFERENCE_ID:\s*(.*)", block)
      jurisdiction_match = re.search(r"JURISDICTION:\s*(.*)", block)
      guidance_match = re.search(r"GUIDANCE:\s*(.*)", block, re.DOTALL)

      ref_id = (
          ref_match.group(1).strip()
          if ref_match
          else f"KB-{filename.upper()}-{idx+1}"
      )
      title = (
          title_match.group(1).strip() if title_match else "Corporate Policy"
      )
      category = (
          category_match.group(1).strip()
          if category_match
          else "GENERAL COMPLIANCE"
      )
      jurisdiction = (
          jurisdiction_match.group(1).strip() if jurisdiction_match else "Global"
      )
      guidance = (
          guidance_match.group(1).strip() if guidance_match else block.strip()
      )

      semantic_text = (
          f"[{category}] {title}: {guidance} (Jurisdiction: {jurisdiction})"
      )

      records.append({
          "ref_id": ref_id,
          "title": title,
          "category": category,
          "jurisdiction": jurisdiction,
          "guidance": guidance,
          "source_file": filename,
          "semantic_text": semantic_text,
      })

    return records

  def _seed_structured_policies(self):
    if self.is_seeding:
        print("ℹ️ Seeding already in progress, skipping...")
        return
        
    self.is_seeding = True
    try:
        policies = []
        point_id_counter = 1

        if os.path.exists(self.csv_path):
          try:
            with open(self.csv_path, mode="r", encoding="utf-8") as file:
              reader = csv.DictReader(file)
              for row in reader:
                ref_id = (
                    row.get("reference_id")
                    or row.get("ref_id")
                    or f"TAX-{point_id_counter}"
                )
                risk_level = row.get("risk_level", "MEDIUM").upper()
                policy_txt = row.get("policy_text") or row.get("trigger", "")
                guidelines = row.get("handling_guidelines") or row.get("action", "")

                semantic_text = f"[{risk_level} RISK TAXONOMY] Ref: {ref_id} | Policy: {policy_txt} | Guidelines: {guidelines}"

                policies.append({
                    "id": point_id_counter,
                    "payload": {
                        "ref": ref_id,
                        "text": semantic_text,
                        "category": "RISK_TAXONOMY",
                        "risk_level": risk_level,
                    },
                })
                point_id_counter += 1
          except Exception as e:
            print(f"Error reading risk_taxonomy.csv: {e}")

        if os.path.exists(self.kb_dir):
          txt_files = glob.glob(os.path.join(self.kb_dir, "*.txt"))
          for file_path in txt_files:
            parsed_records = self._parse_structured_policy_file(file_path)
            for rec in parsed_records:
              policies.append({
                  "id": point_id_counter,
                  "payload": {
                      "ref": rec["ref_id"],
                      "text": (
                          f"[{rec['ref_id']}] {rec['title']} - {rec['guidance']}"
                      ),
                      "title": rec["title"],
                      "category": rec["category"],
                      "jurisdiction": rec["jurisdiction"],
                      "source_file": rec["source_file"],
                  },
                  "embedding_text": rec["semantic_text"],
              })
              point_id_counter += 1

        points = []
        for idx, p in enumerate(policies):
          embed_input = p.get("embedding_text", p["payload"]["text"])
          vector = self._get_embedding(embed_input)
          points.append(
              PointStruct(id=p["id"], vector=vector, payload=p["payload"])
          )

          if (idx + 1) % 10 == 0:
            time.sleep(0.5)

        if points:
          self.qdrant.upsert(collection_name=self.collection_name, points=points)
          print(
              f"✅ RAG Engine: Successfully embedded {len(points)} legal records into Qdrant."
          )
    finally:
        self.is_seeding = False

  def retrieve_context(
      self,
      query_text: str,
      top_k: int = 3,
      category_filter: Optional[str] = None,
  ) -> List[Dict[str, Any]]:
    """Retrieves top matching legal policies from Qdrant vector database."""
    if not query_text:
      return []
      
    try:
        collection_info = self.qdrant.get_collection(self.collection_name)
        if collection_info.points_count == 0:
            print("⚠️ Qdrant database is empty upon first query. Seeding now (Lazy Load)...")
            self._seed_structured_policies()
    except Exception as e:
        print(f"Error checking collection info: {e}")


    query_vector = self._get_embedding(query_text[:1000])
    
    if all(v == 0.0 for v in query_vector):
        print("⚠️ Aborting Qdrant search due to zero-vector embedding failure.")
        return []

    query_filter = None
    if category_filter:
      query_filter = Filter(
          must=[
              FieldCondition(
                  key="category", match=MatchValue(value=category_filter)
              )
          ]
      )

    try:
      results = self.qdrant.search(
          collection_name=self.collection_name,
          query_vector=query_vector,
          query_filter=query_filter,
          limit=top_k,
      )
      return [
          {
              "ref": hit.payload.get("ref", "CLS-GEN-020"),
              "text": hit.payload.get("text", ""),
              "title": hit.payload.get("title", ""),
              "category": hit.payload.get("category", ""),
          }
          for hit in results
      ]
    except Exception as e:
      print(f"Qdrant search error: {e}")
      return []