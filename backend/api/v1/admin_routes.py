from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.services.llm_config import get_llm_config, update_llm_config
from google import genai

router = APIRouter()

class LLMConfigRequest(BaseModel):
    api_key: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None

@router.get("/admin/llm-config")
async def get_config():
    config = get_llm_config()
    # Mask API key for security before returning to UI
    raw_key = config.get("api_key", "")
    masked_key = f"{raw_key[:6]}...{raw_key[-4:]}" if len(raw_key) > 10 else "****"
    return {
        "status": "success",
        "llm_model": config.get("llm_model", "gemini-3.5-flash"),
        "embedding_model": config.get("embedding_model", "gemini-embedding-001"),
        "masked_api_key": masked_key,
        "is_configured": bool(raw_key)
    }

@router.post("/admin/llm-config")
async def update_config(req: LLMConfigRequest):
    try:
        updated = update_llm_config(
            new_key=req.api_key,
            llm_model=req.llm_model,
            embedding_model=req.embedding_model
        )
        return {"status": "success", "message": "LLM Settings Updated Successfully!", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update LLM configuration: {str(e)}")

@router.post("/admin/llm-config/test")
async def test_llm_connection(req: LLMConfigRequest):
    """Validates the key and model connectivity directly with Google AI Studio."""
    key = req.api_key if req.api_key else get_llm_config().get("api_key")
    model = req.llm_model if req.llm_model else get_llm_config().get("llm_model", "gemini-3.5-flash")
    
    if not key:
        raise HTTPException(status_code=400, detail="No API Key provided for testing.")
        
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents="Connection test. Respond with OK."
        )
        return {"status": "success", "message": f"Successfully connected to {model}!", "response": response.text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LLM Connection Failed: {str(e)}")