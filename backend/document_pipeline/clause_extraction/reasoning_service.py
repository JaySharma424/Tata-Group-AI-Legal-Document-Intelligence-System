import json
import os
import re
import ast
from typing import Any, Dict, List

from backend.services.llm_config import get_llm_config

def _invoke_dynamic_llm(prompt: str, model_name: str, api_key: str) -> str:
    model_lower = model_name.lower()
    
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        nv_key = api_key if (api_key and api_key.startswith("nvapi-")) else os.getenv("NVIDIA_API_KEY")
        if not nv_key: raise ValueError("API_KEY_INVALID: No valid NVIDIA key found.")
        return ChatNVIDIA(model=model_name, api_key=nv_key, temperature=0, max_tokens=2048).invoke(prompt).content
        
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        sk_key = api_key if (api_key and api_key.startswith("sk-") and not api_key.startswith("sk-ant-")) else os.getenv("OPENAI_API_KEY")
        if not sk_key: raise ValueError("API_KEY_INVALID: No valid OpenAI key found.")
        return ChatOpenAI(model=model_name, api_key=sk_key, temperature=0).invoke(prompt).content
        
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        ant_key = api_key if (api_key and api_key.startswith("sk-ant-")) else os.getenv("ANTHROPIC_API_KEY")
        if not ant_key: raise ValueError("API_KEY_INVALID: No valid Anthropic key found.")
        return ChatAnthropic(model=model_name, api_key=ant_key, temperature=0).invoke(prompt).content
        
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        if api_key and api_key.startswith("nvapi-"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0, max_tokens=2048).invoke(prompt).content
        else:
            from langchain_groq import ChatGroq
            groq_key = api_key if (api_key and api_key.startswith("gsk_")) else os.getenv("GROQ_API_KEY")
            if not groq_key: raise ValueError("API_KEY_INVALID: No valid Groq key found.")
            return ChatGroq(model=model_name, api_key=groq_key, temperature=0).invoke(prompt).content
            
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key and not api_key.startswith("nvapi-") and not api_key.startswith("sk-") and not api_key.startswith("gsk_"):
            gemini_key = api_key
        if not gemini_key: raise ValueError("API_KEY_INVALID: No valid Google key found.")
            
        response = ChatGoogleGenerativeAI(model=model_name, google_api_key=gemini_key, temperature=0).invoke(prompt)
        if isinstance(response, list): return str(response[0]) if response else ""
        return str(response.content) if hasattr(response, "content") else str(response)

def clean_llm_json_response(raw_text: str) -> str:
    """Heals truncated JSON arrays and strips chatty LLM preambles."""
    if not raw_text: return "[]"
    text = str(raw_text).strip()
    
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    
    md_match = re.search(r"```(?:json)?\s*(.*?)\s*
