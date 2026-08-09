import csv
import glob
import os
import re
from typing import Any, Dict, List, Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings
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
  """Production-grade RAG service using Gemini API embeddings (0 MB local RAM usage)."""

  def __init__(self, storage_path: str = "./backend/storage/qdrant_db"):
    self.collection_name = "tata_legal_knowledge"
    self.vector_dim = 768  # Gemini text-embedding-004 output dimension

    # 1. Disk Connection with In-Memory fallback for lock resilience
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

    # 2. Cloud API Embedding Model (Replaces local heavy SentenceTransformer)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
      self.embedding_model = GoogleGenerativeAIEmbeddings(
          model="text/text-embedding-004", google_api_key=api_key
      )
    else:
      self.embedding_model = None
      print(
          "⚠️ GEMINI_API_KEY not found. Embeddings will fallback to zero vectors."
      )

    # 3. Path Resolution
    current_dir = os.path.dirname(os.path.abspath(__file__))
    self.csv_path = os.path.join(
        os.path.dirname(current_dir), "data", "risk_taxonomy.csv"
    )
    self.kb_dir = os.path.join(
        os.path.dirname(current_dir), "data", "knowledge_base"
    )

    self._ensure_collection_exists()

  def _ensure_collection_exists(self):
      """Creates vector collection if missing, seeding only if empty."""
      try:
        collections = [
            c.name for c in self.qdrant.get_collections().collections
        ]
      except Exception:
        collections = []

      if self.collection_name not in collections:
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_dim, distance=Distance.COSINE
            ),
        )

      # Check count to avoid blocking bootup with repeated embedding API calls
      try:
        collection_info = self.qdrant.get_collection(self.collection_name)
        if collection_info.points_count == 0:
          print("🌱 Seeding RAG knowledge base for the first time...")
          self._seed_structured_policies()
      except Exception as e:
        print(f"⚠️ RAG initialization check skipped: {e}")

  def _get_embedding(self, text: str) -> List[float]:
    """Generates vector embedding via Gemini API."""
    try:
      if self.embedding_model:
        return self.embedding_model.embed_query(text)
      return [0.0] * self.vector_dim
    except Exception as e:
      print(f"Embedding error: {e}")
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
    for p in policies:
      embed_input = p.get("embedding_text", p["payload"]["text"])
      vector = self._get_embedding(embed_input)
      points.append(
          PointStruct(id=p["id"], vector=vector, payload=p["payload"])
      )

    if points:
      self.qdrant.upsert(collection_name=self.collection_name, points=points)
      print(
          f"✅ RAG Engine: Embedded {len(points)} structured legal records"
          " into Qdrant using Gemini Embeddings."
      )

  def retrieve_context(
      self,
      query_text: str,
      top_k: int = 4,
      category_filter: Optional[str] = None,
  ) -> List[Dict[str, str]]:
    if not query_text:
      return []

    query_vector = self._get_embedding(query_text[:1000])

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
          score_threshold=0.45,
      )
      return [
          {
              "ref": hit.payload.get("ref", "REF-N/A"),
              "text": hit.payload.get("text", ""),
          }
          for hit in results
      ]
    except Exception as e:
      print(f"Qdrant search error: {e}")
      return []