# 🏛️ Tata AI Legal Intelligence

**Enterprise Document Parsing, RAG Grounding & Risk Governance Portal** 

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System) 

An advanced, full-stack enterprise application designed for corporate legal and compliance teams.  This system automates the ingestion, parsing, and risk assessment of legal contracts, such as Master Service Agreements and NDAs, by utilizing AI and Retrieval-Augmented Generation (RAG).  It provides a secure, isolated workspace for officers to review AI-extracted clauses, log audit actions, and generate certified compliance reports. 

---

## 🏢 Executive Overview 

In large enterprise environments, evaluating operational and legal contracts requires meticulous, secure, and standardized review.  Relying on manual oversight can lead to inconsistencies and missed risk vectors.  

This platform provides: 
* **Grounded AI Synthesis:** Evaluates extracted clauses against enterprise policy via Vector DB grounding.  This ensures AI rationales are strictly tied to approved internal guidelines. 
* **Automated Risk Assessment:** Highlights risks (HIGH/MEDIUM/LOW) with generated AI rationales directly linked to extracted contract clauses. 
* **Strict RBAC & Governance:** Features a secure, human-in-the-loop workflow allowing officers to 'ACCEPT' or 'REJECT' documents.  This securely logs all decisions into an immutable audit trail. 
* **Certified Reporting:** Generates certified compliance reports and Executive Audit Packages dynamically. 

---

## ✨ Key Enterprise Capabilities 

* **🔒 Role-Based Multi-Tenant Access:** Secured via OAuth2 JWT Bearer tokens with strict data isolation across business units, such as Enterprise Legal, Procurement, Executive Office, and Compliance & Risk. 
* **📄 Multimodal Document Ingestion:** Features native parsing of PDFs (`pypdf`, PyMuPDF), Word documents (`python-docx`), and scanned images via Gemini Vision Multimodal OCR with automated page-level confidence scoring. 
* **🧠 LangGraph State Machine:** Executes deterministic workflows: OCR Extraction -> Clause Identification -> Vector RAG Retrieval -> Taxonomy Normalization -> Constrained Legal Reasoning. 
* **📚 Grounded RAG Policy Knowledge Base:** Cross-references contract text against `risk_taxonomy.csv` and corporate policies.  These are stored in an in-memory Qdrant Vector DB using 384-dimensional `all-MiniLM-L6-v2` dense embeddings. 
* **⚖️ Human-in-the-Loop Governance:** Enforces legal accountability through explicit review actions (`ACCEPT`, `REJECT`, `EDIT`, `ESCALATE`), logging every decision to an immutable PostgreSQL audit trail. 
* **📊 Executive PDF Reporting & Operations Telemetry:** Generates color-coded Executive Compliance Reports via ReportLab.  It visualizes throughput metrics, turnaround times, and high-risk distributions in real time. 
* **💬 Aadhya Legal AI Assistant:** A context-aware interactive assistant providing document Q&A, out-of-domain question deflection, and multi-turn conversational memory. 

---

## 🏗️ Enterprise System Architecture Blueprint 

### 1. Multi-Tier Layered System Topology 

The architecture is divided into distinct layers, from the React SPA frontend down to the PostgreSQL and Qdrant persistence engines, connected via a FastAPI REST Gateway. 

