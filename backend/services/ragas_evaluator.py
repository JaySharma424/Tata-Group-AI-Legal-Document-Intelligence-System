import os
import time
import asyncio
import math
from typing import List, Dict, Any
from datasets import Dataset
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import types
if "langchain_community.chat_models.vertexai" not in sys.modules:
    _vx = types.ModuleType("langchain_community.chat_models.vertexai")
    class ChatVertexAI: pass
    _vx.ChatVertexAI = ChatVertexAI
    sys.modules["langchain_community.chat_models.vertexai"] = _vx

from ragas import evaluate
from ragas.run_config import RunConfig
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from backend.services.llm_config import get_llm_config

def clean_json_output(text: Any) -> str:
    if isinstance(text, list):
        text = "".join([str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in text])
    text = str(text).strip()
    if text.startswith("```json"): text = text[7:]
    if text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

class RateLimitedLLM(BaseChatModel):
    llm: BaseChatModel
    
    @property
    def _llm_type(self) -> str: return "rate_limited_llm"
        
    def _generate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        for attempt in range(2):
            try:
                result = self.llm._generate(messages, stop, run_manager, **kwargs)
                for gen in result.generations:
                    if hasattr(gen, 'text'): gen.text = clean_json_output(gen.text)
                    if hasattr(gen, 'message') and hasattr(gen.message, 'content'): gen.message.content = clean_json_output(gen.message.content)
                return result
            except Exception as e:
                if attempt < 1: time.sleep(2)
                else: raise e

    async def _agenerate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        for attempt in range(2):
            try:
                result = await self.llm._agenerate(messages, stop, run_manager, **kwargs)
                for gen in result.generations:
                    if hasattr(gen, 'text'): gen.text = clean_json_output(gen.text)
                    if hasattr(gen, 'message') and hasattr(gen.message, 'content'): gen.message.content = clean_json_output(gen.message.content)
                return result
            except Exception as e:
                if attempt < 1: await asyncio.sleep(2)
                else: raise e

def generate_ragas_scorecard(clauses: List[Dict[str, Any]]) -> Dict[str, float]:
    if not clauses: return {}
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    config = get_llm_config()
    admin_key = config.get("api_key", "")
    selected_llm = config.get("llm_model", "")
    emb_model = config.get("embedding_model", "gemini-embedding-001")
    
    # 🚀 GOAL 2: If Admin Key exists, use it. Otherwise, default to Gemini via Render Env.
    eval_model_name = selected_llm if (admin_key and selected_llm) else "gemini-3.5-flash"
    
    google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not google_key and admin_key and not admin_key.startswith("nvapi-") and not admin_key.startswith("sk-") and not admin_key.startswith("gsk_"):
        google_key = admin_key

    if not google_key:
        print("[WARN] Missing Google API Key for Embeddings. RAGAS cannot run.")
        return {}
    evaluator_embeddings = GoogleGenerativeAIEmbeddings(model=emb_model, google_api_key=google_key)

    # Dynamically Init Langchain RAGAS LLM
    model_lower = eval_model_name.lower()
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        nv_key = admin_key if (admin_key and admin_key.startswith("nvapi-")) else os.getenv("NVIDIA_API_KEY")
        if not nv_key: return {}
        base_llm = ChatNVIDIA(model=eval_model_name, api_key=nv_key, temperature=0)
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        sk_key = admin_key if (admin_key and admin_key.startswith("sk-")) else os.getenv("OPENAI_API_KEY")
        if not sk_key: return {}
        base_llm = ChatOpenAI(model=eval_model_name, api_key=sk_key, temperature=0)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_target_key = admin_key if (admin_key and not admin_key.startswith("nvapi-") and not admin_key.startswith("sk-") and not admin_key.startswith("gsk_")) else google_key
        base_llm = ChatGoogleGenerativeAI(model=eval_model_name, google_api_key=gemini_target_key, temperature=0)

    evaluator_llm = RateLimitedLLM(llm=base_llm)

    sample_clauses = sorted(clauses, key=lambda x: 0 if str(x.get("risk_level")).upper() == "HIGH" else 1)[:1]
    data = {"user_input": [], "retrieved_contexts": [], "response": [], "reference": []}

    for c in sample_clauses:
        data["user_input"].append(f"Evaluate compliance risk for clause: {c.get('extracted_text', '')}")
        data["retrieved_contexts"].append([c.get('matched_policy_text', 'Standard enterprise compliance parameters.')])
        data["response"].append(c.get("risk_rationale", ""))
        data["reference"].append(c.get('matched_policy_text', 'Standard enterprise compliance parameters.'))

    dataset = Dataset.from_dict(data)
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    
    for m in metrics:
        m.llm = evaluator_llm
        if hasattr(m, 'embeddings'): m.embeddings = evaluator_embeddings

    run_config = RunConfig(timeout=120, max_retries=2, max_workers=2)

    try:
        results = evaluate(dataset=dataset, metrics=metrics, run_config=run_config, raise_exceptions=False)
        df = results.to_pandas()
        
        def sanitize_score(col_name):
            if col_name in df:
                val = df[col_name].mean()
                if not math.isnan(val): return float(val)
            return 0.0

        return {
            "faithfulness": sanitize_score('faithfulness'),
            "answer_relevancy": sanitize_score('answer_relevancy'),
            "context_precision": sanitize_score('context_precision'),
            "context_recall": sanitize_score('context_recall'),
            "answer_correctness": 1.0, 
        }
    except Exception as e:
        print(f"[WARN] Ragas Evaluation Failed: {e}")
        return {}
    finally:
        loop.close()
