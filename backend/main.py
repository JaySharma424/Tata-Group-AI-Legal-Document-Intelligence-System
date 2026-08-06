from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.v1.router import api_router
from backend.database import engine, Base
from backend import models
from backend.api.v1 import monitoring
from backend.api.v1 import risk_review
from backend.api.v1 import chat
from backend.api.v1 import auth  # IMPORT NEW AUTH ROUTER
import os
from dotenv import load_dotenv

load_dotenv() 

Base.metadata.create_all(bind=engine)  # Issue all DDL statements to create all mapped database tabels if not exist.

app = FastAPI(title="Tata AI Legal Intelligence API", version="1.0.0")

# MOUNT AUTH ROUTER
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

app.include_router(risk_review.router, prefix="/api/v1/risk", tags=["Risk Review & Clause Intelligence"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Monitoring & Telemetry"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],        
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "healthy", "database": "PostgreSQL connected"}