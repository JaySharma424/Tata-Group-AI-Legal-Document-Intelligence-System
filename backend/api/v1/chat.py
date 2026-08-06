from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from backend.services.rag_service import RAGKnowledgeService
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import DocumentModel, ClauseModel

from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    genai.configure(api_key="AQ.Ab8RN6KD5GRHayVsTygHrv2tpG4XboavUZVw1DKcMp-2hhHgpw")

router = APIRouter()
rag_service = RAGKnowledgeService()

class ChatMessage(BaseModel):
    role: Optional[str] = "user"
    text: Optional[str] = ""

class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default_user"
    document_id: Optional[str] = None
    chat_history: Optional[List[ChatMessage]] = [] 

@router.post("/query")
async def chat_with_legal_rag(payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        user_query = payload.query.strip() if payload.query else ""
        query_lower = user_query.lower()
        
        # 1. Format Chat History Safely
        formatted_history = "No previous context."
        if payload.chat_history:
            history_lines = []
            for msg in payload.chat_history[-5:]:
                role = msg.role if msg.role else 'user'
                text = msg.text if msg.text else ''
                history_lines.append(f"{role.capitalize()}: {text}")
            formatted_history = "\n".join(history_lines)

        # 2. PostgreSQL Lookup: Fetch Active Document & Clause Data
        postgres_context_str = "No document currently loaded in workspace."
        clauses = []
        doc = None
        try:
            if payload.document_id:
                doc = db.query(DocumentModel).filter(DocumentModel.job_id == payload.document_id).first()
                clauses = db.query(ClauseModel).filter(ClauseModel.job_id == payload.document_id).all()
            
            if not doc:
                doc = db.query(DocumentModel).order_by(DocumentModel.created_at.desc()).first()
                if doc:
                    clauses = db.query(ClauseModel).filter(ClauseModel.job_id == doc.job_id).all()

            if doc:
                postgres_context_str = f"""
--- POSTGRESQL ACTIVE WORKSPACE DATA ---
Filename: {doc.filename}
Business Unit: {doc.business_unit}
"""
            if clauses:
                postgres_context_str += "\nExtracted Clauses & PostgreSQL Records:\n"
                for idx, c in enumerate(clauses, start=1):
                    postgres_context_str += f"[{idx}] Clause: {c.clause_type} (Risk: {c.risk_level})\n    Text: {c.extracted_text}\n    Rationale: {c.risk_rationale}\n\n"
        except Exception as db_error:
            print(f"PostgreSQL Fetch Error in Chat: {db_error}")

        # 3. Vector DB Lookup: Fetch RAG Corporate Policies & Guidelines
        rag_context_str = "No specific corporate policies matched."
        references = []
        try:
            references = rag_service.retrieve_context(user_query)
            if references:
                rag_context_str = "\n".join([f"- [{r.get('ref', 'REF')}]: {r.get('text', '')}" for r in references])
        except Exception as rag_error:
            print(f"Vector DB RAG Fetch Error: {rag_error}")

        # 4. Enterprise Human-Like Prompt with Multi-Source Routing & Domain Boundaries
        prompt = f"""
You are Aadhya, an expert, empathetic, and authoritative Enterprise Legal AI Counsel representing the Tata Group.

ENTERPRISE ROUTING & BEHAVIORAL GUIDELINES:
1. OUT-OF-DOMAIN FILTER (General World Questions): If the user's query is completely unrelated to law, risk, contracts, company policies, corporate governance, or the workspace document (e.g., asking about weather, sports, general knowledge, math trivia), you must politely decline and state: "I am Aadhya, your Tata Legal Assistant. I specialize exclusively in enterprise contract review, document analysis, and corporate compliance. How can I assist you with your legal documents today?"
2. POSTGRESQL WORKSPACE PRIORITY: If the query asks about the specific contents, corporate governance, clauses, liabilities, or risks of the uploaded contract, look directly into the PostgreSQL workspace data provided below.
3. VECTOR DB RAG POLICY ROUTING: If the query asks about general Tata compliance rules, confidentiality standards, liability caps, risk, corporate governance, or legal guidelines, integrate the retrieved Vector DB policies below.
4. HUMAN-LIKE TONE: Respond with the poise and professionalism of senior corporate counsel. Be precise, structured, and clear. 
5. USER-REQUIREMENT: If, user want to answer in perticular words, lines , sentence answer with the refrence of uploded doc only with the  help of risk_taxonomy.csv or document prsent in knowledge base.


Recent Conversation:
{formatted_history}

{postgres_context_str}

VECTOR DB CORPORATE POLICIES (QDRANT):
{rag_context_str}

User Query: {user_query}
"""

        # 5. Call Gemini with Model Fallbacks
        model_candidates = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        answer = None

        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    answer = response.text.strip().replace("###", "")
                    break
            except Exception as e:
                print(f"Model {model_name} failed: {e}")
                continue

        # 6. Intelligent Local Fallback (If API rate-limits)
        if not answer:
            # General world check
            general_triggers = ["weather", "sports", "cricket", "movie", "recipe", "capital of", "who won", "world"]
            if any(t in query_lower for t in general_triggers):
                answer = "I am Aadhya, your Tata Legal Assistant. I specialize exclusively in enterprise contract review, document analysis, and corporate compliance. How can I assist you with your legal documents today?"
            elif doc and clauses:
                matched_clause = next((c for c in clauses if any(w in c.extracted_text.lower() or w in c.clause_type.lower() for w in query_lower.split() if len(w) > 3)), None)
                if matched_clause:
                    answer = f"Based on the active document **{doc.filename}** (Clause: *{matched_clause.clause_type}*):\n\n> \"{matched_clause.extracted_text}\"\n\n**Compliance Rationale:** {matched_clause.risk_rationale}"
                else:
                    answer = f"I've analyzed your active workspace document **{doc.filename}**. You can ask me about specific clauses like liability, payment terms, or confidentiality, and I will cross-reference them with our corporate policies."
            else:
                answer = "Hello! I am Aadhya, your Tata Legal Assistant. Please select or upload a document in your workspace so I can assist you."

        return {
            "answer": answer,
            "references": references
        }
        
    except Exception as e:
        print(f"Chat endpoint critical error: {e}")
        return {
            "answer": "I am Aadhya, your Legal Assistant. I am reviewing your query against our enterprise database and vector policies.",
            "references": []
        }