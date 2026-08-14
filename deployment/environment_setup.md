# ⚙️ Local Environment & Development Setup Guide

This guide provides instructions for setting up the **Tata AI Legal Intelligence System** on a local development workstation.

---

## 📋 Prerequisites

Ensure the following tools are installed on your system:
* **Python 3.11 or 3.12**
* **Node.js 18+ & npm**
* **Docker & Docker Compose** (Optional, for containerized local setup)
* **Git**

---

## 🚀 Quick Setup Option 1: Docker Compose (Recommended)

Spins up PostgreSQL, FastAPI Backend, and React Frontend in isolated local containers.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System.git](https://github.com/JaySharma424/Tata-Group-AI-Legal-Document-Intelligence-System.git)
   cd Tata-Group-AI-Legal-Document-Intelligence-System
Configure local environment variables:Bashcp .env.example .env
Add your GEMINI_API_KEY into .env.Start the containers:Bashdocker-compose up -d --build
Access local services:Frontend: http://localhost:5173Backend API / Docs: http://localhost:8000/docs💻 Manual Setup Option 2: Native Workstation SetupStep 1: Environment Variables SetupCreate a .env file in the root directory:Code snippetDATABASE_URL=postgresql://postgres:YourPassword@localhost:5432/tata_ai_legal
SECRET_KEY=your_secure_development_jwt_secret_key
GEMINI_API_KEY=your_gemini_api_key_here
VITE_API_BASE_URL=http://localhost:8000
Step 2: Backend Setup (Python)Navigate to root and create a virtual environment:Bashpython -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
Install dependencies:Bashpip install --upgrade pip
pip install -r backend/requirements.txt
Download required spaCy NLP model:Bashpython -m spacy download en_core_web_sm
Launch FastAPI development server:Bashuvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
Step 3: Frontend Setup (React + Vite)Open a new terminal and navigate to the frontend/ directory:Bashcd frontend
npm install
Start Vite development server:Bashnpm run dev
Frontend will run at http://localhost:5173.🔑 Key Environment Variables ReferenceVariableDescriptionDefault Local ValueDATABASE_URLPostgreSQL Connection URI  postgresql://postgres:1234@localhost:5432/tata_ai_legalSECRET_KEYSecret key for JWT Bearer token generationCustom StringGEMINI_API_KEYGoogle AI Studio Key for RAG & Clause Extraction  User KeyVITE_API_BASE_URLBase API URL used by frontend Axios instancehttp://localhost:8000
