# 🚀 Backend Deployment Guide: Tata AI Legal Intelligence

This guide details the steps required to deploy the FastAPI backend and PostgreSQL database to **Render** (or any cloud container platform).

---

## 🏗️ Architecture Overview

* **Framework:** FastAPI (`uvicorn` ASGI Server)[cite: 27, 57]
* **Python Runtime:** Python 3.12
* **Database:** Managed PostgreSQL 15 (SQLAlchemy ORM)[cite: 25, 28, 53, 57]
* **Vector Engine:** Qdrant Vector Store (In-Memory / Persistent Storage)[cite: 1]
* **AI Orchestration:** LangGraph State Graph & Gemini Multimodal LLM Cascade[cite: 1, 20]

---

## 🛠️ Option A: Automatic Deployment via Render Blueprint (`render.yaml`)

The repository includes a root-level `render.yaml` specification that automates provisioning.

### Deployment Steps:
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Blueprint**.
3. Connect your GitHub Repository: `https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System`.
4. Render will auto-detect `render.yaml` and provision:
   * `tata-ai-backend` (Web Service)
   * `tata-ai-db` (PostgreSQL Instance)
   * `tata-ai-frontend` (Static Site)[cite: 57]
5. Set `GEMINI_API_KEY` under Environment Variables in the Render Dashboard[cite: 57].

---

## 🔧 Option B: Manual Web Service Setup on Render

If creating the web service manually:

| Setting | Value |
| :--- | :--- |
| **Service Type** | Web Service[cite: 57] |
| **Runtime** | Python 3.12[cite: 57] |
| **Region** | Singapore (or closest to DB)[cite: 57] |
| **Build Command** | `pip install -r backend/requirements.txt && python -m spacy download en_core_web_sm`[cite: 57] |
| **Start Command** | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1`[cite: 57] |

### Required Environment Variables
* `DATABASE_URL`: `postgresql://<user>:<password>@<host>/<database>`[cite: 57]
* `GEMINI_API_KEY`: Your Google AI Studio API key[cite: 57]
* `SECRET_KEY`: A secure 32+ character string for JWT encoding
* `PYTHON_VERSION`: `3.12.0`[cite: 57]

---

## 🌐 CORS Hardening & Gateway Configuration

The FastAPI entry point (`backend/main.py`) enforces strict CORS origin checks:

```python
allowed_origins = [
    "[https://tata-ai-frontend.onrender.com](https://tata-ai-frontend.onrender.com)",
    "http://localhost:5173",
    "http://localhost:3000"
]
Note: Any new frontend domain (e.g., custom domains or Vercel URLs) must be added to allowed_origins or matched via the origin regex https://.*\.onrender\.com in backend/main.py.  🧪 Post-Deployment VerificationVerify deployment health by querying the root check endpoint:  Bashcurl -X GET [https://your-backend-name.onrender.com/](https://your-backend-name.onrender.com/)
# Response: {"status": "healthy", "database": "Connected"}
Access interactive OpenAPI documentation at https://your-backend-name.onrender.com/docs.
