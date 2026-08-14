# 🏛️ Tata Group AI Legal Document Intelligence System

> **Enterprise Legal Document Intelligence, Grounded RAG, Clause Extraction & Risk Governance**

[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)]()
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react)]()
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)]()
[![LangGraph](https://img.shields.io/badge/LangGraph-AI%20Workflow-orange)]()
[![RAGAS](https://img.shields.io/badge/RAGAS-Evaluation-blueviolet)]()
[![LLM Config](https://img.shields.io/badge/LLM%20Config-PostgreSQL-success)]()
[![RAG](https://img.shields.io/badge/RAG-Grounded%20Legal%20Reasoning-purple)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?logo=postgresql)]()
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20Search-red)]()
[![Render](https://img.shields.io/badge/Render-Deployment-46E3B7?logo=render)]()

---

## 📌 Overview

The **Tata Group AI Legal Document Intelligence System** is an enterprise-oriented AI platform designed to reduce the manual burden of first-pass legal document review while keeping **human legal professionals in control of interpretation, approval, escalation, and final decisions**.

The system transforms uploaded contracts, vendor agreements, policy documents, regulatory filings, and compliance records into structured legal intelligence through:

**Upload → OCR → Parsing → Clause Extraction → RAG Retrieval → Legal Reasoning → Risk Flagging → Summarization → Human Review → Audit**

The product is intentionally designed as a **governed document-intelligence system rather than a generic chatbot**. Every material AI output should remain connected to document evidence, retrieved approved context, confidence information, and reviewer decisions.

**Source:** *Tata Group: AI Legal Document Intelligence System*, Executive Overview and product vision, pp. 1–2, 4–5.  
**Citation:** fileciteturn1file0L11-L25

---

## 🎯 Problem Statement

Enterprise legal and compliance teams must review large volumes of:

- Contracts
- Vendor agreements
- Commercial agreements
- Policy documents
- Regulatory filings
- Internal compliance records

Manual first-pass review can delay procurement, vendor onboarding, negotiations, compliance work, and internal decision-making. The product dossier identifies recurring risks such as:

- Unfavorable obligations
- Vague indemnity language
- Missing termination rights
- Unusual liability caps
- Privacy exposure
- Compliance gaps
- Conflicting or unusual provisions

The objective is therefore not to replace legal judgment, but to provide a **common intelligence layer** that helps legal teams identify important clauses, compare obligations, surface deviations, and prioritize high-risk items for expert review.

**Source:** Product Dossier, Executive Overview and "Why This Release Is Time-Critical", pp. 1–2.  
**Citation:** fileciteturn1file0L26-L42

---

## 🧭 Product Vision

> **Move from uploaded legal documents to review-ready contract summaries and risk flags with speed, evidence traceability, and human approval.**

The system unifies:

- OCR
- NLP/document parsing
- Clause extraction
- Vector retrieval
- Retrieval-Augmented Generation (RAG)
- Constrained LLM reasoning
- Risk classification
- Legal summarization
- Human-in-the-loop review
- Audit logging

The core principle is:

**AI accelerates legal analysis; authorized legal professionals retain final authority.**

**Source:** Product Dossier, Product Vision, p. 4.  
**Citation:** fileciteturn1file3L177-L193

---

## ⭐ Key Objectives

| Objective | System Capability |
|---|---|
| Review Velocity | Automate the first-pass extraction, summarization and risk-screening workflow |
| Clause-Level Accuracy | Extract important clauses, obligations, dates, parties and legal terms with traceability |
| Grounded Reasoning | Retrieve approved policies, clause libraries and prior positions before generating conclusions |
| Risk Flag Quality | Detect missing, unusual, conflicting and high-risk clauses with rationale |
| Human Approval | Allow accept, edit, reject, escalate and comment actions |
| Auditability | Preserve document history, AI outputs and reviewer decisions |
| Deployment Readiness | Provide a repeatable, reviewable enterprise workflow |

**Source:** Product Dossier, Leadership Expectations, p. 3.  
**Citation:** fileciteturn1file2L71-L124

---

# 🏗️ System Architecture

## High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                         USER / LEGAL REVIEWER                    │
│                    React + TypeScript Frontend                   │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                         FASTAPI API LAYER                        │
│              Authentication • Upload • Review • Chat            │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                     DOCUMENT PROCESSING                          │
│      PDF/DOCX → OCR → Parsing → Sections → Metadata             │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH AI WORKFLOW                         │
│                                                                  │
│  Clause Extraction → RAG Retrieval → Normalization              │
│              → Legal Reasoning → Risk Classification             │
│                         → Summarization                          │
└───────────────┬──────────────────────┬───────────────────────────┘
                │                      │
                ▼                      ▼
       ┌─────────────────┐    ┌─────────────────────────┐
       │ Qdrant / Vector │    │ PostgreSQL              │
       │ Knowledge Store │    │ Metadata / Audit / Data │
       └─────────────────┘    └─────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│                 HUMAN REVIEW & GOVERNANCE                        │
│          Accept • Reject • Escalate • Comment                    │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                 REPORTING / AUDIT / OBSERVABILITY                │
│             PDF Reports • Logs • Metrics • Evaluation            │
└──────────────────────────────────────────────────────────────────┘
```

The product dossier describes the same lifecycle as a legal document job moving through upload, OCR, parsing, clause extraction, retrieval, reasoning, summarization, risk classification and human review, with structured outputs and errors retained at each stage.

**Source:** Product Dossier, Technical Architecture, pp. 7–9.  
**Citation:** fileciteturn1file5L348-L351  
**Citation:** fileciteturn1file9L475-L491

---

# 🔄 End-to-End Processing Flow

```text
1. Upload Document
       │
       ▼
2. Validate Metadata / File
       │
       ▼
3. OCR
       │
       ▼
4. Structural Parsing
       │
       ▼
5. Clause Extraction
       │
       ▼
6. Clause Normalization
       │
       ▼
7. RAG Retrieval
       │
       ├── Approved Clause Library
       ├── Corporate Policies
       ├── Prior Agreement Positions
       └── Compliance References
       │
       ▼
8. Constrained Legal Reasoning
       │
       ▼
9. Risk Classification
       │
       ▼
10. Summary + Obligation Map
       │
       ▼
11. Human Review
       │
       ├── ACCEPT
       ├── REJECT
       ├── ESCALATE
       └── COMMENT
       │
       ▼
12. Audit Trail + Report
```

The intended workflow requires material risk flags to be supported by extracted document evidence and, where applicable, retrieved approved context.

**Source:** Product Dossier, architecture and validation requirements, pp. 4, 6, 12–13.  
**Citation:** fileciteturn1file4L206-L245

---

# 📄 Document Intake

The system is designed to accept, where technically feasible:

- PDF
- DOCX
- Scanned document images
- Text-based legal files

The upload workflow captures:

- Document type
- Business unit
- Counterparty
- Geography / jurisdiction
- Confidentiality level
- Review priority
- Processing/readiness status

Unsupported, incomplete, unreadable, or invalid documents should generate clear user-facing errors.

**Source:** Product Dossier, Detailed Product Requirements, p. 6.  
**Citation:** fileciteturn0file1L245-L255

---

# 🔍 OCR & Document Parsing

The OCR and parsing layer is responsible for converting documents into structured, traceable content.

### OCR responsibilities

- Extract text from scanned pages
- Preserve page numbers
- Store page-level OCR confidence
- Detect unreadable/low-confidence pages
- Preserve extraction status

### Parsing responsibilities

- Identify headings and sections
- Detect tables
- Detect annexures
- Identify signature blocks
- Preserve clause/document locations
- Extract relevant metadata

Low-confidence pages should be explicitly flagged rather than silently treated as reliable input.

**Source:** Product Dossier, OCR and Parsing Pipeline, p. 6.  
**Citation:** fileciteturn0file1L251-L255

---

# ⚖️ Clause Intelligence

The clause extraction layer identifies and normalizes important legal provisions.

### Target clause categories

- Indemnity
- Limitation of liability
- Confidentiality
- Termination
- Renewal
- Payment
- Data protection
- Governing law
- Dispute resolution
- Audit rights
- Compliance obligations

Each extracted clause should contain structured metadata such as:

```json
{
  "clause_type": "limitation_of_liability",
  "extracted_text": "...",
  "page_reference": "Page 18",
  "section_reference": "12.3",
  "involved_party": "...",
  "obligation_owner": "...",
  "confidence": 0.94
}
```

The system should also identify expected clauses that are missing for a particular document type or business context.

**Source:** Product Dossier, Clause Extraction and Normalization, p. 6.  
**Citation:** fileciteturn0file1L256-L262

---

# 📚 Grounded RAG

The RAG layer prevents the reasoning model from operating only on the uploaded document.

It retrieves relevant approved context from sources such as:

- Approved clause libraries
- Internal policies
- Prior approved agreement positions
- Compliance guidance
- Regulatory references
- Risk taxonomy
- Review playbooks

Retrieved references should be ranked using available metadata such as:

- Relevance
- Document type
- Business unit
- Jurisdiction
- Recency
- Approval status

Outdated or unapproved references should not be treated as high-confidence legal context.

**Source:** Product Dossier, RAG Retrieval and Knowledge Context, p. 6.  
**Citation:** fileciteturn0file1L263-L270

---

# 🧠 Legal Reasoning & Risk Flagging

The reasoning layer generates structured legal-review outputs rather than unrestricted text.

Every material risk flag should ideally contain:

```json
{
  "severity": "HIGH",
  "risk_category": "LIABILITY",
  "affected_clause": "Clause 14.2",
  "rationale": "...",
  "source_location": "Page 32",
  "retrieved_reference": "LIABILITY-POLICY-004",
  "recommended_action": "ESCALATE",
  "confidence": 0.91
}
```

### Risk categories include

- Missing information
- Ambiguous language
- Non-standard wording
- Conflicting obligations
- High-risk provisions

The system must not present an AI-generated legal conclusion as a final approved legal decision before authorized human review.

**Source:** Product Dossier, Legal Reasoning and Risk Flagging, p. 6.  
**Citation:** fileciteturn0file1L271-L277

---

# 📝 Legal Summarization

The summary layer produces:

- Contract overview
- Key terms
- Key obligations
- Obligation maps
- Risk summaries
- Missing-clause indicators
- Deviation notes
- Recommended follow-up actions
- Approval notes

Generated summaries should retain clause citations and disclose low OCR/extraction confidence where relevant.

Summaries must remain editable before approval and should preserve version history.

**Source:** Product Dossier, Summarization and Review Output, p. 6.  
**Citation:** fileciteturn0file1L278-L282

---

# 👨‍⚖️ Human-in-the-Loop Governance

The system is designed around human legal accountability.

Reviewers can:

| Action | Purpose |
|---|---|
| `ACCEPT` | Approve an AI-generated output |
| `EDIT` | Correct or modify the interpretation |
| `REJECT` | Mark the output as unusable |
| `ESCALATE` | Route high-risk/uncertain items to senior review |
| `COMMENT` | Add reviewer context or instructions |

Approval status should be visible at document, clause and risk levels where appropriate.

Reviewer identity, timestamp, decision and rationale must be captured for auditability.

**Source:** Product Dossier, Human Review and Approval Layer, p. 6.  
**Citation:** fileciteturn0file1L283-L287

---

# 🗄️ Data Architecture

## PostgreSQL

Recommended for structured operational data:

```text
User
 ├── Document
 │    ├── Clause
 │    ├── Obligation
 │    ├── RiskFlag
 │    ├── Summary
 │    └── ReviewAction
 │
 └── AuditLog
```

Typical records include:

- User and role information
- Document metadata
- Processing jobs
- OCR confidence
- Extracted clauses
- Obligations
- Retrieval references
- Risk flags
- Generated summaries
- Reviewer actions
- Approval status
- Audit events

## Vector Database

The vector layer stores embeddings for:

- Document chunks
- Clause references
- Approved policies
- Clause libraries
- Prior positions
- Compliance references

The product dossier explicitly recommends a vector database for embeddings and metadata-aware retrieval.

**Source:** Product Dossier, Data Assets and Technical Architecture, pp. 9–10.  
**Citation:** fileciteturn0file1L445-L461

---

# 🧰 Technology Stack

The following stack reflects the implementation represented in the supplied project README, aligned with the architecture described in the product dossier.

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI, Uvicorn, Python 3.12 |
| AI Orchestration | LangGraph, LangChain |
| LLM | Google Gemini models |
| Embeddings | Gemini embedding model |
| RAG | Qdrant |
| Relational DB | PostgreSQL |
| ORM | SQLAlchemy |
| PDF Processing | PyMuPDF / fitz |
| DOCX Processing | python-docx |
| NLP | spaCy |
| OCR | Gemini Vision / OCR pipeline |
| Reporting | ReportLab |
| Evaluation | RAGAS, LangSmith |
| RAGAS Metrics | Faithfulness, Answer Relevancy, Context Precision, Context Recall |
| Evaluation Reliability | Rate-limited LLM wrapper, retries, async support, configurable RunConfig |
| LLM Configuration | PostgreSQL-backed runtime model, embedding model and API-key configuration |
| Testing | Pytest |
| Deployment | Render |
| Configuration | PostgreSQL runtime configuration + environment-variable fallback |

The product dossier lists FastAPI, React, OCR tooling, spaCy/PyMuPDF/pdfplumber, Qdrant/Chroma/pgvector, Gemini, LangChain/LangGraph, PostgreSQL, deployment services, and structured logging as suitable technology choices.

**Source:** Product Dossier, Recommended Technology Choices, p. 9.  
**Citation:** fileciteturn0file1L390-L444

---


# ⚙️ Runtime LLM Configuration

The project includes a dedicated **LLM configuration service** so model and embedding configuration can be changed without hard-coding those values throughout the application.

The implementation uses a PostgreSQL-backed `SystemConfigModel` and exposes two core operations:

```text
                         ┌─────────────────────────────┐
                         │      Admin / Config API     │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │      update_llm_config()    │
                         │  • API key                  │
                         │  • LLM model                │
                         │  • Embedding model          │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │        PostgreSQL           │
                         │      SystemConfigModel      │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │       get_llm_config()      │
                         │ Reads active runtime config │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │ RAG / RAGAS / LLM Services  │
                         └─────────────────────────────┘
```

### Implemented behavior

- Ensures the `SystemConfigModel` table exists at runtime.
- Reads the active `llm_model`, `embedding_model`, and API key from PostgreSQL.
- Falls back to environment configuration when the database configuration is unavailable.
- Provides defaults for the Gemini LLM and embedding models.
- Allows runtime updates of the API key, LLM model and embedding model.
- Updates the in-process `GEMINI_API_KEY` environment value immediately after a successful key change.
- Uses transaction rollback on update failure.

The current implementation defaults to:

```text
LLM Model        → gemini-3.5-flash
Embedding Model  → gemini-embedding-001
API Key          → PostgreSQL value, otherwise GEMINI_API_KEY
```

The implementation is contained in:

```text
backend/services/llm_config.py
```

**Implementation source:** `llm_config.py` — PostgreSQL-backed configuration retrieval, fallback handling, runtime updates and transaction management. fileciteturn2file1L5-L8 fileciteturn2file1L36-L69

### Why this design fits the product requirements

The product dossier requires backend-controlled secrets, secure environment variables, controlled configuration, traceability and an architecture where operational data and AI workflow state can be governed centrally. The runtime configuration service implements that principle by moving the active AI configuration into backend persistence rather than scattering model configuration across application code.

**PDF source:** Security and non-functional requirements, pp. 7–8. fileciteturn1file5L296-L327

---

# 🧩 Core Product Surfaces

The application is organized around the following user-facing workspaces:

### 1. Document Upload Workspace
Upload contracts, agreements, policies, filings and compliance records.

### 2. OCR & Parsing Monitor
Track page-level extraction quality, processing state, failed pages and document sections.

### 3. Clause Intelligence Panel
Inspect clauses, obligations, counterparties, dates, renewal terms, termination rights, liability terms and compliance references.

### 4. Risk Review Console
Review severity, rationale, affected clauses, evidence, confidence and recommended actions.

### 5. RAG Knowledge Workspace
Inspect approved policies, clause libraries, prior positions and retrieved context.

### 6. Legal Summary Workspace
Review contract summaries, obligation maps, risk narratives and comparison notes.

### 7. Legal Operations Dashboard
Monitor document volume, turnaround time, risk categories, escalations and approval outcomes.

**Source:** Product Dossier, Product Surfaces, p. 4.  
**Citation:** fileciteturn1file3L183-L195

---

# 🔌 API Design

The API should keep document storage and processing logic separated and keep secrets and sensitive files backend-controlled.

Representative endpoints:

| Endpoint | Method | Purpose |
|---|---:|---|
| `/api/v1/auth/register` | POST | Register user |
| `/api/v1/auth/login` | POST | Authenticate user |
| `/api/v1/documents/upload` | POST | Upload and create processing job |
| `/api/v1/documents/{id}` | GET | Retrieve document analysis |
| `/api/v1/documents/{id}/clauses` | GET | Retrieve extracted clauses |
| `/api/v1/documents/{id}/risks` | GET | Retrieve risk flags |
| `/api/v1/documents/{id}/summary` | GET | Retrieve generated summary |
| `/api/v1/review/actions` | POST | Record reviewer action |
| `/api/v1/audit/{id}` | GET | Retrieve audit information |
| `/api/v1/chat/query` | POST | Query the legal AI assistant |

The product dossier calls for endpoints covering upload, OCR jobs, clause extraction, retrieval, summary generation, review actions and audit retrieval.

**Source:** Product Dossier, API/engineering discussion, p. 4.  
**Citation:** fileciteturn1file4L220-L227

---

# 🧪 Evaluation Framework

Evaluation is a first-class part of the system.

## AI Evaluation Metrics

The project should evaluate:

- **Clause Recall** — Were expected clauses detected?
- **Risk-Flag Precision** — Are flagged risks actually relevant?
- **Summary Faithfulness** — Does the summary remain grounded in source evidence?
- **Citation Accuracy** — Do citations point to the correct document locations?
- **Structured Output Validity** — Does the model follow the required schema?
- **Reviewer Acceptance Rate** — How often are AI outputs accepted by reviewers?
- **Refusal / Insufficient-Evidence Behavior** — Does the system avoid unsupported conclusions?

The project now implements these evaluation requirements through a dedicated RAGAS evaluator, while the broader test suite can validate clause extraction, risk classification, citations and workflow behavior. The product dossier explicitly recommends test documents with known expected clauses and risks.

**Source:** Product Dossier, AI Engineering and Evaluation requirements, p. 4 and testing approach, p. 13.  
**Citation:** fileciteturn1file4L213-L223  
**Citation:** fileciteturn1file7L396-L405

---


# 📐 RAGAS Evaluation & Quality Scoring

The system also includes a dedicated **RAGAS evaluation layer** for measuring the quality of the grounded RAG workflow.

The evaluator is implemented in:

```text
backend/services/ragas_evaluator.py
```

### Implemented RAGAS metrics

The evaluator computes:

| Metric | What it checks |
|---|---|
| **Faithfulness** | Whether the generated risk rationale is supported by the provided context |
| **Answer Relevancy** | Whether the generated response is relevant to the clause-level question |
| **Context Precision** | Whether retrieved context is relevant to the evaluation |
| **Context Recall** | Whether the retrieved context covers the expected ground-truth context |
| **Answer Correctness** | Included in the returned scorecard contract |

The product dossier explicitly calls for evaluation of clause recall, risk-flag precision, summary faithfulness, citation accuracy and reviewer acceptance, and it identifies evaluation as a critical engineering concern. The implemented RAGAS layer provides concrete runtime measurements for the grounded retrieval and answer-quality portion of that evaluation strategy.

**PDF source:** Evaluation requirements and engineering discussion, p. 4. fileciteturn1file4L213-L223

### Evaluation pipeline

```text
Uploaded Clause
      │
      ▼
Extracted Contract Text
      │
      ▼
Matched Policy / Risk Context from Qdrant
      │
      ▼
┌──────────────────────────────────────┐
│            RAGAS Dataset             │
│                                      │
│ user_input                           │
│ retrieved_contexts                   │
│ response                             │
│ reference                            │
└────────────────┬─────────────────────┘
                 │
                 ▼
      Faithfulness / Relevancy
      Context Precision / Recall
                 │
                 ▼
         RAGAS Scorecard
```

### Grounded evaluation design

For each selected clause, the evaluator uses:

- **User input:** the extracted contract clause framed as a compliance-risk question.
- **Retrieved context:** the matched knowledge-base policy text.
- **Response:** the generated risk rationale.
- **Reference:** the policy text treated as the compliance ground truth.

The evaluator currently prioritizes a **high-risk clause** for targeted evaluation, which makes the scorecard especially useful for monitoring the quality of risk-oriented RAG behavior.

**Implementation source:** `ragas_evaluator.py`, scorecard construction and clause/context mapping. fileciteturn2file2L82-L123

### Rate-limit resilience

The RAGAS evaluator includes a custom `RateLimitedLLM` wrapper that:

- Retries model calls up to four attempts.
- Detects `429`, `RESOURCE_EXHAUSTED`, and quota-related failures.
- Waits before retrying.
- Supports both synchronous and asynchronous generation.
- Cleans fenced JSON/model output before returning results.

This is important for cloud evaluation workloads where repeated LLM calls can otherwise cause timeout or quota failures.

**Implementation source:** `ragas_evaluator.py`, rate-limit wrapper. fileciteturn2file2L47-L80

### Runtime evaluation configuration

The evaluator uses:

```text
RunConfig(
    timeout=180,
    max_retries=3,
    max_workers=1
)
```

and runs RAGAS with `raise_exceptions=False` so a failed evaluation run can return a safe empty result rather than crashing the document workflow.

**Implementation source:** `ragas_evaluator.py`, RAGAS runtime configuration and evaluation call. fileciteturn2file2L123-L159

### LLM and embedding integration

The evaluator obtains the active model configuration from the PostgreSQL-backed LLM configuration service and then initializes:

```text
ChatGoogleGenerativeAI
GoogleGenerativeAIEmbeddings
```

This means the same runtime model configuration can be reused by the legal RAG evaluation layer rather than duplicating model-selection logic.

**Implementation source:** `ragas_evaluator.py`. fileciteturn2file2L90-L100

### Mapping to the product requirements

The product dossier states that AI outputs must be grounded in document evidence and retrieved approved context, and that evaluation should verify faithfulness, citation accuracy and risk-flag quality.

The implemented RAGAS layer directly supports that governance model by measuring whether the RAG response remains aligned with the retrieved policy context.

**PDF source:** Grounded legal reasoning, risk-flag quality and evaluation requirements. fileciteturn1file2L90-L111 fileciteturn1file4L213-L223

---

# 🧪 Test Coverage

Testing should include:

### Document Tests

- Text-based PDFs
- Scanned PDFs
- DOCX documents
- Long agreements
- Annexures
- Tables
- Poor-quality scans
- Mixed-format documents

### Legal Edge Cases

- Missing clauses
- Duplicate clauses
- Conflicting obligations
- Unusual governing-law provisions
- Unsupported document types
- Retrieval failure
- Model timeout
- Low OCR confidence
- Ambiguous language

### Functional Tests

```text
Upload
  ↓
OCR Job
  ↓
Parsing
  ↓
Clause Extraction
  ↓
RAG Retrieval
  ↓
Reasoning
  ↓
Summary
  ↓
Review Action
  ↓
Audit Retrieval
```

Failures should be visible, actionable, and preserve partial outputs where useful.

**Source:** Product Dossier, Testing Approach, p. 13.  
**Citation:** fileciteturn1file7L396-L405

---

# 🔐 Security & Data Governance

Legal documents may contain commercially sensitive, personal and confidential information.

The system should therefore enforce:

- Role-based access
- Business-unit isolation
- Controlled document access
- Encrypted storage where applicable
- Backend-only secrets
- Secure environment variables
- Restricted telemetry
- Audit logging
- Controlled model-service data flows
- Visible approval status
- Evidence traceability

Sensitive document content should not be exposed through frontend logs or uncontrolled telemetry.

**Source:** Product Dossier, Security, Logging and Observability + Non-Functional Expectations, pp. 7–8.  
**Citation:** fileciteturn1file5L273-L327

---

# 📊 Observability

Operational monitoring should capture:

- Upload events
- Processing stages
- Model calls
- Retrieval references
- Failures
- Retries
- Processing latency
- Reviewer actions
- OCR quality
- Clause extraction coverage
- Reviewer acceptance rate

This provides a traceable path from the original document through AI processing to the final human decision.

**Source:** Product Dossier, Security, Logging and Observability, p. 7.  
**Citation:** fileciteturn1file5L273-L277

---

# 🚀 Deployment

## Production Architecture

```text
                         ┌───────────────────┐
                         │   React Frontend  │
                         │      Render       │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │   FastAPI Backend │
                         │      Render       │
                         └──────┬───────┬────┘
                                │       │
                     ┌──────────┘       └──────────┐
                     ▼                             ▼
              ┌──────────────┐              ┌──────────────┐
              │ PostgreSQL   │              │ Qdrant       │
              │ Operational  │              │ Vector/RAG   │
              │ Data + Audit │              │ Knowledge     │
              └──────────────┘              └──────────────┘
```

The product dossier recommends deploying the frontend through services such as Vercel/Netlify and the backend through hosted API services such as Render/Railway, with credentials stored in environment variables.

**Source:** Product Dossier, Deployment Approach, p. 11.  
**Citation:** fileciteturn1file6L363-L369

---

# 🌐 Live Deployment

The supplied project README identifies the following deployment targets:

- **Frontend:** `https://tata-ai-frontend.onrender.com`
- **Backend API / Swagger:** `https://tata-ai-backend-og7t.onrender.com/docs`
- **Backend Health:** `https://tata-ai-backend-og7t.onrender.com/`

> Replace these URLs if the deployment environment changes.

---

# ⚙️ Local Setup

## 1. Clone Repository

```bash
git clone https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System.git
cd Tata-Group-AI-Legal-Document-Intelligence-System
```

## 2. Configure Environment

Create the environment file:

```bash
cp .env.example .env
```

Configure the required credentials for:

```text
DATABASE_URL=
GOOGLE_API_KEY=
QDRANT_URL=
QDRANT_API_KEY=
SECRET_KEY=
```

Do not commit real credentials.

The product dossier explicitly requires model, OCR, database, vector database, storage and authentication credentials to be supplied through environment variables.

**Source:** Product Dossier, Deployment Approach, p. 11.  
**Citation:** fileciteturn1file6L363-L369

---

## 3. Backend

```bash
cd backend

python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn main:app --reload
```

Swagger documentation:

```text
http://localhost:8000/docs
```

---

## 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Typical development URL:

```text
http://localhost:5173
```

---

# 📂 Project Structure

```text
Tata-Group-AI-Legal-Document-Intelligence-System/
│
├── backend/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── chat.py
│   │       ├── documents.py
│   │       ├── review.py
│   │       ├── router.py
│   │       ├── admin_routes.py
│   │       ├── knowledge_base.py
│   │       ├── monitoring.py
│   │       └── risk_review.py
│   │
│   ├── data/
│   │   ├── knowledge_base/
│   │   └── risk_taxonomy.csv
│   │
│   ├── document_pipeline/
│   │   ├── clause_extraction/
│   │   ├── normalization/
│   │   ├── ocr/
│   │   ├── parsing/
│   │   └── reporting/
│   │
│   ├── services/
│   │   ├── llm_config.py          # PostgreSQL-backed runtime LLM/embedding config
│   │   ├── rag_service.py         # Qdrant vector retrieval / grounded RAG
│   │   └── ragas_evaluator.py     # RAGAS quality scoring with rate-limit resilience
│   │
│   ├── storage/
│   ├── database.py
│   ├── models.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── component/
│   │   │   ├── AuthGate.tsx
│   │   │   ├── DocumentWorkspace.tsx
│   │   │   ├── PipelineVisualizer.tsx
│   │   │   ├── DocumentHistorySidebar.tsx
│   │   │   ├── LegalChatWidget.tsx
│   │   │   └── AdminPortal.tsx
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   └── Dockerfile
│
├── deployment/
│   ├── backend_deployment.md
│   ├── environment_setup.md
│   └── render_frontend_notes.md
│
├── docs/
│   ├── architecture.md
│   ├── api_documentation.md
│   ├── security_notes.md
│   ├── demo_script.md
│   └── screenshots/
│
├── tests/
│   ├── functional_tests/
│   ├── document_processing_tests/
│   ├── ai_output_tests/
│   └── edge_cases/
│
├── scripts/
│   └── evaluate_pipeline.py
│
├── render.yaml
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

# 🎬 Demonstration Flow

A recommended leadership demonstration should follow the complete product journey:

```text
Upload Vendor Agreement
        ↓
Document Readiness
        ↓
OCR / Parsing
        ↓
Clause Extraction
        ↓
RAG Retrieval
        ↓
Risk Flagging
        ↓
Contract Summary
        ↓
Reviewer Validation
        ↓
Accept / Edit / Reject / Escalate
        ↓
Audit Record / Report
```

Recommended demo scenarios include:

1. **Vendor Agreement Review** — demonstrate first-pass contract analysis.
2. **Policy Document Summary** — demonstrate grounded document summarization.
3. **High-Risk Clause Escalation** — demonstrate risk identification and senior-review routing.

**Source:** Product Dossier, Primary User Journeys and Demo Requirements, pp. 5 and 11.  
**Citation:** fileciteturn1file8L417-L463  
**Citation:** fileciteturn1file6L362-L369

---

# 📈 Primary User Journeys

| Journey | Input | System Behavior | Expected Output |
|---|---|---|---|
| Contract First-Pass Review | Vendor/commercial agreement | OCR → parsing → extraction → RAG → reasoning → summary | Review-ready contract summary |
| Clause Risk Detection | Contract with unusual/missing terms | Compare against approved references | Prioritized risk list |
| Obligation Comparison | Multiple agreements | Extract obligations, dates and commitments | Structured comparison |
| Policy/Filing Review | Policy or regulatory document | Parse + retrieve context + summarize | Compliance-oriented summary |
| Senior Legal Escalation | High-risk/uncertain item | Package evidence and rationale | Escalation-ready review record |

**Source:** Product Dossier, Primary User Journeys, p. 5.  
**Citation:** fileciteturn1file8L417-L463

---

# 🛡️ AI Guardrails

The system should enforce the following principles:

### 1. Evidence First

A material risk flag should reference extracted document evidence.

### 2. Approved Context

When external legal context is needed, use approved/retrieved references.

### 3. Structured Outputs

Use schemas for:

- Clause records
- Risk flags
- Summaries
- Obligation maps
- Reviewer actions

### 4. No Autonomous Final Legal Decision

AI output remains pending human approval.

### 5. Confidence Visibility

Expose confidence and source locations to reviewers.

### 6. Audit Everything Important

Persist model outputs, retrieval references and reviewer decisions.

**Source:** Product Dossier, AI workflow validation and governance requirements, pp. 12–13.  
**Citation:** fileciteturn1file7L381-L405

---

# 🧠 RAG Quality Principles

A legal RAG pipeline should not be judged only by whether it produces a fluent answer.

The system should be evaluated on:

```text
Question
   │
   ▼
Relevant Retrieval
   │
   ▼
Correct Source Context
   │
   ▼
Grounded Reasoning
   │
   ▼
Correct Citation
   │
   ▼
Useful Legal Review Output
```

A response should be considered weak if it:

- Retrieves irrelevant policy material
- Uses outdated or unapproved context
- Makes a claim without evidence
- Cites the wrong clause/page
- Produces a risk flag unsupported by the document
- Presents an uncertain conclusion as a final legal decision

---

# 💰 Cost & Performance Strategy

The product dossier identifies cost optimization and practical processing time as non-functional requirements.

Recommended techniques include:

- Asynchronous document processing
- Background jobs
- Chunking
- Caching
- Tiered model routing
- Token-budget controls
- Batch processing
- Retention policies
- Usage dashboards
- Cost alerts

**Source:** Product Dossier, Non-Functional Expectations, pp. 7–8.  
**Citation:** fileciteturn1file5L288-L347

---

# 🧱 Extensibility Roadmap

The first release should establish the traceable document-intelligence foundation.

Future extensions can include:

- Negotiation playbooks
- Obligation monitoring
- Policy mapping
- Enterprise document repository integrations
- Expanded compliance workflows
- Advanced analytics
- Recurring obligation tracking

The product dossier explicitly positions these capabilities as later expansion areas after the core upload-to-human-approval workflow is proven.

**Source:** Product Dossier, Leadership Discussion and Product Vision, p. 4.  
**Citation:** fileciteturn1file3L169-L182

---

# ⚠️ Important Legal & Governance Disclaimer

This system is intended to **assist legal and compliance professionals** with document analysis, clause discovery, evidence retrieval, summarization and risk prioritization.

It should **not** be represented as an autonomous legal decision-maker.

AI-generated outputs must remain clearly identifiable as system-generated and should remain pending authorized legal review until approved.

**Source:** Product Dossier, Human Approval and Governance requirements, pp. 3, 4 and 6.  
**Citation:** fileciteturn1file2L106-L117  
**Citation:** fileciteturn1file4L232-L245

---

# 📚 Source & Traceability

This README is based primarily on the supplied project implementation README and the following product-design source:

> **Tata Group: AI Legal Document Intelligence System**  
> Internal Product Dossier  
> 15-page product, architecture, requirements, testing and deployment specification.

### PDF sections used

| README Area | PDF Source |
|---|---|
| Product purpose | Executive Overview, pp. 1–2 |
| Business problem | Why This Release Is Time-Critical, pp. 1–2 |
| Success criteria | Leadership Expectations, p. 3 |
| Product vision | Product Blueprint, pp. 4–5 |
| Product surfaces | Product Surfaces, p. 4 |
| User journeys | Primary User Journeys, p. 5 |
| Functional requirements | Detailed Product Requirements, p. 6 |
| Security & NFRs | Security / Non-Functional Expectations, pp. 7–8 |
| Technical architecture | Technical Architecture, pp. 8–9 |
| Technology choices | Recommended Technology Choices, p. 9 |
| Data assets | Data Assets Required, p. 9 |
| Deployment | Deployment Flow / Deployment Approach, pp. 10–11 |
| AI guardrails | AI workflow requirements, pp. 12–13 |
| Testing | Testing Approach, p. 13 |
| Demo | Demonstration requirements, p. 11 |

**Primary source citation:** fileciteturn0file1L2-L8

---

# 👥 Intended Users

The platform is intended for enterprise workflows involving:

- Legal teams
- Compliance teams
- Procurement teams
- Business-unit reviewers
- Senior counsel
- Legal operations
- Risk/governance teams
- Engineering and AI quality teams

The system's purpose is to help these users spend less time on repetitive first-pass analysis and more time on judgment, negotiation strategy, escalation and accountable approval.

---


# ✅ Implemented AI Engineering Components

Beyond the core document-processing and RAG workflow, the project includes two important production-oriented components:

### PostgreSQL-backed LLM Configuration
The active Gemini LLM model, embedding model and API key can be read from and updated in PostgreSQL, with environment-variable fallback and transaction-safe updates. fileciteturn2file1L8-L34 fileciteturn2file1L36-L69

### RAGAS Evaluation
The system evaluates clause-level RAG behavior using Faithfulness, Answer Relevancy, Context Precision and Context Recall, with a quota-aware `RateLimitedLLM`, asynchronous support and explicit timeout/retry configuration. fileciteturn2file2L47-L80 fileciteturn2file2L123-L159

These components strengthen the project's alignment with the product dossier's requirements for **evaluation, evidence-grounded reasoning, operational observability, secure configuration and governed AI review workflows**. fileciteturn1file5L296-L327

# 🏁 Project Outcome

The target outcome is a **traceable, governed legal-document intelligence workflow** where a user can:

```text
Upload
  ↓
Extract
  ↓
Retrieve
  ↓
Reason
  ↓
Flag
  ↓
Summarize
  ↓
Review
  ↓
Approve
  ↓
Audit
```

The core success criterion is not simply generating a good-looking AI answer. The system must make it possible for a reviewer to understand:

1. **What the document says**
2. **Which clause was identified**
3. **Why the clause was flagged**
4. **Which evidence supports the flag**
5. **Which approved context was retrieved**
6. **How confident the system is**
7. **What action the reviewer should take**
8. **Who approved or changed the result**
9. **What was ultimately recorded for audit**

This traceability-first approach follows the product dossier's central requirement for evidence-grounded AI with human approval and auditability.

**Source:** Product Dossier, Executive Overview, Technical Architecture and Governance requirements.  
**Citation:** fileciteturn1file0L18-L25
