from fastapi import APIRouter
from . import documents, governance, auth, chat, review, monitoring, risk_review, knowledge_base #, summary_api

api_router = APIRouter()

# Register all modular routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents & Pipeline"])
api_router.include_router(review.router, prefix="/review", tags=["Review & Governance"])
api_router.include_router(governance.router, prefix="/governance", tags=["Governance Operations"])
api_router.include_router(chat.router, prefix="/chat", tags=["Aadhya Legal Chat Assistant"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Legal Operations Telemetry"])
api_router.include_router(risk_review.router, prefix="/risk", tags=["Risk Review & Clause Intelligence"])
api_router.include_router(knowledge_base.router, prefix="/kb", tags=["Knowledge Base & Policies"])
# api_router.include_router(summary_api.router, prefix="/summary", tags=["Executive Summary"])