```text
╔═════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                    1. CLIENT PRESENTATION LAYER                                         ║
║  ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                               React 19 + TypeScript + Vite 8 SPA                                  │  ║
║  │  ┌───────────────────┐    ┌────────────────────┐    ┌──────────────────────┐    ┌──────────────┐  │  ║
║  │  │   AuthGate.tsx    │    │ DocumentWorkspace  │    │ DocumentHistorySide  │    │ ChatWidget   │  │  ║
║  │  │  (JWT Portal)     │    │ (RAG Matrix UI)    │    │  (Audit Sidebar)     │    │ (Aadhya AI)  │  │  ║
║  │  └─────────┬─────────┘    └─────────┬──────────┘    └──────────┬───────────┘    └──────┬───────┘  │  ║
║  └────────────┼────────────────────────┼──────────────────────────┼───────────────────────┼──────────┘  ║
╚═══════════════┼════════════════════════┼══════════════════════════┼═══════════════════════┼═════════════╝
                │                        │ HTTP REST (JSON)         │                       │
                └────────────────────────┴────────┬─────────────────┴───────────────────────┘
                                                  │ Bearer Token Authorization
══════════════════════════════════════════════════╪═════════════════════════════════════════════════════════
                                                  ▼
╔═════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                  2. API GATEWAY & SECURITY PERIMETER                                    ║
║  ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                               FastAPI REST Gateway (Uvicorn)                                      │  ║
║  │  ┌───────────────────┐    ┌────────────────────┐    ┌──────────────────────┐    ┌──────────────┐  │  ║
║  │  │ Auth & JWT Router │    │  Document Job API  │    │  Governance & Review │    │ Telemetry API│  │  ║
║  │  │ (/api/v1/auth)    │    │ (/api/v1/documents)│    │ (/api/v1/review)     │    │ (/monitoring)│  │  ║
║  │  └─────────┬─────────┘    └─────────┬──────────┘    └──────────┬───────────┘    └──────────────┘  │  ║
║  └────────────┼────────────────────────┼──────────────────────────┼──────────────────────────────────┘  ║
╚═══════════════┼════════════════════════┼══════════════════════════┼═════════════════════════════════════╝
                │                        │                          │
                ▼                        ▼                          ▼
╔═══════════════════════════╗  ╔═══════════════════════════╗  ╔═══════════════════════════════════════════╗
║  3. PERSISTENCE ENGINE    ║  ║ 4. AI & RAG ORCHESTRATION ║  ║  5. VECTOR & KNOWLEDGE BASE CORE          ║
║  ┌─────────────────────┐  ║  ║ ┌───────────────────────┐ ║  ║ ┌───────────────────────────────────────┐ ║
║  │  PostgreSQL 15 DB   │  ║  ║ │  LangGraph Engine     │ ║  ║ │ In-Memory Qdrant Vector Store         │ ║
║  │ ┌─────────────────┐ │  ║  ║ │ ┌───────────────────┐ │ ║  ║ │ ┌───────────────────────────────────┐ │ ║
║  │ │ UserModel       │ │  ║  ║ │ │ RAG Retrieval     │ │ ║  ║ │ │ 384-Dim Dense Embeddings           │ │ ║
║  │ │ DocumentModel   │ │  ║  ║ │ └─────────┬─────────┘ │ ║  ║ │ │ (SentenceTransformer MiniLM)      │ │ ║
║  │ │ ClauseModel     │ │  ║  ║ │ ┌─────────▼─────────┐ │ ║  ║ │ └─────────────────┬─────────────────┘ │ ║
║  │ │ AuditLogModel   │ │  ║  ║ │ │ Gemini Extraction │ │ ║  ║ │ ┌─────────────────▼─────────────────┐ │ ║
║  │ └─────────────────┘ │  ║  ║ │ └─────────┬─────────┘ │ ║  ║ │ │ Risk Taxonomy & Policies          │ │ ║
║  └─────────────────────┘  ║  ║ │ ┌─────────▼─────────┐ │ ║  ║ │ │ (risk_taxonomy.csv / KB .txt)     │ │ ║
║                           ║  ║ │ │ Normalization     │ │ ║  ║ │ └───────────────────────────────────┘ │ ║
║  ┌─────────────────────┐  ║  ║ │ └─────────┬─────────┘ │ ║  └───────────────────────────────────────┘ ║
║  │ Audit Log Storage   │  ║  ║ │ ┌─────────▼─────────┐ │ ║                                              ║
║  │ (audit_logs.json)   │  ║  ║ │ │ Legal Reasoning   │ │ ║  ╔═══════════════════════════════════════════╗
║  └─────────────────────┘  ║  ║ │ └───────────────────┘ │ ║  ║  6. OBSERVABILITY & TRACING LAYER        ║
║                           ║  ║ └───────────────────────┘ ║  ║ ┌───────────────────────────────────────┐ ║
║  ┌─────────────────────┐  ║  ║                           ║  ║ │ LangSmith Tracing & Evaluator        │ ║
║  │ PDF Report Generator│  ║  ║ ┌───────────────────────┐ ║  ║ │ (Tata_Legal_Contract_Benchmark_v1)  │ ║
║  │ (ReportLab Engine)  │  ║  ║ │ Local Heuristic       │ ║  ║ └───────────────────────────────────────┘ ║
║  └─────────────────────┘  ║  ║ │ Fallback Evaluator    │ ║  ╚═══════════════════════════════════════════╝
╚═══════════════════════════╝  ║ └───────────────────────┘ ║
                               ╚═══════════════════════════╝

```

