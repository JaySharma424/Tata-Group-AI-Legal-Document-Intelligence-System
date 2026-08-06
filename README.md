# 🏛️ Tata AI Legal Intelligence

**Enterprise Document Parsing, RAG Grounding & Risk Governance Portal**

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System)

An advanced, full-stack enterprise application designed for corporate legal and compliance teams. This system automates the ingestion, parsing, and risk assessment of legal contracts (like Master Service Agreements, NDAs, etc.) using AI and Retrieval-Augmented Generation (RAG). It provides a secure, isolated workspace for officers to review AI-extracted clauses, log audit actions, and generate certified compliance reports.

---

## 📋 Table of Contents
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
