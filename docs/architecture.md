# Tata AI Legal Intelligence System - Architecture Documentation

## System Overview

The **Tata AI Legal Intelligence System** is an enterprise-grade Legal Contract Analysis and RAG Risk Assessment platform. It automates contract ingestion, multi-modal OCR text extraction, structural clause taxonomy normalization, vector-based policy retrieval (Qdrant), LLM risk reasoning (LangGraph), and automated RAG performance scoring (RAGAS).

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                             REACT FRONTEND UI                               │
 │   - Workspace Ingestion   - RAGAS Scorecard   - Admin Governance Portal   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │ (REST API / JSON)
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                            FASTAPI BACKEND                                  │
 │                                                                             │
 │  ┌───────────────────────────────────────────────────────────────────────┐  │
 │  │                      LANGGRAPH ORCHESTRATION                          │  │
 │  │  Extract Clauses ──► Ground RAG ──► Normalize ──► Legal Reasoning    │  │
 │  └──────┬────────────────────┬─────────────────────────────┬─────────────┘  │
 │         │                    │                             │                │
 │         ▼                    ▼                             ▼                │
 │  ┌─────────────┐    ┌─────────────────┐           ┌─────────────────┐       │
 │  │ Gemini LLM  │    │  Qdrant Vector  │           │ PostgreSQL DB   │       │
 │  │ Reasoning   │    │  Database       │           │ - Documents     │       │
 │  │ (3.5-Flash) │    │  (Policy RAG)   │           │ - System Config │       │
 │  └─────────────┘    └─────────────────┘           │ - Audit Logs    │       │
 │                                                   └─────────────────┘       │
 │                                                                             │
 │  ┌───────────────────────────────────────────────────────────────────────┐  │
 │  │                       RAGAS EVALUATION ENGINE                         │  │
 │  │  Faithfulness  •  Answer Relevancy  •  Precision  •  Recall           │  │
 │  └───────────────────────────────────────────────────────────────────────┘  │
 └─────────────────────────────────────────────────────────────────────────────┘

```

---

## 🔄 Core Components

### 1. LangGraph State Pipeline (`LegalPipelineState`)

The analysis pipeline uses LangGraph `StateGraph` for predictable, stateful execution across four nodes:

1. **`extract_clauses_node`:** Extracts distinct legal clauses from OCR document text using Google Gemini (`gemini-3.5-flash`), featuring fallback cascades (`gemini-3.6-flash`, `gemini-2.0-flash-lite`).
2. **`ground_clauses_with_rag_node`:** Queries Qdrant Vector DB per clause to fetch top matching enterprise legal policy citations (e.g., `CLS-GEN-020`, `TAX-1`).
3. **`normalize_clauses_node`:** Standardizes raw headings into Tata Enterprise Legal Taxonomy.
4. **`legal_reasoning_node`:** Generates risk ratings (`HIGH`, `MEDIUM`, `LOW`), risk rationales, and locks citations to prevent hallucinated reference IDs.

### 2. PostgreSQL Relational Storage

All dynamic configuration, metadata, and audit records are persisted in PostgreSQL via SQLAlchemy:

* **`system_config`:** Stores runtime Gemini API keys and active models (`SystemConfigModel`).
* **`documents`:** Stores contract metadata, OCR scores, masked API key tracking (`api_key_masked`), active model (`llm_model_used`), and RAGAS scorecards.
* **`clauses`:** Stores extracted clause text, risk levels, rationales, and cited policy IDs.
* **`audit_logs`:** Immutable record of human accept/reject actions.

### 3. Qdrant Vector Database (RAG Engine)

* Stores 132+ embedded Tata Group compliance rules and risk policy vectors using `gemini-embedding-001`.
* **Resilience:** Implements lazy loading and falls back to an in-memory instance if disk locks occur on container restart.

### 4. RAGAS Evaluation Engine (`ragas_evaluator.py`)

Evaluates the retrieval and reasoning quality of the RAG pipeline:

* **Evaluated Metrics:** `Faithfulness`, `Answer Relevancy`, `Context Precision`, `Context Recall`.
* **Grounding Scheme:** Evaluates the **Uploaded Document Clause** (`user_input`) against the **Qdrant KB Policy** (`retrieved_contexts` & `reference`) and the **LLM Risk Rationale** (`response`).
* **Free-Tier Protection:**
* Wraps LangChain models in `RateLimitedLLM` with backoff logic for HTTP 429 quota errors.
* Isolates `asyncio` event loops to prevent Render `uvloop` crashes.
* Uses `RunConfig(timeout=180, max_workers=1)` to prevent async `TimeoutError()` exceptions.
* Implements `sanitize_score()` to clean mathematical `NaN` values before JSON serialization.



---

## 🌐 Deployment Architecture

* **Host:** Render Web Service (`uvicorn backend.main:app`).
* **Runtime:** Python 3.12, Node.js React Frontend.
* **State Persistence Strategy:** Overcomes Render's ephemeral filesystem by storing LLM configuration and keys directly in PostgreSQL (`system_config`), ensuring updates survive server restarts.