### 2. End-to-End Processing & Dataflow Architecture



The workflow handles everything from user browser uploads through the FastAPI gateway to the LangGraph orchestration and final PostgreSQL persistence.

```text
[User Browser]
      │
      │ 1. Upload Contract (File + Metadata)
      ▼
┌─────────────────────────┐
│ FastAPI Gateway         │
│ (/documents/upload)     │
└────────────┬────────────┘
             │
             │ 2. Extract Raw Text & Page Metrics
             ▼
┌─────────────────────────┐      ┌──────────────────────────┐
│ OCR & Parsing Engine    ├─────►│ PyMuPDF / python-docx    │
│ (ocr_service.py)        │      │ Gemini Vision AI (Scans) │
└────────────┬────────────┘      └──────────────────────────┘
             │
             │ 3. Dispatch Initial State to LangGraph Workflow
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LANGGRAPH ORCHESTRATION GRAPH                      │
│                                                                         │
│   ┌────────────────────────┐         ┌──────────────────────────────┐   │
│   │ retrieve_rag Node      ├────────►│ Qdrant Vector Search         │   │
│   │ (Vector Policy Query)  │         │ (SentenceTransformers MiniLM)│   │
│   └──────────┬─────────────┘         └──────────────────────────────┘   │
│              │                                                          │
│              ▼                                                          │
│   ┌────────────────────────┐         ┌──────────────────────────────┐   │
│   │ extract_clauses Node   ├────────►│ Gemini Cascade               │   │
│   │ (Summary & Clauses)    │         │ (3.5 / 2.5 / 2.0 Flash)      │   │
│   └──────────┬─────────────┘         └──────────────┬───────────────┘   │
│              │                                      │ (Quota Error)     │
│              │                                      ▼                   │
│              │                       ┌──────────────────────────────┐   │
│              │                       │ Local Heuristic Fallback     │   │
│              │                       │ (Keyword Risk Scanner)       │   │
│              │                       └──────────────┬───────────────┘   │
│              ▼                                      │                   │
│   ┌────────────────────────┐                        │                   │
│   │ normalize_clauses Node ◄────────────────────────┘                   │
│   │ (Taxonomy Standardizer)│                                            │
│   └──────────┬─────────────┘                                            │
│              │                                                          │
│              ▼                                                          │
│   ┌────────────────────────┐                                            │
│   │ legal_reasoning Node   │                                            │
│   │ (Risk Scoring Pass)    │                                            │
│   └──────────┬─────────────┘                                            │
└──────────────┼──────────────────────────────────────────────────────────┘
               │
               │ 4. Persist Results & Structured Metadata
               ▼
┌─────────────────────────┐      ┌──────────────────────────┐
│ PostgreSQL Storage      ├─────►│ DocumentModel            │
│ (database.py)           │      │ ClauseModel              │
└────────────┬────────────┘      └──────────────────────────┘
             │
             │ 5. Render Extracted Clauses & Risk Matrix
             ▼
┌─────────────────────────┐
│ DocumentWorkspace.tsx   │
│ (React Interface)       │
└────────────┬────────────┘
             │
             │ 6. Counsel Review Action (ACCEPT / REJECT / ESCALATE)
             ▼
┌─────────────────────────┐      ┌──────────────────────────┐
│ Governance Service      ├─────►│ AuditLogModel (DB)       │
│ (/review/actions)       │      │ audit_logs.json          │
└─────────────────────────┘      │ ReportLab PDF Generator  │
                                 └──────────────────────────┘

```

