# 🏛️ Tata AI Legal Intelligence

**Enterprise Document Parsing, RAG Grounding & Risk Governance Portal**

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System)

An advanced, full-stack enterprise application designed for corporate legal and compliance teams. This system automates the ingestion, parsing, and risk assessment of legal contracts (like Master Service Agreements, NDAs, etc.) using AI and Retrieval-Augmented Generation (RAG). It provides a secure, isolated workspace for officers to review AI-extracted clauses, log audit actions, and generate certified compliance reports.

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
    - [2. AI Content Evaluation Framework](#2-ai-content-evaluation-framework)
    - [3. Pytest Unit \& Integration Test Suite](#3-pytest-unit--integration-test-suite)
  - [☁️ Render Deployment](#️-render-deployment)
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
- [Executive Overview](#-executive-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Repository Structure](#-repository-structure)
- [Knowledge Base Assets](#-knowledge-base-assets)
- [Pipeline & Workflows](#-pipeline--workflows)
  - [1. Data Ingestion & Parsing](#1-data-ingestion--parsing)
  - [2. RAG Risk Matrix & Governance](#2-rag-risk-matrix--governance)
  - [3. Audit & Reporting](#3-audit--reporting)
- [Installation & Setup](#-installation--setup)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Security & Compliance](#-security--compliance)
- [License & Support](#-license--support)

---

## 🏢 Executive Overview

In large enterprise environments, evaluating operational and legal contracts requires meticulous, secure, and standardized review. Relying on manual oversight can lead to inconsistencies and missed risk vectors. 

This platform provides:
* **Grounded AI Synthesis:** Evaluates extracted clauses against enterprise policy via Vector DB grounding, ensuring AI rationales are strictly tied to approved internal guidelines.
* **Automated Risk Assessment:** Highlights risks (HIGH/MEDIUM/LOW) with generated AI rationales directly linked to extracted contract clauses.
* **Strict RBAC & Governance:** Features a secure, human-in-the-loop workflow allowing officers to 'ACCEPT' or 'REJECT' documents, securely logging all decisions into an immutable audit trail.
* **Certified Reporting:** Generates certified compliance reports and Executive Audit Packages dynamically.

---

## ✨ Key Features

| Feature Component | Description |
| :--- | :--- |
| **RBAC Query & Access** | Uses JWT-based authentication with strict role-based access control (RBAC) to ensure users only interact with their isolated document history. |
| **AI Processing Pipeline** | Automated OCR (`ocr_service.py`), structural parsing, and entity extraction tailored for highly structured legal documents. |
| **RAG Risk Matrix** | Blends RAG capabilities (`rag_service.py`) with enterprise policy texts to score extracted clauses and generate highlighted risk rationales. |
| **Governance Engine** | Human-in-the-loop workflow (`governance_service.py`) for auditing, accepting, or overriding AI risk assessments. |
| **Aadhya AI Assistant** | Context-aware floating chat widget that allows users to seamlessly interrogate the active legal document. |
| **Certified PDF Export** | 1-click generation of Executive Audit Packages, dynamically streaming binary blobs back to the frontend. |

---

## 📐 System Architecture

```text
                                  +---------------------------------+
                                  |      Enterprise User            |
                                  +---------------------------------+
                                                   | (Credentials)
                                                   v
                                  +---------------------------------+
                                  |           AuthGate              |
                                  |        (api/v1/auth.py)         |
                                  +---------------------------------+
                                                   | (JWT Token)
                                                   v
                                  +---------------------------------+
                                  |    React Dashboard (Frontend)   |
                                  |  (Vite, Tailwind, TypeScript)   |
                                  +---------------------------------+
                                      /            |                                                 /             |                                                 v              v              v
                  +--------------------+  +-----------------+  +-------------------+
                  | History Sidebar    |  | Workspace       |  | Aadhya AI Widget  |
                  |                    |  | (documents.py)  |  | (chat.py)         |
                  +--------------------+  +-----------------+  +-------------------+
                            |                      |                     |
                            |                      v                     v
                            |           +-------------------+  +-------------------+
                            |           | Document Pipeline |  | Qdrant Vector DB  |
                            |           | (OCR & Parsing)   |  | (rag_service.py)  |
                            |           +-------------------+  +-------------------+
                            |                      |
                            v                      v
                       +---------------------------------------------+
                       |             PostgreSQL DB                   |
                       |       (database.py, models.py)              |
                       +---------------------------------------------+
                                                   |
                                                   v
                                  +---------------------------------+
                                  |     PDF Reporting Engine        |
                                  |     (reporting services)        |
                                  +---------------------------------+
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

### 2. AI Content Evaluation Framework

The AI output is evaluated as a **content-quality and grounding layer around the existing LangGraph workflow**. LangGraph remains responsible for deterministic orchestration, while LangSmith provides observability, benchmark execution, trace inspection, and evaluation of generated legal content.

```text
                    Legal Contract
                           │
                           ▼
                  ┌─────────────────┐
                  │    LangGraph    │
                  │ State Workflow  │
                  └────────┬────────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
        RAG Retrieval  Clause Output  Risk Reasoning
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                 ┌───────────────────┐
                 │   LangSmith      │
                 │ Trace + Evaluate │
                 └─────────┬─────────┘
                           │
          ┌────────────────┼─────────────────┐
          ▼                ▼                 ▼
   Risk Accuracy     Policy Grounding   Output Quality
          │                │                 │
          └────────────────┼─────────────────┘
                           ▼
                  Evaluation Results
```

#### Evaluation dimensions

| Evaluation Dimension | What is checked | Existing project signal |
| :--- | :--- | :--- |
| **Risk Classification Accuracy** | Whether the predicted `HIGH/MEDIUM/LOW` risk matches the benchmark expectation | `risk_accuracy_score` |
| **RAG Policy Grounding** | Whether generated rationales are supported by retrieved enterprise policies | `rag_policy_citation_score` |
| **Clause Extraction Quality** | Whether important legal clauses are correctly identified and structured | Ground-truth benchmark comparison |
| **Citation / Evidence Quality** | Whether risk explanations remain tied to approved policy evidence | Retrieved policy context + citation output |
| **Guardrail Behaviour** | Whether Aadhya deflects non-legal/out-of-domain questions | Out-of-domain guardrail tests |
| **Fallback Consistency** | Whether local heuristic evaluation still returns structured risk output when LLM calls fail | `_dynamic_fallback_evaluation()` |

#### LangGraph + LangSmith responsibility split

* **LangGraph:** Controls the deterministic state-machine execution of `retrieve_rag_context → extract_clauses → normalize_clauses → legal_reasoning`.
* **LangSmith:** Captures traces and supports benchmark-based inspection/evaluation of the AI workflow and generated content.
* **Local evaluator:** Provides deterministic fallback scoring when cloud LLM evaluation is unavailable.
* **Pytest:** Validates application behaviour, guardrails, OCR confidence limits, normalization, and API/integration boundaries.

#### Evaluation command

```bash
python evaluate_pipeline.py
```

The benchmark is designed to verify that improvements to prompts, retrieval, model selection, or fallback behaviour do not silently reduce legal-risk accuracy or policy grounding.

### 3. Pytest Unit & Integration Test Suite
Executes unit tests covering OCR confidence limits, clause normalization, fallback heuristics, and out-of-domain chat guardrails:

```bash
pytest
```

---

## ☁️ Render Deployment

The project includes a repository-level `render.yaml` Blueprint configuration for Render deployment. This file should be treated as the deployment configuration source for the services defined in the repository.

### Render Blueprint Configuration

The deployment architecture is defined directly in:

```text
render.yaml
```

The Blueprint configuration defines the Render resources, build/start commands, environment-variable wiring, and service relationships used by the deployment.

### Deploy with `render.yaml`

1. Push the project to GitHub with `render.yaml` present at the repository root.
2. In Render, create a new **Blueprint** and select the GitHub repository.
3. Render reads the repository's `render.yaml` and provisions the services declared by the Blueprint.
4. Configure any environment values/secrets that are intentionally supplied by Render rather than committed to source control.
5. After deployment, verify the deployed frontend/backend endpoints and confirm the application can communicate with its configured database and AI/RAG services.

### Deployment Configuration

The repository's `render.yaml` is the authoritative configuration for the Render deployment. Keep the README aligned with that file whenever service names, build commands, start commands, environment variables, or deployment relationships change.

> **Important:** Do not copy secrets such as API keys into `render.yaml` or the README. Use Render's environment-variable/secret configuration for sensitive values.

### Render Deployment Flow

```text
                    GitHub Repository
                           │
                           ▼
                     render.yaml
                           │
                           ▼
                    Render Blueprint
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Web / API      Frontend      Database /
        Services       Service       Dependencies
              │            │
              └──────┬─────┘
                     ▼
              Tata AI Legal
             Intelligence System
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Gemini     RAG /       LangSmith
        AI       Qdrant      Tracing & Eval
```

### Post-Deployment Verification

After Render provisions the Blueprint:

- Confirm every service declared in `render.yaml` reaches a healthy/running state.
- Verify the backend starts using the command defined by the Blueprint.
- Verify the frontend is built using the configuration defined by the Blueprint.
- Confirm required environment variables are available to the correct service.
- Test authentication and the document-upload workflow.
- Test the LangGraph document-processing workflow.
- Verify RAG retrieval and legal-risk evaluation.
- Verify LangSmith traces/evaluation data when LangSmith is configured.
- Confirm the Aadhya AI Assistant can reach the deployed backend.

The existing Docker Compose and local-development deployment sections remain unchanged; the Render Blueprint is an additional deployment path.

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
├── render.yaml                   # Render Blueprint Deployment Configuration
├── Dockerfile.backend              # Python 3.12 Backend Linux Image
├── requirements.txt                # Python Backend Package Dependencies
├── .env.example                    # Environment Template Configuration
└── README.md                       # Comprehensive Technical Documentation
## 📁 Repository Structure

```text
.
├── backend/                         # FastAPI Application Core
│   ├── api/v1/                      # API Endpoints
│   │   ├── auth.py                  # JWT Authentication
│   │   ├── chat.py                  # Aadhya AI chat endpoints
│   │   ├── documents.py             # Document upload & retrieval
│   │   ├── governance.py            # Audit & approval workflows
│   │   ├── knowledge_base.py        # Vector DB sync & management
│   │   ├── monitoring.py            # System health metrics
│   │   ├── review.py                # Human-in-the-loop actions
│   │   └── risk_review.py           # RAG-based risk matrix endpoints
│   ├── data/
│   │   └── knowledge_base/          # Source truths for Grounded RAG
│   │       ├── approved_clause_library.txt
│   │       ├── compliance_guidelines.txt
│   │       ├── confidentiality_policy.txt
│   │       ├── internal_policies.txt
│   │       ├── jurisdiction_guidelines.txt
│   │       └── liability_cap_policy.txt
│   ├── document_pipeline/           # Ingestion & AI Processing
│   │   ├── clause_extraction/       # NLP entity & clause extraction
│   │   ├── normalization/           # Text standardization
│   │   ├── ocr/                     # Optical Character Recognition
│   │   └── parsing/                 # Structural data framing
│   ├── governance/                  # Core governance logic
│   ├── services/                    
│   │   └── rag_service.py           # RAG retrieval and synthesis
│   ├── database.py                  # PostgreSQL ORM connection
│   ├── models.py                    # SQLAlchemy Data Models
│   └── main.py                      # FastAPI Application Entry
├── data/                            # Sample Datasets & taxonomies
│   ├── risk_taxonomy.csv
├── deployment/                      # DevOps Instructions
│   ├── backend_deployment.md
│   ├── environment_setup.md
│   └── vercel_notes.md
├── docs/                            # Extensive Documentation
│   ├── api_documentation.md
│   ├── architecture.md
│   └── security_notes.md
├── frontend/                        # React 18 & TypeScript Workspace
│   ├── src/
│   │   ├── assets/
│   │   ├── component/               # Workspace, Sidebar, Chat Widget
│   │   └── styles/                  # Tailwind CSS (Glassmorphism)
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── tests/                           # Comprehensive Pytest Suite
│   ├── ai_output_tests/             # Grounding & Hallucination checks
│   ├── document_processing_tests/   # OCR pipeline validation
│   ├── edge_cases/
│   └── functional_tests/            # API endpoint integration tests
├── .env                             # Environment Variables
├── docker-compose.yml               # Multi-container orchestration
└── Dockerfile.backend               # Backend Container Image
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
## 📚 Knowledge Base Assets

To prevent AI hallucination, the system's `rag_service.py` strictly grounds generated rationales against predefined enterprise policy text files stored in `backend/data/knowledge_base/`:

* `approved_clause_library.txt` — Standard templates and acceptable fallbacks for MSAs.
* `compliance_guidelines.txt` — Regulatory standards and mandatory compliance checks.
* `confidentiality_policy.txt` — Strict rules regarding NDA scope and data handling.
* `jurisdiction_guidelines.txt` — Approved governing laws and venue stipulations.
* `liability_cap_policy.txt` — Financial exposure limits and indemnification thresholds.

---

## 🔄 Pipeline & Workflows

### 1. Data Ingestion & Parsing
The workflow starts when an Enterprise User uploads a contract via the Frontend Workspace. 
* Requests hit `backend/api/v1/documents.py`.
* The file routes through `backend/document_pipeline/ocr/ocr_service.py` to extract text from scanned PDFs.
* The content is structurally chunked by `parsing_service.py` and specific legal entities are isolated via `clause_extraction/`.

### 2. RAG Risk Matrix & Governance
Extracted clauses are evaluated by the AI Risk Engine:
* `backend/services/rag_service.py` performs a similarity search against the Vector DB (populated by the Knowledge Base Assets).
* `backend/api/v1/risk_review.py` calculates risk vectors (HIGH/MEDIUM/LOW).
* A prompt is orchestrated ensuring strict adherence to the retrieved policy files, producing an explainable rationale for the assigned risk level.

### 3. Audit & Reporting
* Risk matrices are delivered to the UI where legal officers review the findings.
* Using `backend/api/v1/governance.py`, users Accept, Reject, or Modify the clauses.
* Final decisions are immutably written via `database.py` to PostgreSQL.
* Executive audit reports are generated dynamically and exported.

---

## ⚙️ Installation & Setup

### Prerequisites
* Docker & Docker Compose
* Node.js 18+ (for local frontend development)
* Python 3.10+ (for local backend development)

### Deployment (Dockerized)

For a managed cloud alternative, see [Render Deployment](#️-render-deployment). The existing Dockerized deployment remains unchanged.

The application utilizes Docker Compose for a seamless, containerized deployment of the entire stack (FastAPI, React UI, PostgreSQL, and Vector DB).

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System.git
   cd Tata-Group-AI-Legal-Document-Intelligence-System
   ```

2. **Environment Setup:**
   * Create a `.env` file in the root directory.
   * Reference the configurations detailed in `deployment/environment_setup.md`.

3. **Launch the Stack:**
   ```bash
   docker-compose up --build -d
   ```
   * The Frontend will be available at `http://localhost:3000` (or configured Nginx port).
   * The Backend API will be available at `http://localhost:8000`.

---

## 🔧 Configuration

### Environment Variables (`.env`)
You must configure the following key areas for full functionality:
* `DATABASE_URL`: Connection string for PostgreSQL.
* `JWT_SECRET_KEY` & `JWT_ALGORITHM`: Secure hashing for API authentication.
* `VECTOR_DB_URL`: Endpoint for Qdrant/Chroma instance.
* `OPENAI_API_KEY` (or Local LLM configurations) for the extraction and chat services.

### Frontend Styling (`tailwind.config.js`)
The application uses a Glassmorphism design pattern. Custom brand colors and border-radius settings are pre-configured to match enterprise portal standards.

---

## 🚀 Usage Guide

### 1. Authenticate & Access Workspace
Log in via the main AuthGate portal. Axios interceptors will handle token passing for all subsequent API calls. Only authorized personnel will have access to the upload mechanics.

### 2. Upload & Parse
Drag and drop a legal contract (PDF/DOCX) into the workspace. The system will automatically engage the document pipeline to process the file and run it against the approved clause library.

### 3. Review Risk Matrix
Examine the AI-highlighted clauses on the dashboard. 
* **Red:** High Risk (Critical deviations from `liability_cap_policy.txt` or `jurisdiction_guidelines.txt`).
* **Yellow:** Medium Risk (Standard deviations requiring review).
* **Green:** Low Risk (Matches `approved_clause_library.txt`).

### 4. Interrogate with Aadhya AI
Use the floating chat widget on the bottom right to ask specific questions about the active document (e.g., *"What are the termination conditions listed in section 4?"*).

---

## 🔒 Security & Compliance

* **Isolated Contexts:** RBAC ensures users cannot query or access document pipelines outside their authorized department.
* **Immutable Auditing:** The `governance_service.py` explicitly blocks soft-deletions of human-in-the-loop decisions, creating a permanent paper trail of who approved which clause.
* **Grounded Integrity:** Strict system prompts prevent hallucinated legal assumptions by forcing the LLM to cite internal knowledge bases exclusively.

---

## 📄 License & Support

**Internal Enterprise Software**  
For support, refer to the documentation in the `docs/` folder or contact the AI Governance IT team. 

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System)
