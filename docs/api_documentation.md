Here is the complete, updated content for your **`api_documentation.md`** file:

```markdown
# Tata AI Legal Intelligence System - API Documentation

## Base Overview
* **Base URL:** `https://tata-ai-backend-og7t.onrender.com`
* **Version:** `v1`
* **Authentication:** JWT Bearer Token (`Authorization: Bearer <TOKEN>`)
* **Content-Type:** `application/json` (except multi-part file uploads)

---

## 🔑 Authentication Endpoints

### 1. User Login
Authenticates an enterprise user and returns a JWT access token.

* **Endpoint:** `POST /api/v1/auth/login`
* **Content-Type:** `application/x-www-form-urlencoded` or `application/json`

#### Request Body
```json
{
  "username": "compliance.officer@tata.com",
  "password": "your_secure_password"
}

```

#### Response (`200 OK`)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "role": "Admin",
  "email": "compliance.officer@tata.com"
}

```

---

## 📄 Document Processing & Analysis Endpoints

### 2. Upload and Analyze Legal Contract

Uploads a legal document (PDF/DOCX/Txt), runs OCR/Parsing, executes the 4-node LangGraph analysis pipeline, grounds clauses against Qdrant Vector DB, and triggers RAGAS metrics evaluation.

* **Endpoint:** `POST /api/v1/documents/upload`
* **Content-Type:** `multipart/form-data`

#### Form Parameters

| Field Name | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | File | **Yes** | Contract file (PDF, DOCX, TXT) |
| `business_unit` | String | **Yes** | Enterprise BU (e.g., `Procurement`, `Legal`) |
| `document_category` | String | **Yes** | Category (e.g., `Vendor Agreement`, `MSA`) |
| `confidentiality_level` | String | **Yes** | `Confidential`, `Restricted`, or `Standard` |
| `review_priority` | String | **Yes** | `High`, `Medium`, or `Normal` |
| `document_type` | String | No | Document type (Default: `Master Services Agreement`) |
| `counterparty` | String | No | Name of counterparty (e.g., `Acme Inc`) |
| `jurisdiction` | String | No | Legal jurisdiction (e.g., `Global`, `India`) |

#### Response (`200 OK`)

```json
{
  "message": "Document successfully processed via LangGraph.",
  "job_id": "c3c4cb37-3602-4fa9-9483-6fe3dba1ffb3",
  "llm_model_used": "gemini-3.5-flash",
  "api_key_masked": "...fkkQ",
  "metrics": {
    "ocr_confidence": 96.0,
    "pages": 1,
    "entities_detected": 87,
    "requires_manual_review": false
  },
  "ragas_scores": {
    "faithfulness": 0.85,
    "answer_relevancy": 0.825,
    "context_precision": 0.78,
    "context_recall": 0.88,
    "answer_correctness": 1.0
  },
  "clauses": [
    {
      "clause_type": "LIMITATION OF LIABILITY",
      "extracted_text": "Neither party shall be liable for indirect or consequential damages...",
      "confidence_score": 0.95,
      "risk_level": "HIGH",
      "risk_rationale": "Uncapped liability exception breaches Tata Group Risk Policy.",
      "involved_party": "Both Parties",
      "rag_reference_used": "TAX-1",
      "page_reference": "Section 4"
    }
  ],
  "clauses_extracted_count": 1
}

```

---

### 3. Get Document Details & RAGAS Metrics

Fetches analyzed contract metadata, clause breakdowns, and stored RAGAS scorecard metrics.

* **Endpoint:** `GET /api/v1/documents/{document_id}`

#### Response (`200 OK`)

```json
{
  "document": {
    "job_id": "c3c4cb37-3602-4fa9-9483-6fe3dba1ffb3",
    "filename": "Tata_Vendor_Agreement.pdf",
    "business_unit": "Procurement",
    "category": "Vendor Agreement",
    "created_at": "2026-08-13T04:24:19.470Z",
    "ocr_confidence": 96.0,
    "pages_processed": 1,
    "llm_model_used": "gemini-3.5-flash",
    "api_key_masked": "...fkkQ",
    "ragas_faithfulness": 0.85,
    "ragas_answer_relevancy": 0.825,
    "ragas_context_precision": 0.78,
    "ragas_context_recall": 0.88
  },
  "clauses": [...]
}

