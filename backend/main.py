from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv
from sqlalchemy import text
from backend.database import engine, Base
from backend import models
from backend.api.v1.router import api_router

load_dotenv() 

# Issue all DDL statements to create mapped database tables if they do not exist
Base.metadata.create_all(bind=engine)

def ensure_database_schema_upgrades():
    """Automatically adds missing columns to live PostgreSQL tables without manual migrations."""
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                ALTER TABLE extracted_clauses 
                ADD COLUMN IF NOT EXISTS proposed_redline TEXT;
            """))
            connection.execute(text("""
                ALTER TABLE extracted_clauses 
                ADD COLUMN IF NOT EXISTS rag_reference_used VARCHAR(255) DEFAULT 'POL-IND-2026-01';
            """))
            print("✅ Database schema verified: 'proposed_redline' and 'rag_reference_used' columns exist.")
    except Exception as e:
        print(f"⚠️ Schema migration notice: {e}")

ensure_database_schema_upgrades()

app = FastAPI(title="Tata AI Legal Intelligence API", version="1.0.0")

# -------------------------------------------------------------------------
# HEALTH CHECK (Supports both GET and HEAD for Render orchestrator)
# -------------------------------------------------------------------------
@app.get("/")
@app.head("/")
async def health_check():
    """Unauthenticated health check for Render deployment."""
    return {"status": "healthy", "service": "tata-ai-backend", "version": "v2-async"}

# -------------------------------------------------------------------------
# CORS CONFIGURATION
# -------------------------------------------------------------------------
allowed_origins = [
    "https://tata-ai-frontend.onrender.com",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

allow_origin_regex = r"https://([a-zA-Z0-9-]+\.)*onrender\.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Global Exception Handler to guarantee CORS headers on 500 errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled Exception: {exc}", exc_info=True)
    origin = request.headers.get("origin", "https://tata-ai-frontend.onrender.com")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": origin if origin in allowed_origins or "onrender.com" in origin else allowed_origins[0],
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        }
    )

# -------------------------------------------------------------------------
# CENTRALIZED API GATEWAY MOUNTING
# -------------------------------------------------------------------------
app.include_router(api_router, prefix="/api/v1")