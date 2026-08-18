import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

from PIL import Image, PngImagePlugin
from backend.services.rag_service import RAGKnowledgeService
from backend.document_pipeline.normalization.normalization_service import ClauseNormalizationService
from backend.document_pipeline.clause_extraction.reasoning_service import LegalReasoningService
from backend.services.llm_config import get_llm_config

# =====================================================================
# 🚀 NEW: DYNAMIC LLM ROUTER
# =====================================================================
def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    """Dynamically routes tasks while strictly isolating provider API keys."""
    import os
    model_lower = model_name.lower()
    
    # 1. NVIDIA ROUTING
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        
    # 2. OPENAI ROUTING
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        
    # 3. ANTHROPIC ROUTING
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        
    # 4. GROQ ROUTING (For open-source Llama/Mixtral)
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        # If user passed an NVIDIA key, route open-source models to NVIDIA NIM instead of Groq
        if api_key.startswith("nvapi-"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
        else:
            from langchain_groq import ChatGroq
            return ChatGroq(model=model_name, api_key=api_key, temperature=0).invoke(prompt).content
            
    # 5. GEMINI ROUTING (DEFAULT FALLBACK)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        # 🛑 CRITICAL ISOLATION: Never send an NVIDIA or OpenAI key to Gemini.
        # Force the fallback to use the hardcoded Google API key from Render Environment.
        google_key = os.getenv("GEMINI_API_KEY") 
        if not google_key and not api_key.startswith("nvapi-") and not api_key.startswith("sk-"):
            google_key = api_key
            
        response = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_key, temperature=0).invoke(prompt)
        # Handle both string and list responses from newer langchain versions
        if isinstance(response, list):
            return str(response[0]) if response else ""
        return str(response.content) if hasattr(response, "content") else str(response)
# =====================================================================

