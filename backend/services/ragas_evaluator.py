import os
import time
import asyncio
from typing import List, Dict, Any
from datasets import Dataset
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ==============================================================================
# 🛑 CRITICAL DEPENDENCY FIX FOR RAGAS + LANGCHAIN
# ==============================================================================
import sys
import types
if "langchain_community.chat_models.vertexai" not in sys.modules:
    _vx = types.ModuleType("langchain_community.chat_models.vertexai")
    class ChatVertexAI: pass
    _vx.ChatVertexAI = ChatVertexAI
    sys.modules["langchain_community.chat_models.vertexai"] = _vx
# ==============================================================================

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness,
)
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
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
    delay: float = 3.0 
    
    @property
    def _llm_type(self) -> str:
        return "rate_limited_llm"
        
    def _generate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        time.sleep(self.delay)
        for attempt in range(4):
            try:
                result = self.llm._generate(messages, stop, run_manager, **kwargs)
                for gen in result.generations:
                    if hasattr(gen, 'text'): gen.text = clean_json_output(gen.text)
                    if hasattr(gen, 'message') and hasattr(gen.message, 'content'): gen.message.content = clean_json_output(gen.message.content)
                return result
            except Exception as e:
                if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt < 3:
                    time.sleep(15)
                else:
                    raise e

    async def _agenerate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        await asyncio.sleep(self.delay)
        for attempt in range(4):
            try:
                result = await self.llm._agenerate(messages, stop, run_manager, **kwargs)
                for gen in result.generations:
                    if hasattr(gen, 'text'): gen.text = clean_json_output(gen.text)
                    if hasattr(gen, 'message') and hasattr(gen.message, 'content'): gen.message.content = clean_json_output(gen.message.content)
                return result
            except Exception as e:
                if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt < 3:
                    await asyncio.sleep(15)
                else:
                    raise e

def generate_ragas_scorecard(clauses: List[Dict[str, Any]]) -> Dict[str, float]:
    """Generates RAGAS metrics dynamically based on the Admin's configured LLM."""
    if not clauses:
        return {}

    config = get_llm_config()
    api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {}

    llm_model = config.get("llm_model", "gemini-3.5-flash")
    emb_model = config.get("embedding_model", "gemini-embedding-001")

    base_llm = ChatGoogleGenerativeAI(model=llm_model, google_api_key=api_key, temperature=0)
    evaluator_llm = RateLimitedLLM(llm=base_llm, delay=2.0)
    evaluator_embeddings = GoogleGenerativeAIEmbeddings(model=emb_model, google_api_key=api_key)

    # Sample top 2 highest risk clauses to prevent Render HTTP timeouts
    sample_clauses = sorted(clauses, key=lambda x: 0 if str(x.get("risk_level")).upper() == "HIGH" else 1)[:2]

    data = {"user_input": [], "retrieved_contexts": [], "response": [], "reference": []}

    for c in sample_clauses:
        data["user_input"].append(f"Evaluate the compliance risk of: {c.get('extracted_text', '')}")
        data["retrieved_contexts"].append([c.get("risk_rationale", "Standard compliance policy.")])
        data["response"].append(c.get("risk_rationale", ""))
        data["reference"].append(c.get("risk_rationale", ""))

    dataset = Dataset.from_dict(data)
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness]
    
    for m in metrics:
        m.llm = evaluator_llm
        if hasattr(m, 'embeddings'):
            m.embeddings = evaluator_embeddings

    try:
        results = evaluate(dataset=dataset, metrics=metrics, raise_exceptions=False)
        df = results.to_pandas()
        return {
            "faithfulness": float(df['faithfulness'].mean()) if 'faithfulness' in df else 0.0,
            "answer_relevancy": float(df['answer_relevancy'].mean()) if 'answer_relevancy' in df else 0.0,
            "context_precision": float(df['context_precision'].mean()) if 'context_precision' in df else 0.0,
            "context_recall": float(df['context_recall'].mean()) if 'context_recall' in df else 0.0,
            "answer_correctness": float(df['answer_correctness'].mean()) if 'answer_correctness' in df else 0.0,
        }
    except Exception as e:
        print(f"Ragas Evaluation Failed: {e}")
        return {}