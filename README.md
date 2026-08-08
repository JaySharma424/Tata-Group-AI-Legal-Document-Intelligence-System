# 🏛️ Tata AI Legal Intelligence System

![Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![Architecture](https://img.shields.io/badge/Architecture-Full--Stack%20%7C%20Microservices-purple)
![AI Engine](https://img.shields.io/badge/AI%20Engine-LangGraph%20%7C%20Gemini-orange)
![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20Qdrant-green)
![License](https://img.shields.io/badge/License-Proprietary%20Enterprise-red)

---

## 📖 Executive Summary

The **Tata AI Legal Intelligence System** is an enterprise-grade, governed AI document-intelligence platform engineered for corporate legal, risk, and compliance departments across the Tata Group. It accelerates first-pass contract reviews, vendor onboarding, policy verification, and regulatory assessments by converting complex, unstructured legal agreements into structured **Contract Summaries & Risk Flags**.

The system automates labor-intensive extraction and risk analysis while strictly preserving **human legal authority, auditability, multi-tenant isolation, and escalation controls**. Every AI recommendation is grounded in document evidence and validated against approved corporate policies.

---

## 📋 Table of Contents

- [🏛️ Tata AI Legal Intelligence System](#️-tata-ai-legal-intelligence-system)
  - [📖 Executive Summary](#-executive-summary)
  - [✨ Key Enterprise Capabilities](#-key-enterprise-capabilities)
  - [🏗️ Enterprise System Architecture Blueprint](#️-enterprise-system-architecture-blueprint)
    - [1. Multi-Tier Layered System Topology](#1-multi-tier-layered-system-topology)
    - [2. End-to-End Processing \& Dataflow Architecture](#2-end-to-end-processing--dataflow-architecture)
    - [3. LangGraph AI Agent State Machine Topology](#3-langgraph-ai-agent-state-machine-topology)
    - [4. Multi-Tenant Data Security \& Isolation Model](#4-multi-tenant-data-security--isolation-model)
    - [5. Architectural Component \& Design Pattern Matrix](#5-architectural-component--design-pattern-matrix)
  - [🧠 AI Engineering \& Resiliency Architecture](#-ai-engineering--resiliency-architecture)
    - [Triple-Tier Resiliency \& Fallback Engine](#triple-tier-resiliency--fallback-engine)
    - [Vector Database \& Semantic Chunking](#vector-database--semantic-chunking)
  - [🗄️ Database Schema \& Relational Design](#️-database-schema--relational-design)
  - [🌐 Complete REST API Reference](#-complete-rest-api-reference)
  - [🚀 Quick Start Deployment Guide](#-quick-start-deployment-guide)
    - [Option A: Docker Compose Cluster (Recommended)](#option-a-docker-compose-cluster-recommended)
    - [Option B: Local Development Setup (Manual)](#option-b-local-development-setup-manual)
  - [⚙️ Environment Variables Reference](#️-environment-variables-reference)
  - [🧪 Testing, Guardrails \& Evaluation Suite](#-testing-guardrails--evaluation-suite)
    - [1. LangSmith Benchmark Evaluator](#1-langsmith-benchmark-evaluator)
    - [2. Pytest Unit \& Integration Test Suite](#2-pytest-unit--integration-test-suite)
  - [🔒 Security, Data Governance \& Compliance](#-security-data-governance--compliance)
  - [🎬 Demonstration Scenarios](#-demonstration-scenarios)
  - [📂 Comprehensive Project Directory Structure](#-comprehensive-project-directory-structure)
  - [❓ Troubleshooting \& FAQ](#-troubleshooting--faq)

---

## ✨ Key Enterprise Capabilities

* **🔒 Role-Based Multi-Tenant Access:** Secured via OAuth2 JWT Bearer tokens with strict data isolation across business units (e.g., Enterprise Legal, Procurement, Executive Office, Compliance & Risk).
* **📄 Multimodal Document Ingestion:** Native parsing of PDFs (`pypdf`, PyMuPDF), Word documents (`python-docx`), and scanned images via Gemini Vision Multimodal OCR with automated page-level confidence scoring.
* **🧠 LangGraph State Machine:** Deterministic workflow execution: OCR Extraction $\rightarrow$ Clause Identification $\rightarrow$ Vector RAG Retrieval $\rightarrow$ Taxonomy Normalization $\rightarrow$ Constrained Legal Reasoning.
* **📚 Grounded RAG Policy Knowledge Base:** Cross-references contract text against `risk_taxonomy.csv` and corporate policies stored in an in-memory **Qdrant** Vector DB using 384-dimensional `all-MiniLM-L6-v2` dense embeddings.
* **⚖️ Human-in-the-Loop Governance:** Enforces legal accountability through explicit review actions (`ACCEPT`, `REJECT`, `EDIT`, `ESCALATE`), logging every decision to an immutable PostgreSQL audit trail.
* **📊 Executive PDF Reporting & Operations Telemetry:** Generates color-coded Executive Compliance Reports via ReportLab and visualizes throughput metrics, turnaround times, and high-risk distributions in real time.
* **💬 Aadhya Legal AI Assistant:** Context-aware interactive assistant providing document Q&A, out-of-domain question deflection, and multi-turn conversational memory.

---

## 🏗️ Enterprise System Architecture Blueprint

### 1. Multi-Tier Layered System Topology

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

---

### 2. End-to-End Processing & Dataflow Architecture

The diagram below illustrates the exact control flow and lifecycle of an uploaded legal document from intake to human sign-off:

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

---

### 3. LangGraph AI Agent State Machine Topology

The AI pipeline is structured as a deterministic state machine managed by `langgraph.graph.StateGraph`:

```text
                  ┌──────────────────────────────┐
                  │          [START]             │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │    retrieve_rag_context      │
                  │ - Embed OCR text via MiniLM  │
                  │ - Search Qdrant Vector Store │
                  │ - Retrieve relevant policies │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │       extract_clauses        │
                  │ - Execute Gemini LLM prompt  │
                  │ - Output JSON clause schema  │
                  │ - [Fallback] Local Heuristic │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      normalize_clauses       │
                  │ - Map raw headers to standard│
                  │   corporate taxonomy schema  │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │       legal_reasoning        │
                  │ - 2nd-pass risk scoring      │
                  │ - Assign HIGH/MEDIUM/LOW     │
                  │ - Attach policy citations    │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │           [END]              │
                  └──────────────────────────────┘
```

---

### 4. Multi-Tenant Data Security & Isolation Model

Data privacy and multi-tenancy are enforced at the database level using `business_unit` and user role scoping:

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

### 5. Architectural Component & Design Pattern Matrix

| Architecture Layer | Core Software Module | Key Design Patterns Used | System Responsibility |
| :--- | :--- | :--- | :--- |
| **Presentation Layer** | `AuthGate.tsx`<br>`DocumentWorkspace.tsx` | Component-Based Architecture, Custom Hooks, Global Interceptor Pattern | Provides glassmorphic user surfaces, handles file uploads, renders risk matrix, manages JWT auth storage. |
| **API Gateway Layer** | `main.py`<br>`router.py` | Gateway Pattern, Dependency Injection, Router Aggregation | Exposes RESTful OpenAPI endpoints, manages CORS policies, validates Pydantic schemas, handles global exceptions. |
| **AI Processing Layer** | `legal_graph.py`<br>`clause_service.py` | State Machine Pattern (LangGraph), Fallback / Circuit Breaker Pattern | Orchestrates end-to-end document extraction, handles model cascading, provides heuristic fallback during LLM quota failures. |
| **RAG & Vector Core** | `rag_service.py` | Retrieval-Augmented Generation (RAG), Dense Embedding Vector Search | Generates 384-dim text vectors, splits documents using `RecursiveCharacterTextSplitter`, queries Qdrant DB. |
| **Parsing Engine** | `ocr_service.py`<br>`parsing_service.py` | Strategy Pattern (Multi-Format Extraction) | Extracts text from PDF, DOCX, and Scanned Images (Vision AI), calculates page counts (PyMuPDF) and spaCy NLP entities. |
| **Persistence Layer** | `database.py`<br>`models.py` | Object-Relational Mapping (ORM), Repository Pattern | Manages PostgreSQL database connections, enforces foreign key constraints, preserves relational user/document data. |
| **Governance Engine** | `review.py`<br>`governance_service.py` | Command Pattern, Audit Trail Pattern | Captures human review sign-offs (`ACCEPT`, `REJECT`, `ESCALATE`), updates database state, logs JSON audit trails. |
| **Reporting Layer** | `report_service.py` | Template Method Pattern, Builder Pattern | Dynamically compiles structured document metadata, color-coded risk matrices, and audit logs into downloadable PDF files. |

---

## 🧠 AI Engineering & Resiliency Architecture

### Triple-Tier Resiliency & Fallback Engine

To guarantee 99.8%+ system availability without breaking API contracts during rate-limit spikes or cloud service degradation:

* **Tier 1 (LLM Model Cascade):** Sequentially attempts extraction across candidate models: `gemini-3.5-flash` $\rightarrow$ `gemini-2.5-flash` $\rightarrow$ `gemini-2.0-flash` $\rightarrow$ `gemini-1.5-pro`.
* **Tier 2 (Local Heuristic Fallback):** If all cloud models fail, `_dynamic_fallback_evaluation()` executes a deterministic keyword scan checking for high-risk legal terms (`indemn`, `liability`, `penalty`, `termination`) to produce structured clause evaluation outputs locally.
* **Tier 3 (Out-of-Domain Chat Guardrail):** The conversational assistant "Aadhya" inspects user queries for non-legal topics (weather, sports, general knowledge) and politely deflects them to preserve persona boundaries.

### Vector Database & Semantic Chunking

* **Embedding Model:** `all-MiniLM-L6-v2` generating 384-dimensional dense vectors.
* **Chunking Strategy:** Knowledge base `.txt` policy files are split using LangChain's `RecursiveCharacterTextSplitter` (`chunk_size=1000`, `chunk_overlap=150`).
* **Storage Engine:** Qdrant in-memory vector store configured with Cosine distance metric.

---

## 🗄️ Database Schema & Relational Design

The system uses **PostgreSQL** with SQLAlchemy ORM models enforcing strict relational integrity and user isolation:

```
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

## 🌐 Complete REST API Reference

| Endpoint | Method | Tag | Description |
| :--- | :---: | :--- | :--- |
| `/api/v1/auth/register` | `POST` | Authentication | Register a new user with role and business unit |
| `/api/v1/auth/login` | `POST` | Authentication | Authenticate user and return Bearer JWT token |
| `/api/v1/auth/profile` | `PUT` | Authentication | Update user profile and password in database |
| `/api/v1/documents/upload` | `POST` | Documents | Upload contract file and trigger processing pipeline |
| `/api/v1/documents/history` | `GET` | Documents | Get processed document history for active user |
| `/api/v1/documents/{document_id}` | `GET` | Documents | Retrieve document details and extracted clauses |
| `/api/v1/documents/{job_id}/export-pdf` | `GET` | Documents | Generate and download certified PDF compliance report |
| `/api/v1/chat/query` | `POST` | Chat | Query Aadhya Legal AI Assistant with active context |
| `/api/v1/review/actions` | `POST` | Governance | Record reviewer sign-off (`ACCEPT`, `REJECT`, `EDIT`) |
| `/api/v1/review/history` | `GET` | Governance | Get audit sign-off history isolated by user session |
| `/api/v1/review/{job_id}/audit-trail` | `GET` | Governance | Retrieve full audit trail for a specific contract job |
| `/api/v1/risk/console/high-risk` | `GET` | Risk Review | Fetch high-risk clauses scoped by business unit |
| `/api/v1/risk/{job_id}/clause-intelligence` | `GET` | Risk Review | Get deep clause metrics and risk rationales |
| `/api/v1/monitoring/telemetry` | `GET` | Monitoring | Get system-wide operational metrics and risk counts |
| `/api/v1/kb/policies` | `GET` | Knowledge Base | Fetch active policies and risk taxonomy library |

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
   * **Frontend Application:** [http://localhost:5173](http://localhost:5173)
   * **Backend API Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
   * **PostgreSQL Database:** `localhost:5432`

---

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

## ⚙️ Environment Variables Reference

| Variable Name | Required | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | Yes | `postgresql://postgres:1234@localhost:5432/tata_legal_db` | PostgreSQL connection string |
| `SECRET_KEY` | Yes | `tata_enterprise_secure_secret_key_2026` | 32+ character key for JWT encoding |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | JWT token validity duration |
| `GEMINI_API_KEY` | Yes | `—` | Google Gemini Generative AI API key |
| `LANGCHAIN_TRACING_V2` | No | `"true"` | Enables LangSmith observability tracing |
| `LANGCHAIN_API_KEY` | No | `—` | LangSmith API key for evaluations |
| `LANGCHAIN_PROJECT` | No | `"tata-ai-legal-intelligence"` | Project name in LangSmith dashboard |
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Backend API base URL for frontend Axios |

---

## 🧪 Testing, Guardrails & Evaluation Suite

### 1. LangSmith Benchmark Evaluator
Evaluates clause extraction precision and policy grounding against a ground-truth benchmark dataset (`Tata_Legal_Contract_Benchmark_v1`):

```bash
python evaluate_pipeline.py
```
* **Metrics Computed:** `risk_accuracy_score` (Target $\ge 0.90$) and `rag_policy_citation_score` (Target $\ge 0.95$).

### 2. Pytest Unit & Integration Test Suite
Executes unit tests covering OCR confidence limits, clause normalization, fallback heuristics, and out-of-domain chat guardrails:

```bash
pytest
```

---

## 🔒 Security, Data Governance & Compliance

* **Token Protection:** Passwords are hashed using `bcrypt` (pinned to stable v4.0.1). Authentication uses HS256-signed JWT tokens.
* **Data Isolation:** User sessions and document histories are strictly isolated by `business_unit` and user identity.
* **Non-Retention Policy:** Sensitive contract text is never sent to third-party services for training; all external LLM calls are bound by enterprise confidentiality standards.
* **Audit Logging:** Every human review decision is recorded with timestamps, user emails, comments, and action types in `AuditLogModel` and `audit_logs.json`.

---

## 🎬 Demonstration Scenarios

1. **Vendor NDA Review:** Upload a standard NDA file. The system identifies missing indemnification clauses, verifies confidentiality survival periods against `CLS-NDA-003`, and generates an executive brief.
2. **Unlimited Liability Escalation:** Upload a supplier agreement containing unlimited liability wording. The system flags `HIGH` risk against policy `RISK-CAP-99`, provides an AI rationale, and enables senior counsel to escalate the file.
3. **Out-of-Domain Conversational Deflection:** Ask Aadhya "What is the weather in Mumbai?" or "Who won the cricket match?". The assistant politely declines and redirects focus to corporate contract compliance.

---

## 📂 Comprehensive Project Directory Structure

```text
tata-ai-legal-intelligence-system/
├── backend/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py             # JWT Register, Login & User Auth
│   │       ├── chat.py             # Aadhya Legal AI Chat Assistant Endpoint
│   │       ├── documents.py        # File Upload, Retrieval & PDF Export
│   │       ├── governance.py       # Review Sign-Off & Audit Logging
│   │       ├── knowledge_base.py   # Corporate Policy Library Routes
│   │       ├── monitoring.py       # Legal Operations Telemetry
│   │       ├── review.py           # Multi-tenant Review & History API
│   │       ├── risk_review.py      # High-Risk Clause Console
│   │       └── router.py           # Unified Router Assembly
│   ├── data/
│   │   ├── knowledge_base/         # Policy text documents (.txt)
│   │   └── risk_taxonomy.csv       # Standard risk rules & trigger keywords
│   ├── document_pipeline/
│   │   ├── clause_extraction/
│   │   │   └── reasoning_service.py # 2nd-pass Legal Reasoning Engine
│   │   ├── normalization/
│   │   │   └── normalization_service.py # Taxonomy Header Normalizer
│   │   ├── ocr/
│   │   │   └── ocr_service.py      # Multimodal OCR & Metrics Engine
│   │   ├── parsing/
│   │   │   └── parsing_service.py  # PyMuPDF Page counter & spaCy NLP
│   │   ├── reporting/
│   │   │   └── report_service.py   # ReportLab PDF Report Generator
│   │   ├── summary_service.py      # Executive Brief Synthesizer
│   │   ├── legal_graph.py          # LangGraph State Graph Orchestrator
│   │   └── clause_service.py       # Clause Service & Local Fallback
│   ├── services/
│   │   ├── governance_service.py   # Audit Log File Logger
│   │   └── rag_service.py          # Qdrant Vector Search & MiniLM Embeddings
│   ├── storage/                    # Uploads, Reports & Audit JSON Logs
│   ├── database.py                 # SQLAlchemy Session & Engine Config
│   ├── models.py                   # PostgreSQL Relational ORM Schemas
│   └── main.py                     # FastAPI Application Gateway
├── frontend/
│   ├── src/
│   │   ├── component/
│   │   │   ├── AuthGate.tsx               # Login & Registration Portal
│   │   │   ├── DocumentHistorySidebar.tsx # Real-Time Audit Archive Sidebar
│   │   │   ├── DocumentWorkspace.tsx      # Central Upload & RAG Matrix UI
│   │   │   ├── LegalChatWidget.tsx        # Floating Aadhya Assistant
│   │   │   └── LegalOpsDashboard.tsx      # Governance Telemetry Dashboard
│   │   ├── App.tsx                        # Root Layout & Axios Interceptors
│   │   ├── main.tsx                       # React 19 Entrypoint
│   │   └── index.css                      # Tailwind CSS v4 Global Styles
│   ├── Dockerfile                         # Node 20 Builder & Nginx Server
│   └── package.json                       # Frontend Dependencies
├── tests/
│   ├── test_api_endpoints.py       # Review & History Integration Tests
│   ├── test_chat_and_rag.py        # Vector Retrieval & Chat Guardrail Tests
│   ├── test_error_handling.py      # API Boundary & Exception Tests
│   └── test_ocr_and_parsing.py     # OCR Score & Normalization Tests
├── evaluate_pipeline.py            # LangSmith Ground-Truth Evaluator
├── docker-compose.yml              # Multi-Container Deployment Specification
├── Dockerfile.backend              # Python 3.12 Backend Linux Image
├── requirements.txt                # Python Backend Package Dependencies
├── .env.example                    # Environment Template Configuration
└── README.md                       # Comprehensive Technical Documentation
```

---

## ❓ Troubleshooting & FAQ

#### Q1: OCR Extraction returns lower confidence scores for scanned PDFs.
* **Resolution:** Ensure `tesseract-ocr` is installed on the host system or system container. On Windows, verify `TESSERACT_CMD_PATH` in `.env` points to `C:\Program Files\Tesseract-OCR\tesseract.exe`.

#### Q2: FastAPI returns a 500 error connecting to PostgreSQL.
* **Resolution:** Verify your PostgreSQL service is running and that `DATABASE_URL` in `.env` matches your credentials. When running inside Docker, ensure the database host points to `db` instead of `localhost`.

#### Q3: Gemini API rate limit or quota exceeded error appears in backend logs.
* **Resolution:** The system automatically executes `_dynamic_fallback_evaluation()` to compute clause risk levels locally without breaking frontend workflows. You can also add secondary model keys or upgrade API quotas.

---

*Approved for Enterprise Internal Review and Staging Deployment.*
