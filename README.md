# 🏛️ Tata AI Legal Intelligence

**Enterprise Document Parsing, RAG Grounding & Risk Governance Portal**

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/TriptiVishwakarma/Tata-Group-AI-Legal-Document-Intelligence-System)
[![License: Enterprise](https://img.shields.io/badge/License-Enterprise-red.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-teal?logo=fastapi)]()
[![React](https://img.shields.io/badge/React-19-blue?logo=react)]()

---

## 🌟 Welcome to the Future of Legal Compliance
Welcome to the official repository for the **Tata AI Legal Intelligence System**—an advanced, full-stack enterprise application built from the ground up for corporate legal, procurement, and risk compliance teams. 

Navigating complex operational agreements (such as Master Service Agreements, Vendor Contracts, and NDAs) manually is slow and prone to oversight. This platform automates document ingestion, multi-modal OCR text extraction, structural clause taxonomy normalization, vector-based policy retrieval (Qdrant), LLM risk reasoning (LangGraph), and automated RAG performance scoring (RAGAS). It provides a secure, isolated workspace for officers to review AI-extracted clauses, log audit actions, and generate certified compliance reports.

---

## 📋 Interactive Table of Contents
* [✨ Key Enterprise Capabilities](#-key-enterprise-capabilities)
* [🏗️ Enterprise System Architecture Blueprint](#️-enterprise-system-architecture-blueprint)
* [🧠 AI Engineering & Resiliency Architecture](#-ai-engineering--resiliency-architecture)
* [📚 Knowledge Base Assets & Grounded RAG](#-knowledge-base-assets--grounded-rag)
* [🗄️ Database Schema & Relational Design](#️-database-schema--relational-design)
* [🌐 Complete REST API Reference](#-complete-rest-api-reference)
* [🚀 Quick Start Deployment Guide](#-quick-start-deployment-guide)
* [🧪 Testing, Guardrails & Evaluation Suite](#-testing-guardrails--evaluation-suite)
* [🔒 Security, Data Governance & Compliance](#-security-data-governance--compliance)
* [🎬 Demonstration Scenarios](#-demonstration-scenarios)
* [📂 Comprehensive Project Directory Structure](#-comprehensive-project-directory-structure)

---

## ✨ Key Enterprise Capabilities

* **🔒 Role-Based Multi-Tenant Access:** Secured via OAuth2 JWT Bearer tokens with strict data isolation across business units (e.g., Enterprise Legal, Procurement, Executive Office, Compliance & Risk).
* **📄 Multimodal Document Ingestion:** Native parsing of PDFs (`pypdf`, PyMuPDF), Word documents (`python-docx`), and scanned images via Gemini Vision Multimodal OCR with automated page-level confidence scoring.
* **🧠 LangGraph State Machine:** Deterministic workflow execution: OCR Extraction $\rightarrow$ Clause Identification $\rightarrow$ Vector RAG Retrieval $\rightarrow$ Taxonomy Normalization $\rightarrow$ Constrained Legal Reasoning.
* **📚 Grounded RAG Policy Knowledge Base:** Cross-references contract text against `risk_taxonomy.csv` and corporate policy text blocks stored in an in-memory or file-backed **Qdrant** Vector DB using Google's native **`gemini-embedding-001`** (768-dimensional) dense embeddings .
* **⚖️ Human-in-the-Loop Governance:** Enforces legal accountability through explicit review actions (`ACCEPT`, `REJECT`, `EDIT`, `ESCALATE`), logging every decision to an immutable PostgreSQL audit trail.
* **📊 Executive PDF Reporting & AI Scorecards:** Generates color-coded Executive Compliance Reports via ReportLab and calculates real-time RAGAS evaluations (Faithfulness, Relevancy, Precision, Recall).

---

## 🏗️ Enterprise System Architecture Blueprint

### 1. Multi-Tier Layered System Topology
The platform is designed around a modular, multi-tier architecture spanning a React presentation layer, a FastAPI backend gateway, and robust vector-relational persistence engines.

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
║  │  PostgreSQL 15 DB   │  ║  ║ │  LangGraph Engine     │ ║  ║ │ Qdrant Vector Store (File/Memory)     │ ║
║  │ ┌─────────────────┐ │  ║  ║ │ ┌───────────────────┐ │ ║  ║ │ ┌───────────────────────────────────┐ │ ║
║  │ │ UserModel       │ │  ║  ║ │ │ RAG Retrieval     │ │ ║  ║ │ │ 768-Dim Gemini Embeddings         │ │ ║
║  │ │ DocumentModel   │ │  ║  ║ │ └─────────┬─────────┘ │ ║  ║ │ │ (gemini-embedding-001)            │ │ ║
║  │ │ ClauseModel     │ │  ║  ║ │ ┌─────────▼─────────┐ │ ║  ║ │ └─────────────────┬─────────────────┘ │ ║
║  │ │ AuditLogModel   │ │  ║  ║ │ │ Gemini Extraction │ │ ║  ║ │ ┌─────────────────▼─────────────────┐ │ ║
║  │ └─────────────────┘ │  ║  ║ │ └─────────┬─────────┘ │ ║  ║ │ │ Risk Taxonomy & Structured Policies│ │ ║
║  └─────────────────────┘  ║  ║ │ ┌─────────▼─────────┐ │ ║  ║ │ │ (Parsed via Regex Blocks / CSV)   │ │ ║
║                           ║  ║ │ │ Normalization     │ │ ║  ║ │ └───────────────────────────────────┘ │ ║
║  ┌─────────────────────┐  ║  ║ │ └─────────┬─────────┘ │ ║  ╚═══════════════════════════════════════════╝
║  │ Audit Log Storage   │  ║  ║ │ ┌─────────▼─────────┐ │ ║                                              ║
║  │ (audit_logs.json)   │  ║  ║ │ │ Legal Reasoning   │ │ ║  ╔═══════════════════════════════════════════╗
║  └─────────────────────┘  ║  ║ │ └───────────────────┘ │ ║  ║  6. OBSERVABILITY & TRACING LAYER        ║
║                           ║  ║ └───────────────────────┘ ║  ║ ┌───────────────────────────────────────┐ ║
║  ┌─────────────────────┐  ║  ╚═════════════════════════╝  ║ │ LangSmith Tracing & Evaluator        │ ║
║  │ PDF Report Generator│  ║                               ║ │ (Tata_Legal_Contract_Benchmark_v1)  │ ║
║  │ (ReportLab Engine)  │  ║                               ║ └───────────────────────────────────────┘ ║
║  └─────────────────────┘  ║                               ╚═══════════════════════════════════════════╝
╚═══════════════════════════╝

```

### 2. End-to-End Processing & Dataflow Architecture

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
│   │ (Vector Policy Query)  │         │ (gemini-embedding-001)       │   │
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

## 🧠 AI Engineering & Resiliency Architecture

* **Triple-Tier Resiliency & Fallback Engine:** To guarantee high availability, the platform features a model cascade (`gemini-3.5-flash` $\rightarrow$ `gemini-2.5-flash` $\rightarrow$ `gemini-2.0-flash`). If cloud models experience rate limits or quotas, a deterministic local heuristic evaluation scanner kicks in automatically.
* **Vector Database & Custom Block Parsing:** Powered by 768-dimensional dense vector embeddings generated via `gemini-embedding-001`. Knowledge base files (`.txt`) are dynamically parsed using robust block-splitting algorithms looking for `TITLE:`, `CATEGORY:`, and `REFERENCE_ID:` keys.



---

## 📚 Knowledge Base Assets & Grounded RAG



The backend anchors its RAG pipeline using specialized policy text files placed in `backend/data/knowledge_base/` alongside `risk_taxonomy.csv`:

* `approved_clause_library.txt`
* `compliance_guidelines.txt`
* `confidentiality_policy.txt`
* `jurisdiction_guidelines.txt`
* `liability_cap_policy.txt`

---

## 🗄️ Database Schema & Relational Design

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

## 🌐 Complete REST API Reference

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/v1/auth/register` | `POST` | Register a new user profile with role and business unit |
| `/api/v1/auth/login` | `POST` | Authenticate user and issue Bearer JWT access token |
| `/api/v1/documents/upload` | `POST` | Upload legal document and trigger LangGraph pipeline |
| `/api/v1/documents/history` | `GET` | Fetch document history filtered by user credentials |
| `/api/v1/documents/{id}` | `GET` | Get document analysis details and extracted clauses |
| `/api/v1/documents/{id}/export-pdf` | `GET` | Download ReportLab certified compliance audit PDF |
| `/api/v1/chat/query` | `POST` | Query Aadhya Legal AI Assistant with active context |
| `/api/v1/review/actions` | `POST` | Submit human-in-the-loop review sign-offs (`ACCEPT`/`REJECT`) |
| `/api/v1/admin/llm-config` | `POST` | Dynamically update active LLM model and API key in DB |

---

## 🚀 Quick Start Deployment Guide

### Option 1: Render Cloud Deployment (Recommended)

1. Connect your repository to Render via the `render.yaml` Blueprint configuration.
2. Render provisions the Web API, Frontend, and PostgreSQL instances automatically.
3. Configure your environment keys on the Render dashboard.

### Option 2: Local Docker Compose Cluster

1. Copy the environment variables template:
```bash
cp .env.example .env

```


2. Build and launch the multi-container environment:
```bash
docker-compose up -d --build

```


3. Open your browser:
* **Frontend UI:** `http://localhost:5173`
* **Swagger Docs:** `http://localhost:8000/docs`



---

## 🧪 Testing, Guardrails & Evaluation Suite

* **RAGAS Evaluator:** Computes Faithfulness, Answer Relevancy, Context Precision, and Context Recall using a specialized `RateLimitedLLM` wrapper with smart backoffs.
* **LangSmith Benchmark:** Validates extraction accuracy using `evaluate_pipeline.py`.
* **Pytest Suite:** Execute all system unit tests via `pytest`.

---

## 🔒 Security, Data Governance & Compliance

* **Dynamic Key Persistence:** Secrets and model choices are persisted directly into PostgreSQL, overriding static environment variables safely.
* **Data Isolation:** User permissions restrict document lookups to authorized business units.
* **Immutable Auditing:** Review decisions are permanently written to PostgreSQL and static JSON records.

---

## 🎬 Demonstration Scenarios

1. **Vendor NDA Review:** Upload a standard NDA to verify confidentiality terms and indemnities.
2. **Unlimited Liability Escalation:** Upload a supplier contract with high financial exposure to trigger `HIGH` risk compliance flags.
3. **Conversational Deflection:** Interrogate Aadhya AI on out-of-domain inquiries to test persona boundaries.

---

## 📂 Comprehensive Project Directory Structure

```text
Tata-Group-AI-Legal-Document-Intelligence-System/
├── backend/
│   ├── api/v1/
│   │   ├── auth.py             # JWT Register, Login & User Auth 
│   │   ├── chat.py             # Aadhya Legal AI Chat Assistant 
│   │   ├── documents.py        # File Upload, Retrieval & PDF Export 
│   │   ├── governance.py       # Admin configuration & review oversight 
│   │   ├── review.py           # Human-in-the-loop action logging 
│   │   └── router.py           # Unified FastAPI router assembly
│   │   └── admin_routes.py     # Admin_login
│   │   └── knowledge_base.py   # Knowledge_base for rag retrival
│   │   └── monitoring.py       # It's for admin monitoring tab
│   │   └── risk_review.py      # Show all HIGH-risk clauses to authorized users
│   ├── data/
│   │   ├── knowledge_base/     # Enterprise Policy text files (.txt) 
│   │   ├── uploads             # this shows the uploaded doc
│   ├── document_pipeline/
│   │   ├── clause_extraction/  # Clause isolation prompts 
│   │   ├── normalization/      # Taxonomy Header Normalizer 
│   │   ├── ocr/                # Multimodal OCR & PyMuPDF Engine 
│   │   ├── parsing/            # Structural text chunking 
│   │   ├── reporting/          # ReportLab PDF Generator
│   │   └── summary/            # automatically generate an executive-level summary of a contract using Gemini
│   │   └── legal_graph.py      # LangGraph State Graph Orchestrator
│   └── governance/
│   │   └── governance_service.py  # Who reviewed this contract, what did they do, when did they do it, and what did they change?
│   ├── services/
│   │   ├── llm_config.py       # PostgreSQL dynamic key management 
│   │   ├── rag_service.py      # Qdrant Vector Search & Gemini Embeddings 
│   │   └── ragas_evaluator.py  # Real-time RAGAS scoring engine 
│   ├── storage/                # Local uploads, reports & audit JSONs 
│   ├── database.py             # SQLAlchemy Session & Engine Config 
│   ├── models.py               # PostgreSQL Relational ORM Schemas 
│   └── main.py                 # FastAPI Application Gateway
│   └── requirements.txt        # all requirenment file
│   └── Dockerfile              # Docker file for backened
│   └── data/
│   │   └── risk_taxonomy.csv   # Standard risk rules & trigger
│   └── deployment/             # all .md files for deployment phase
│   │   └── backend_deployment.md  # readme.md file for backend deployment
│   │   └──  environment_setup.md  # readme.md file for environment setup guidlines
│   │   └── vercel_notes.md
│   └── docs/                   # Documents related to api , architecture, demo_script, and security notes and some screenshots
│   │   └── screenshots/        # some screenshots of the forentend
│   └── api_documentation.md
│   └── architecutre.md
│   └── demo_script.md
│   └── security_notes.md
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── component/
│   │   │   ├── AuthGate.tsx               # Login & Registration Portal 
│   │   │   ├── DocumentWorkspace.tsx      # Central Upload & RAG Matrix UI 
│   │   │   └── PipelineVisualizer.tsx     # LangGraph status visualizer
│   │   │   └── DocumentHistorySidebar.tsx # Document history for each user
│   │   │   └── LegalChatWidget.tsx        # Aadhya Chatbot
│   │   │   └── LegalOpsDashboard.tsx      # So this component itself doesn't calculate the legal metrics. It gets them from the backend.
│   │   │   └── AdminPortal.tsx            # The admin ui or frontend
│   │   ├── component/
│   │   │   └── hero.png
│   │   │   └── react.svg
│   │   │   └── vite.svg  
│   │   ├── App.tsx                        # Root Layout & Global State
│   │   ├── App.css                        # The css file for app
│   │   ├── main.tsx                       # React 19 Entrypoint 
│   │   └── index.css                      # Tailwind CSS v4 Global Styles 
│   ├── Dockerfile                         # Node Builder & Nginx Server 
│   └── package.json                       # Frontend Dependencies
│   └── scripts/
│   │   └── evaluate_pipeline.py           # This file is your quality-control system for the RAG + LangGraph + LLM legal pipeline.
├── tests/                              # Pytest Suite
│   └── ai_output_tests/
│   │   └── eval_dataset.json          # dataset for ragas metric
│   │   └── reags_eval_gemini.py       # for ragas metrics calcuator
│   │   └── test_chat_and_rag.py       # for overall chat and rag test
│   └── document_processing_tests/
│   │   └── test_ocr_and_parsing.py    # for testing ocr and parsing services
│   └── edge_cases/
│   │   └── test_error_handling.py     # Manintaning the error handling
│   └── functional_tests/
│   │   └── test_api_endpoints.py      # for testing endpoints of API
├── docker-compose.yml                  # Local Multi-Container Deployment 
├── render.yaml                         # Render Cloud Blueprint Config 
├── Dockerfile.backend                  # Python 3.12 Backend Image 
├── requirements.txt                    # Python Backend Dependencies 
└── .env.example                        # Environment Template
└── README.md                           # Readme File

```
