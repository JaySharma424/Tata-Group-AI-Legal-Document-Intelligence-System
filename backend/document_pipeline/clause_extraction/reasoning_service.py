import os
import google.generativeai as genai
from typing import List, Dict, Any

class LegalReasoningService:
    """Executes a dedicated legal reasoning and risk flagging pass using Gemini and RAG context."""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

    def evaluate_risk_and_reasoning(self, normalized_clauses: List[Dict[str, Any]], business_unit: str, user_role: str) -> List[Dict[str, Any]]:
        """Applies rigorous legal reasoning to normalized clauses based on corporate compliance policies."""
        evaluated_clauses = []
        
        model_candidates = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash","gemini-3.5-flash"]
        model = None
        for m_name in model_candidates:
            try:
                model = genai.GenerativeModel(m_name)
                break
            except Exception:
                continue

        for clause in normalized_clauses:
            if not model:
                # Fallback if AI model is unavailable
                evaluated_clauses.append(clause)
                continue

            prompt = f"""
            You are a Senior Legal Counsel at Tata Group evaluating contracts for the '{business_unit}' business unit under the review perspective of a '{user_role}'.
            
            Analyze the following normalized clause:
            - Clause Type: {clause['clause_type']}
            - Extracted Text: {clause['extracted_text']}
            
            Perform a rigorous legal reasoning evaluation:
            1. Determine the risk level strictly as one of: HIGH, MEDIUM, or LOW.
            2. Provide a professional legal rationale explaining exposure, liability, or compliance alignment.
            3. Specify the appropriate RAG policy reference ID (e.g., POL-IND-2026-01).
            
            Return ONLY a valid JSON object with keys: "risk_level", "risk_rationale", "rag_reference_used", "recommended_action".
            """
            
            try:
                response = model.generate_content(prompt)
                text_res = response.text.strip()
                # Clean markdown code blocks if returned
                if text_res.startswith("```json"):
                    text_res = text_res[7:]
                if text_res.endswith("```"):
                    text_res = text_res[:-3]
                
                import json
                parsed_eval = json.loads(text_res.strip())
                
                clause["risk_level"] = parsed_eval.get("risk_level", clause["risk_level"])
                clause["risk_rationale"] = parsed_eval.get("risk_rationale", clause["risk_rationale"])
                clause["rag_reference_used"] = parsed_eval.get("rag_reference_used", clause["rag_reference_used"])
                clause["recommended_action"] = parsed_eval.get("recommended_action", clause["recommended_action"])
            except Exception as e:
                print(f"Legal reasoning evaluation fallback triggered: {e}")

            evaluated_clauses.append(clause)
            
        return evaluated_clauses