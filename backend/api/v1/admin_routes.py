from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.services.llm_config import get_llm_config, update_llm_config

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
        "llm_model": config.get("llm_model", "gemini-2.0-flash-lite"),
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

# =====================================================================
# 🚀 NEW: DYNAMIC CONNECTION TESTER
# =====================================================================
def _test_dynamic_llm_connection(model_name: str, api_key: str) -> str:
    """Dynamically tests the correct API provider based on the model string."""
    model_lower = model_name.lower()
    test_prompt = "Connection test. Respond exactly with the word: OK"
    
    if "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, max_retries=1).invoke(test_prompt).content
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, max_retries=1).invoke(test_prompt).content
    elif "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(model=model_name, api_key=api_key).invoke(test_prompt).content
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        from langchain_groq import ChatGroq
        return ChatGroq(model=model_name, api_key=api_key).invoke(test_prompt).content
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, max_retries=1).invoke(test_prompt).content

@router.post("/admin/llm-config/test")
async def test_llm_connection(req: LLMConfigRequest):
    """Validates the key and model connectivity directly with the respective AI provider."""
    key = req.api_key if req.api_key else get_llm_config().get("api_key")
    model = req.llm_model if req.llm_model else get_llm_config().get("llm_model", "gemini-2.0-flash-lite")
    
    if not key:
        raise HTTPException(status_code=400, detail="No API Key provided for testing.")
        
    try:
        response_text = _test_dynamic_llm_connection(model, key)
        return {"status": "success", "message": f"Successfully connected to {model}!", "response": response_text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LLM Connection Failed. Verify your API key for {model}: {str(e)}")
