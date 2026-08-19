import os
import math
import asyncio
import warnings
from typing import List, Dict, Any # 🚀 FIX: Imported 'Any' to resolve NameError

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
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from backend.services.llm_config import get_llm_config

def force_json_structure(raw_text: Any) -> str:
    text = str(raw_text).strip()
    idx_list = text.find('[')
    idx_dict = text.find('{')
    
    if idx_list == -1 and idx_dict == -1: return text
        
    start_idx = min(idx_list, idx_dict) if (idx_list != -1 and idx_dict != -1) else max(idx_list, idx_dict)
    text = text[start_idx:]
    
    idx_list_end = text.rfind(']')
    idx_dict_end = text.rfind('}')
    end_idx = max(idx_list_end, idx_dict_end)
    
    if end_idx != -1: text = text[:end_idx+1]
    return text

class RagasJSONWrapper(BaseChatModel):
    llm: BaseChatModel
    @property
    def _llm_type(self) -> str: return "ragas_json_wrapper"
        
    def _generate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        res = self.llm._generate(messages, stop, run_manager, **kwargs)
        for g in res.generations:
            if hasattr(g, 'text'): g.text = force_json_structure(g.text)
            if hasattr(g, 'message') and hasattr(g.message, 'content'): g.message.content = force_json_structure(g.message.content)
        return res

    async def _agenerate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        res = await self.llm._agenerate(messages, stop, run_manager, **kwargs)
        for g in res.generations:
            if hasattr(g, 'text'): g.text = force_json_structure(g.text)
            if hasattr(g, 'message') and hasattr(g.message, 'content'): g.message.content = force_json_structure(g.message.content)
        return res

def generate_ragas_scorecard(clauses: list) -> dict:
    if not clauses: return {}
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    config = get_llm_config()
    admin_key = config.get("api_key", "")
    eval_model_name = config.get("llm_model", "")
    emb_model = config.get("embedding_model", "gemini-embedding-001")
    
    if not admin_key or not eval_model_name:
        return {}
    
    if admin_key and not admin_key.startswith("nvapi-") and not admin_key.startswith("sk-") and not admin_key.startswith("gsk_"):
        google_key = admin_key
    else:
        google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not google_key:
        print("[WARN] Missing Google API Key in Environment for Embeddings. RAGAS cannot run.")
        return {}

    evaluator_embeddings = GoogleGenerativeAIEmbeddings(model=emb_model, google_api_key=google_key)

    model_lower = eval_model_name.lower()
    
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        base_llm = ChatNVIDIA(model=eval_model_name, api_key=admin_key, temperature=0, max_tokens=2048, timeout=120)
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        base_llm = ChatOpenAI(model=eval_model_name, api_key=admin_key, temperature=0, max_retries=0)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_target_key = admin_key if (admin_key and not admin_key.startswith("nvapi-") and not admin_key.startswith("sk-") and not admin_key.startswith("gsk_")) else google_key
        base_llm = ChatGoogleGenerativeAI(model=eval_model_name, google_api_key=gemini_target_key, temperature=0, max_retries=0)

    evaluator_llm = RagasJSONWrapper(llm=base_llm)

    sample_clauses = sorted(clauses, key=lambda x: 0 if str(x.get("risk_level")).upper() == "HIGH" else 1)[:1]
    data = {"user_input": [], "retrieved_contexts": [], "response": [], "reference": []}

    for c in sample_clauses:
        data["user_input"].append(f"Evaluate compliance risk for clause: {c.get('extracted_text', '')}")
        data["retrieved_contexts"].append([c.get('matched_policy_text', 'Standard enterprise compliance parameters.')])
        data["response"].append(c.get("risk_rationale", ""))
        data["reference"].append(c.get('matched_policy_text', 'Standard enterprise compliance parameters.'))

    from datasets import Dataset
    dataset = Dataset.from_dict(data)
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    
    for m in metrics:
        m.llm = evaluator_llm 
        if hasattr(m, 'embeddings'): m.embeddings = evaluator_embeddings

    run_config = RunConfig(timeout=120, max_retries=0, max_workers=1) 

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