### 3. Multi-Tenant Data Security & Isolation Model



Data privacy and multi-tenancy are enforced at the database level using `business_unit` and user role scoping via JWT authentication.

```text
               ┌───────────────────────────────────────────┐
               │         Authenticated Request             │
               │   (JWT Token: email, role, BU)            │
               └─────────────────────┬─────────────────────┘
                                     │
                                     ▼
               ┌───────────────────────────────────────────┐
               │        FastAPI Security Dependency        │
               │        (get_current_user in auth.py)      │
               └─────────────────────┬─────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
     Is Admin User? │ YES                             │ No (Standard User)
                    ▼                                 ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│          Unrestricted Access          │ │      Strict Data Scoping Query        │
│ SELECT * FROM documents;              │ │ SELECT * FROM documents               │
│ SELECT * FROM audit_logs;             │ │ WHERE uploaded_by = :user_email       │
└───────────────────────────────────────┘ │   AND business_unit = :user_bu;       │
                                          └───────────────────────────────────────┘

```

---

## 🧠 AI Engineering & Resiliency Architecture



### Triple-Tier Resiliency & Fallback Engine



To guarantee 99.8%+ system availability without breaking API contracts during rate-limit spikes or cloud service degradation:

* **Tier 1 (LLM Model Cascade):** Sequentially attempts extraction across candidate models: `gemini-3.5-flash` -> `gemini-2.5-flash` -> `gemini-2.0-flash` -> `gemini-1.5-pro`.


* **Tier 2 (Local Heuristic Fallback):** If all cloud models fail, `_dynamic_fallback_evaluation()` executes a deterministic keyword scan checking for high-risk legal terms to produce structured clause evaluation outputs locally.


* **Tier 3 (Out-of-Domain Chat Guardrail):** The conversational assistant "Aadhya" inspects user queries for non-legal topics and politely deflects them to preserve persona boundaries.



### Vector Database & Semantic Chunking



* **Embedding Model:** `all-MiniLM-L6-v2` generating 384-dimensional dense vectors.


* **Chunking Strategy:** Knowledge base `.txt` policy files are split using LangChain's `RecursiveCharacterTextSplitter` (`chunk_size=1000`, `chunk_overlap=150`).


* **Storage Engine:** Qdrant in-memory vector store configured with Cosine distance metric.



---

## 🗄️ Database Schema & Relational Design



The system uses PostgreSQL with SQLAlchemy ORM models enforcing strict relational integrity and user isolation:

```text
┌─────────────────┐       1:N       ┌──────────────────┐
│    UserModel    │────────────────>│  DocumentModel   │
│  (email, role)  │                 │  (job_id, bu)    │
└────────┬────────┘                 └────────┬─────────┘
         │                                   │
      1:N│                                1:N│
         ▼                                   ▼
┌─────────────────┐                 ┌──────────────────┐
│  SessionModel   │                 │   ClauseModel    │
│  (JWT Tokens)   │                 │ (risk, text, FK) │
└─────────────────┘                 └────────┬─────────┘
         │                                   │
         └──────────────┐     ┌──────────────┘
                        ▼     ▼
              ┌──────────────────┐
              │  AuditLogModel   │
              │ (action, notes)  │
              └──────────────────┘

```

---