```

---

### 4. Fetch User Analysis History

Returns all processed contracts uploaded by or accessible to the logged-in user.

* **Endpoint:** `GET /api/v1/review/history`

#### Response (`200 OK`)

```json
[
  {
    "job_id": "c3c4cb37-3602-4fa9-9483-6fe3dba1ffb3",
    "filename": "Tata_Vendor_Agreement.pdf",
    "business_unit": "Procurement",
    "document_category": "Vendor Agreement",
    "ocr_confidence": 96.0,
    "pages": 1,
    "created_at": "2026-08-13T04:24:19",
    "llm_model_used": "gemini-3.5-flash",
    "api_key_masked": "...fkkQ",
    "ragas_scores": {
      "faithfulness": 0.85,
      "answer_relevancy": 0.825,
      "context_precision": 0.78,
      "context_recall": 0.88
    }
  }
]

```

---

### 5. Export Certified Audit PDF

Generates a downloadable ReportLab PDF audit report with compliance rationale and reviewer sign-offs.

* **Endpoint:** `GET /api/v1/documents/{job_id}/export-pdf`
* **Query Parameter:** `token` (Optional token for direct browser links)

#### Response

* **Content-Type:** `application/pdf`
* **Header:** `Content-Disposition: attachment; filename="Audit_Report_Tata_Vendor_Agreement.pdf"`

---

## ⚙️ Governance & LLM Configuration Endpoints

### 6. Get Active System Configuration

Fetches the active LLM engine model, embedding model, and masked Gemini API key stored in PostgreSQL.

* **Endpoint:** `GET /api/v1/admin/llm-config`

#### Response (`200 OK`)

```json
{
  "llm_model": "gemini-3.5-flash",
  "embedding_model": "gemini-embedding-001",
  "api_key": "...fkkQ"
}

```

---

### 7. Update Gemini Key & LLM Model (Admin)

Persists a new Gemini API Key or LLM Model directly into PostgreSQL `system_config`.

* **Endpoint:** `POST /api/v1/admin/llm-config`

#### Request Body

```json
{
  "api_key": "AIzaSyD...YourNewKey",
  "llm_model": "gemini-3.5-flash",
  "embedding_model": "gemini-embedding-001"
}

```

#### Response (`200 OK`)

```json
{
  "message": "LLM Configuration updated successfully.",
  "llm_model": "gemini-3.5-flash",
  "embedding_model": "gemini-embedding-001",
  "api_key": "...fkkQ"
}

```

---

### 8. Test LLM Connection

Tests connection with the newly provided Gemini key before saving.

* **Endpoint:** `POST /api/v1/admin/llm-config/test`

#### Request Body

```json
{
  "api_key": "AIzaSyD...YourNewKey",
  "llm_model": "gemini-3.5-flash"
}

```

#### Response (`200 OK`)

```json
{
  "status": "success",
  "message": "Connection successful! Model gemini-3.5-flash responded."
}

```

---

## ✍️ Human-in-the-Loop Review Endpoints

### 9. Submit Compliance Sign-Off

Logs human reviewer actions (`ACCEPT` / `REJECT`) with compliance notes to the immutable audit trail.

* **Endpoint:** `POST /api/v1/review/actions`

#### Request Body

```json
{
  "document_id": "c3c4cb37-3602-4fa9-9483-6fe3dba1ffb3",
  "user_email": "compliance.officer@tata.com",
  "action": "ACCEPT",
  "file_name": "Tata_Vendor_Agreement.pdf",
  "comments": "Approved under Procurement Exception Ex-2026."
}

```

#### Response (`200 OK`)

```json
{
  "status": "success",
  "message": "Action ACCEPT logged successfully for document c3c4cb37-3602-4fa9-9483-6fe3dba1ffb3."
}

```

```

```