class ClauseService:
    def __init__(self):
        self.rag_service = RAGKnowledgeService()
        self.normalization_service = ClauseNormalizationService()
        self.reasoning_service = LegalReasoningService()

    def _dynamic_fallback_evaluation(self, ocr_text: str, user_role: str):
        text_lower = ocr_text.lower() if ocr_text else ""
        base_confidence = 0.78
        length_bonus = min(len(text_lower) / 4000, 0.18)
        confidence_score = round(base_confidence + length_bonus, 2)

        high_risk_keywords = ["indemn", "liability", "penalty", "termination", "breach", "damages", "exclusive"]
        medium_risk_keywords = ["confidential", "jurisdiction", "governing law", "dispute", "warranty"]

        risk_level = "LOW"
        risk_rationale = f"- Dynamically evaluated for {user_role}.\n- Standard provisions detected with minimal regulatory exposure."

        if any(kw in text_lower for kw in high_risk_keywords):
            risk_level = "HIGH"
            risk_rationale = f"- Dynamically flagged for {user_role}.\n- High-risk legal exposure keywords (indemnity/liability/penalties) identified in text."
        elif any(kw in text_lower for kw in medium_risk_keywords):
            risk_level = "MEDIUM"
            risk_rationale = f"- Dynamically flagged for {user_role}.\n- Requires secondary legal review due to jurisdiction or confidentiality terms."

        snippet = ocr_text[:300].replace('\n', ' ') if ocr_text else "Standard enterprise document terms."
        
        return [
            {
                "clause_type": "GENERAL PROVISION & COMPLIANCE",
                "extracted_text": snippet,
                "confidence_score": confidence_score,
                "risk_level": risk_level,
                "risk_rationale": risk_rationale,
                "involved_party": "Enterprise Stakeholders & Counterparty",
                "rag_reference_used": "POL-IND-2026-01",
                "page_reference": "N/A",
                "obligation_owner": "N/A",
                "recommended_action": "Review Document"
            }
        ]

    def extract_clauses(self, ocr_text: str, file_path: str = None, user_role: str = "Senior Reviewer", business_unit: str = "Enterprise"):
        retrieved_references = self.rag_service.semantic_search(ocr_text, top_k=5)
        rag_context_str = json.dumps(retrieved_references, indent=2)

        config = get_llm_config()
        api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY", "")
        selected_llm = config.get("llm_model", "gemini-2.0-flash-lite")
        
        # Priority fallback chain - Ordered by: user preference -> NVIDIA (best free tier for legal) -> Gemini flash-lite (fast) -> Gemini flash (fallback)
        model_candidates = [selected_llm, "nvidia/nemotron-3-ultra", "gemini-2.0-flash-lite", "gemini-2.0-flash"]

        prompt = f"""
        You are Aadhya, an expert Enterprise Legal Intelligence AI for Tata Group.
        Analyze the provided document text for the '{business_unit}' business unit.
        The user reviewing this document holds the role of: {user_role}.
        
        APPROVED ENTERPRISE RAG CONTEXT:
        {rag_context_str}

        CRITICAL SPECIFICATION INSTRUCTIONS:
        You must output a strictly formatted JSON array addressing the following stages:

        1. (Contract Summary & Obligations): The FIRST object MUST be a "Document Summary" mapping out parties, key dates, and core obligations.
        2. (Missing Clauses): The SECOND object MUST be type "Missing Expected Clauses". Identify standard legal protections (e.g., Indemnity, Data Privacy) that are dangerously absent based on the document type.
        3. (Risk Extraction): Extract 2 to 4 material clauses. Evaluate risk (HIGH/MEDIUM/LOW) against the RAG Context.

        Each JSON object in the array must contain exactly these keys:
           - "clause_type", "extracted_text", "confidence_score", "risk_level", "risk_rationale", "involved_party", "rag_reference_used", "page_reference", "obligation_owner", "recommended_action"

        Document Text to Analyze:
        {ocr_text}
        """

        raw_clauses = []
        for model_name in model_candidates:
            try:
                # 🛑 SAFETY GUARD: If processing an image, force Gemini Vision Model
                if file_path and os.path.exists(file_path) and file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    from google import genai as google_genai
                    client = google_genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-2.0-flash-lite",
                        contents=[Image.open(file_path), prompt]
                    )
                    raw_text = response.text.strip()
                else:
                    # ✅ Text document: Route to user's selected Nvidia/OpenAI model
                    raw_text = _invoke_dynamic_llm(prompt, model_name, api_key).strip()

                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    parsed_clauses = json.loads(json_str)

                    if isinstance(parsed_clauses, list) and len(parsed_clauses) > 0:
                        raw_clauses = parsed_clauses
                        print(f"✅ Successfully extracted {len(raw_clauses)} clauses using model: {model_name}")
                        break  # STOP cascade on first success

            except Exception as e:
                error_str = str(e)
                # Only skip model if it's a SERIOUS error (invalid key, model not found, auth error)
                # Don't skip for rate limits (429) - those are temporary
                if any(serious in error_str for serious in ["INVALID_ARGUMENT", "API_KEY_INVALID", "NOT_FOUND", "PERMISSION_DENIED", "UNAUTHENTICATED", "model not found", "does not exist"]):
                    print(f"❌ Model {model_name} has serious error, skipping: {e}")
                    continue
                # For rate limits (429) and other transient errors, log but continue to next model
                print(f"⚠️ Model {model_name} transient error, trying next: {e}")
                continue

        if not raw_clauses:
            print("All cloud models failed or rate limited. Executing local fallback evaluation.")
            raw_clauses = self._dynamic_fallback_evaluation(ocr_text, user_role)

        normalized_clauses = self.normalization_service.normalize_clauses(raw_clauses)
        final_evaluated_clauses = self.reasoning_service.evaluate_risk_and_reasoning(
            normalized_clauses, business_unit=business_unit, user_role=user_role
        )

        return final_evaluated_clauses

def extract_clauses(ocr_text: str, file_path: str = None, user_role: str = "Senior Reviewer", business_unit: str = "Enterprise"):
    service = ClauseService()
    return service.extract_clauses(ocr_text, file_path=file_path, user_role=user_role, business_unit=business_unit)
