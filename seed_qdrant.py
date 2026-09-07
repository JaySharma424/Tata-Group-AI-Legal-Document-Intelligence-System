# seed_qdrant.py
import os, glob, re, csv, uuid, time
from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from backend.database import SessionLocal, Base, engine
from backend.models import KnowledgeBaseModel

Base.metadata.create_all(bind=engine)
db = SessionLocal()

qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")
google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=google_key)
qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

col_name = "tata_legal_knowledge_v4"
collections = [c.name for c in qdrant.get_collections().collections]
if col_name not in collections:
    qdrant.create_collection(collection_name=col_name, vectors_config=VectorParams(size=768, distance=Distance.COSINE))

parsed = []
# 1. Parse CSV
csv_path = "data/risk_taxonomy.csv" if os.path.exists("data/risk_taxonomy.csv") else "backend/data/risk_taxonomy.csv"
if os.path.exists(csv_path):
    with open(csv_path, "r", encoding="utf-8") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            ref = row.get("reference_id") or f"TAX-{idx+1}"
            text = f"Clause Type: {row.get('clause_type')}. Reference ID: {ref}. Mandatory Policy: {row.get('policy_text')}. Guidelines: {row.get('handling_guidelines')}"
            parsed.append({"ref": ref, "title": row.get("clause_type", "Rule"), "category": row.get("clause_type", "General"), "guidance": row.get("policy_text", ""), "source": "risk_taxonomy.csv", "text": text})

# 2. Parse TXT files
for fpath in glob.glob("backend/data/knowledge_base/*.txt") + glob.glob("data/*.txt") + glob.glob("*.txt"):
    if "requirements.txt" in fpath or "new 1.txt" in fpath: continue
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    for block in re.split(r'\n\s*\n(?=TITLE:)|(?<=\n)(?=TITLE:)', content.strip()):
        if not block.strip().startswith("TITLE:"): continue
        item = {}
        for line in block.split("\n"):
            if line.startswith("TITLE:"): item["title"] = line[6:].strip()
            elif line.startswith("CATEGORY:"): item["category"] = line[9:].strip()
            elif line.startswith("REFERENCE_ID:"): item["ref"] = line[13:].strip()
            elif line.startswith("GUIDANCE:"): item["guidance"] = line[9:].strip()
        if item.get("ref"):
            search_text = f"Policy Title: {item.get('title')}. Category: {item.get('category')}. Reference ID: {item.get('ref')}. Guidance Rule: {item.get('guidance')}"
            parsed.append({"ref": item["ref"], "title": item.get("title", ""), "category": item.get("category", "General"), "guidance": item.get("guidance", ""), "source": os.path.basename(fpath), "text": search_text})

points = []
print(f"Embedding {len(parsed)} entries...")
for i, entry in enumerate(parsed):
    det_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"tata_kb_{entry['ref']}"))
    if not db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == det_uuid).first():
        db.add(KnowledgeBaseModel(id=det_uuid, reference_id=entry["ref"], title=entry["title"], category=entry["category"], guidance=entry["guidance"], source_file=entry["source"], search_text=entry["text"]))
    
    resp = client.models.embed_content(model="gemini-embedding-001", contents=entry["text"][:2000])
    emb = list(resp.embeddings[0].values)
    points.append(PointStruct(id=det_uuid, vector=emb, payload={"ref": entry["ref"], "category": entry["category"], "guidance": entry["guidance"], "source": entry["source"], "text": entry["text"]}))
    time.sleep(0.1)

db.commit()
db.close()

for i in range(0, len(points), 50):
    qdrant.upsert(collection_name=col_name, points=points[i:i+50])
print(f"Successfully seeded {len(points)} points into Qdrant Cloud!")