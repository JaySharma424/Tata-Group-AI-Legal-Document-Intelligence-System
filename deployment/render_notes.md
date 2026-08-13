# 🎨 Render Frontend Deployment Notes: Tata AI Legal Intelligence

This document outlines the deployment configuration, single-page application (SPA) rewrite rules, and API integration settings for hosting the React frontend as a **Static Site on Render**.

---

## 🌟 Overview & Advantages

In this system architecture, the React SPA frontend is hosted directly on Render alongside the FastAPI web service and PostgreSQL database. This unified setup provides:

* **Unified Dashboard Governance:** Manage frontend, backend, and database resources within a single platform region.
* **Blueprint Infrastructure Automation:** Zero-touch provisioning via root-level `render.yaml` Blueprint.
* **Automated SSL & Global CDN:** Free managed SSL certificates and fast edge delivery provided out of the box by Render.

---

## ⚙️ Render Static Site Configuration

### 1. Render Blueprint Specification (`render.yaml`)
When deployed via Render Blueprint or created manually, the static site uses the following parameters:

| Setting | Value | Description |
| :--- | :--- | :--- |
| **Service Type** | Static Site (`web` runtime: `static`) | Hosted as compiled static web assets served over CDN |
| **Name** | `tata-ai-frontend` | Service name identifier in Render |
| **Build Command** | `cd frontend && npm install && npm run build` | Installs Node packages and executes Vite production build |
| **Publish Directory** | `./frontend/dist` | Directory containing built static output (`dist/`) |

### 2. Environment Variables Configuration
Configure the following environment variable in the Render Dashboard under **Static Site Settings**:

| Variable Name | Value / Example | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://tata-ai-backend-og7t.onrender.com` | Production URL of FastAPI backend used by Axios requests |

---

## 🔄 Client-Side SPA Rewrite Rules (React Router)

Because the application uses client-side routing (React Router), refreshing the browser on direct application sub-paths (e.g., `/admin` or `/workspace`) will cause a `404 Not Found` error unless Render is instructed to route all incoming HTTP requests to `index.html`.

### How to Configure Rewrites on Render:
1. Go to the **Render Dashboard** and select your **`tata-ai-frontend`** Static Site.
2. Navigate to **Redirects / Rewrites** in the left sidebar menu.
3. Add a new rule with the following parameters:
   * **Source:** `/*`
   * **Destination:** `/index.html`
   * **Action:** `Rewrite` (200 Status Code)

*(Note: When deploying locally or via containerized Nginx Docker builds, this behavior is handled by `try_files $uri $uri/ /index.html;` in Nginx configuration).*

---

## 🔒 Cross-Origin Resource Sharing (CORS) Alignment

To guarantee uninterrupted communication between `tata-ai-frontend.onrender.com` and `tata-ai-backend.onrender.com`, ensure the production frontend domain is whitelisted in `backend/main.py`:

```python
allowed_origins = [
    "[https://tata-ai-frontend.onrender.com](https://tata-ai-frontend.onrender.com)",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.onrender\.com", # Auto-matches Render staging/preview domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
🚀 Pre-Deployment Verification Checklist[ ] render.yaml specifies ./frontend/dist as staticPublishPath.[ ] Environment variable VITE_API_BASE_URL points to live Render backend endpoint.[ ] FastAPI CORS middleware includes https://tata-ai-frontend.onrender.com.[ ] Client-side rewrite rule (/* $\rightarrow$ /index.html) is added under Render Static Site settings.