## 📚 Knowledge Base Assets



To prevent AI hallucination, the system's `rag_service.py` strictly grounds generated rationales against predefined enterprise policy text files stored in `backend/data/knowledge_base/`:

* `approved_clause_library.txt` — Standard templates and acceptable fallbacks for MSAs.


* `compliance_guidelines.txt` — Regulatory standards and mandatory compliance checks.


* `confidentiality_policy.txt` — Strict rules regarding NDA scope and data handling.


* `jurisdiction_guidelines.txt` — Approved governing laws and venue stipulations.


* `liability_cap_policy.txt` — Financial exposure limits and indemnification thresholds.



---

## 🚀 Quick Start Deployment Guide



### Option A: Docker Compose Cluster (Recommended)



1. **Clone the repository and prepare `.env` file:**

```bash
cp .env.example .env

```


*Fill in your `GEMINI_API_KEY`, `SECRET_KEY`, and optional `LANGCHAIN_API_KEY`.*

2. **Launch the multi-container cluster:**

```bash
docker-compose up -d --build

```


3. **Verify running services:**

* **Frontend Application:** `http://localhost:5173`

* **Backend API Swagger Documentation:** `http://localhost:8000/docs`

* **PostgreSQL Database:** `localhost:5432`




### Option B: Local Development Setup (Manual)



#### 1. Backend Setup



```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy English NLP model
python -m spacy download en_core_web_sm

# Start FastAPI server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

```

#### 2. Frontend Setup



```bash
cd frontend

# Install Node modules
npm install

# Start Vite development server
npm run dev

```

---

## ☁️ Render Deployment



The project includes a repository-level `render.yaml` Blueprint configuration for Render deployment. This file should be treated as the deployment configuration source for the services defined in the repository.

1. Push the project to GitHub with `render.yaml` present at the repository root.


2. In Render, create a new **Blueprint** and select the GitHub repository.


3. Render reads the repository's `render.yaml` and provisions the services declared by the Blueprint.


4. Configure any environment values/secrets that are intentionally supplied by Render rather than committed to source control.


5. After deployment, verify the deployed frontend/backend endpoints and confirm the application can communicate with its configured database and AI/RAG services.



---

## 🧪 Testing, Guardrails & Evaluation Suite



* **LangSmith Benchmark Evaluator:** Evaluates clause extraction precision and policy grounding against a ground-truth benchmark dataset using `evaluate_pipeline.py`.


* **Pytest Unit & Integration Test Suite:** Executes unit tests covering OCR confidence limits, clause normalization, fallback heuristics, and out-of-domain chat guardrails by running `pytest`.



---

## 🔒 Security, Data Governance & Compliance



* **Token Protection:** Passwords are hashed using `bcrypt`. Authentication uses HS256-signed JWT tokens.


* **Data Isolation:** User sessions and document histories are strictly isolated by `business_unit` and user identity.


* **Non-Retention Policy:** Sensitive contract text is never sent to third-party services for training. All external LLM calls are bound by enterprise confidentiality standards.


* **Audit Logging:** Every human review decision is recorded with timestamps, user emails, comments, and action types in `AuditLogModel` and `audit_logs.json`.


* **Immutable Auditing:** The `governance_service.py` explicitly blocks soft-deletions of human-in-the-loop decisions, creating a permanent paper trail of who approved which clause.



---

## 🎬 Demonstration Scenarios



1. **Vendor NDA Review:** Upload a standard NDA file. The system identifies missing indemnification clauses, verifies confidentiality survival periods, and generates an executive brief.


2. **Unlimited Liability Escalation:** Upload a supplier agreement containing unlimited liability wording. The system flags `HIGH` risk against policy, provides an AI rationale, and enables senior counsel to escalate the file.


3. **Out-of-Domain Conversational Deflection:** Ask Aadhya "What is the weather in Mumbai?". The assistant politely declines and redirects focus to corporate contract compliance.
