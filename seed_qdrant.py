import os, glob, re, csv, uuid, time
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from backend.database import SessionLocal, Base, engine
from backend.models import KnowledgeBaseModel

Base.metadata.create_all(bind=engine)
db = SessionLocal()

qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")
google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not google_key:
    raise ValueError("GEMINI_API_KEY environment variable is missing.")
if not qdrant_url or not qdrant_api_key:
    raise ValueError("QDRANT_URL or QDRANT_API_KEY environment variable is missing.")

if not qdrant_url.startswith("http"):
    qdrant_url = f"https://{qdrant_url}"

client = genai.Client(api_key=google_key)
qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=60)

col_name = "tata_legal_knowledge_v4"
collections = [c.name for c in qdrant.get_collections().collections]
if col_name not in collections:
    qdrant.create_collection(
        collection_name=col_name,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
    print(f"Created Qdrant collection: {col_name}")

parsed = []

# 1. Parse CSV
csv_path = "data/risk_taxonomy.csv" if os.path.exists("data/risk_taxonomy.csv") else "backend/data/risk_taxonomy.csv"
if os.path.exists(csv_path):
    with open(csv_path, "r", encoding="utf-8") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            ref = row.get("reference_id") or f"TAX-{idx+1}"
            text = f"Clause Type: {row.get('clause_type')}. Reference ID: {ref}. Mandatory Policy: {row.get('policy_text')}. Guidelines: {row.get('handling_guidelines')}"
            parsed.append({
                "ref": ref,
                "title": f"{row.get('clause_type')} Policy",
                "category": row.get("clause_type", "General"),
                "guidance": row.get("policy_text", ""),
                "source": "risk_taxonomy.csv",
                "text": text
            })

# 2. Parse TXT files
search_dirs = ["backend/data/knowledge_base/*.txt", "backend/data/*.txt", "data/*.txt", "*.txt"]
txt_files = []
for pattern in search_dirs:
    for fpath in glob.glob(pattern):
        base = os.path.basename(fpath)
        if base not in ["requirements.txt", "new 1.txt"] and fpath not in txt_files:
            txt_files.append(fpath)

for fpath in txt_files:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    for block in re.split(r'\n\s*\n(?=TITLE:)|(?<=\n)(?=TITLE:)', content.strip()):
        if not block.strip().startswith("TITLE:"):
            continue
        item = {}
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("TITLE:"): item["title"] = line[6:].strip()
            elif line.startswith("CATEGORY:"): item["category"] = line[9:].strip()
            elif line.startswith("REFERENCE_ID:"): item["ref"] = line[13:].strip()
            elif line.startswith("GUIDANCE:"): item["guidance"] = line[9:].strip()
        if item.get("ref"):
            search_text = f"Policy Title: {item.get('title')}. Category: {item.get('category')}. Reference ID: {item.get('ref')}. Guidance Rule: {item.get('guidance')}"
            parsed.append({
                "ref": item["ref"],
                "title": item.get("title", ""),
                "category": item.get("category", "General Provision"),
                "guidance": item.get("guidance", ""),
                "source": os.path.basename(fpath),
                "text": search_text
            })

print(f"Found {len(parsed)} policies. Starting rate-safe embedding...")

def get_embedding_safe(text: str, max_retries: int = 5) -> list:
    for attempt in range(max_retries):
        try:
            resp = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text[:2000]
            )
            return list(resp.embeddings[0].values)
        except ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_sec = 45
                print(f"[Rate Limit] 429 hit at attempt {attempt+1}. Pausing for {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                raise e
        except Exception as e:
            print(f"[Warn] Embedding error ({e}), retrying in 5s...")
            time.sleep(5)
    return [0.0] * 768

points_batch = []
total_seeded = 0

for i, entry in enumerate(parsed):
    det_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"tata_kb_{entry['ref']}"))
    
    # Check and insert into Postgres
    if not db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == det_uuid).first():
        db.add(KnowledgeBaseModel(
            id=det_uuid,
            reference_id=entry["ref"],
            title=entry["title"],
            category=entry["category"],
            guidance=entry["guidance"],
            source_file=entry["source"],
            search_text=entry["text"]
        ))
        db.commit()

    emb = get_embedding_safe(entry["text"])
    points_batch.append(PointStruct(
        id=det_uuid,
        vector=emb,
        payload={
            "uuid": det_uuid,
            "ref": entry["ref"],
            "title": entry["title"],
            "category": entry["category"],
            "clause_type": entry["category"],
            "guidance": entry["guidance"],
            "policy_text": entry["guidance"],
            "source": entry["source"],
            "text": entry["text"]
        }
    ))

    # Safe pace: 0.65s delay prevents exceeding 100 requests per minute
    time.sleep(0.65)

    if (i + 1) % 10 == 0 or (i + 1) == len(parsed):
        print(f"Processed {i + 1}/{len(parsed)} policies...")

    # Upsert every 25 records to keep progress
    if len(points_batch) >= 25:
        qdrant.upsert(collection_name=col_name, points=points_batch)
        total_seeded += len(points_batch)
        points_batch = []

if points_batch:
    qdrant.upsert(collection_name=col_name, points=points_batch)
    total_seeded += len(points_batch)

db.close()
print(f"Successfully seeded all {total_seeded} policy vectors into Qdrant Cloud!")