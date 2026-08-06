import os
import csv
import glob
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
# NEW: Import the RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter

class RAGKnowledgeService:
    def __init__(self):
        self.qdrant = QdrantClient(location=":memory:")
        self.collection_name = "tata_legal_knowledge"
        
        # Load local sentence transformer model (MiniLM-L6-v2)
        print("Loading local embedding model: all-MiniLM-L6-v2...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Resolve path to risk_taxonomy.csv across potential directory levels
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_path = os.path.join(os.path.dirname(current_dir), "data", "risk_taxonomy.csv")
        if not os.path.exists(self.csv_path):
            self.csv_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "data", "risk_taxonomy.csv")
        if not os.path.exists(self.csv_path):
            self.csv_path = "risk_taxonomy.csv"

        # Resolve path to knowledge base directory
        self.kb_dir = os.path.join(os.path.dirname(current_dir), "data", "knowledge_base")
        if not os.path.exists(self.kb_dir):
            self.kb_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "backend", "data", "knowledge_base")
        if not os.path.exists(self.kb_dir):
            self.kb_dir = "backend/data/knowledge_base"

        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        self.qdrant.recreate_collection(
            collection_name=self.collection_name,
            # MiniLM-L6-v2 uses 384 dimensions
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        self._seed_default_policies()

    def _get_embedding(self, text: str):
        try:
            vector = self.embedding_model.encode(text)
            return vector.tolist()
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * 384 

    def _seed_default_policies(self):
        policies = []
        point_id_counter = 1
        
        # 1. Ingest from risk_taxonomy.csv
        if os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, mode='r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        risk_level = row.get('risk_level', '').upper()
                        ref_id = row.get('reference_id', 'TAX-REF')
                        policy_txt = row.get('policy_text', '') or row.get('trigger', '')
                        guidelines = row.get('handling_guidelines', '') or row.get('action', '')
                        
                        policies.append({
                            "id": point_id_counter,
                            "ref": ref_id,
                            "text": f"[{risk_level} RISK TARGET] Policy: {policy_txt} | Guidelines: {guidelines}"
                        })
                        point_id_counter += 1
            except Exception as e:
                print(f"Error reading risk_taxonomy.csv: {e}")

        # 2. Ingest from Knowledge Base text files using RecursiveCharacterTextSplitter
        if os.path.exists(self.kb_dir):
            txt_files = glob.glob(os.path.join(self.kb_dir, "*.txt"))
            
            # NEW: Initialize the text splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, 
                chunk_overlap=150,
                length_function=len
            )
            
            for file_path in txt_files:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        filename = os.path.basename(file_path)
                        
                        # NEW: Split the document content into chunks
                        chunks = text_splitter.split_text(content)
                        
                        for i, chunk in enumerate(chunks):
                            policies.append({
                                "id": point_id_counter,
                                "ref": f"KB-{filename.upper()}-PART-{i+1}",
                                "text": f"[POLICY DOCUMENT: {filename} (Part {i+1})] {chunk}"
                            })
                            point_id_counter += 1
                except Exception as e:
                    print(f"Error reading KB file {file_path}: {e}")

        # 3. Fallback defaults if nothing was found on disk
        if not policies:
            policies = [
                {"id": 1, "ref": "POL-IND-2026-01", "text": "All vendor agreements must mandate explicit confidentiality obligations. Anonymized data may not be used by 3rd-party LLMs without consent."},
                {"id": 2, "ref": "LAW-CORP-882", "text": "Governing law must default to Indian Law with Mumbai jurisdiction. US jurisdictions like New York are strictly discouraged."},
                {"id": 3, "ref": "RISK-CAP-99", "text": "Liability must be capped at 12 months fees. Unlimited liability requires General Counsel approval."}
            ]
        
        # 4. Embed and upsert into Qdrant
        points = []
        for p in policies:
            vector = self._get_embedding(p["text"])
            points.append(PointStruct(id=p["id"], vector=vector, payload=p))
            
        if points:
            self.qdrant.upsert(collection_name=self.collection_name, points=points)
            print(f"Successfully embedded {len(points)} policies and taxonomy rules into Qdrant RAG database using MiniLM.")

    def retrieve_context(self, query_text: str, top_k: int = 4):
        if not query_text:
            return []
            
        query_vector = self._get_embedding(query_text[:1000])
        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=0.55  # Threshold tuned for MiniLM semantic similarity
            )
            return [{"ref": hit.payload["ref"], "text": hit.payload["text"]} for hit in results]
        except Exception as e:
            print(f"Qdrant search error: {e}")
            return []