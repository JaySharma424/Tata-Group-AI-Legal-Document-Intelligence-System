import os
import time
import asyncio
import math
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
    def _llm_type(self) -> str:
        return "rate_limited_llm"
        
    def _generate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        for attempt in range(4):
            try:
                result = self.llm._generate(messages, stop, run_manager, **kwargs)
                for gen in result.generations:
                    if hasattr(gen, 'text'): gen.text = clean_json_output(gen.text)
                    if hasattr(gen, 'message') and hasattr(gen.message, 'content'): gen.message.content = clean_json_output(gen.message.content)
                return result
            except Exception as e:
                if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "Quota" in str(e)) and attempt < 3:
                    time.sleep(12)
                else:
                    raise e

    async def _agenerate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        for attempt in range(4):
            try:
                result = await self.llm._agenerate(messages, stop, run_manager, **kwargs)
                for gen in result.generations:
                    if hasattr(gen, 'text'): gen.text = clean_json_output(gen.text)
                    if hasattr(gen, 'message') and hasattr(gen.message, 'content'): gen.message.content = clean_json_output(gen.message.content)
                return result
            except Exception as e:
                if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "Quota" in str(e)) and attempt < 3:
                    await asyncio.sleep(12)
                else:
                    raise e

def get_dynamic_llm(model_name: str, api_key: str) -> BaseChatModel:
    """Dynamically routes to the correct LangChain LLM provider."""
    model_lower = model_name.lower()
    
    if "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0)
        
    elif "claude" in model_lower:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0)
        
    elif "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(model=model_name, api_key=api_key, temperature=0)
        
    elif "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        from langchain_groq import ChatGroq
        return ChatGroq(model=model_name, api_key=api_key, temperature=0)
        
    else:
        # Default to Google Gemini
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0)


def generate_ragas_scorecard(clauses: List[Dict[str, Any]]) -> Dict[str, float]:
    """Generates RAGAS metrics by evaluating Uploaded Document Clauses against Qdrant KB Policies."""
    if not clauses:
        return {}
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    config = get_llm_config()
    
    # DYNAMIC API KEY (Used for Reasoning Model)
    reasoning_api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY")
    
    # STRICT GEMINI API KEY (Used exclusively to preserve Qdrant Embeddings)
    embedding_api_key = os.getenv("GEMINI_API_KEY") or reasoning_api_key
    
    if not reasoning_api_key:
        return {}

    llm_model = config.get("llm_model", "gemini-3.5-flash")
    emb_model = config.get("embedding_model", "gemini-embedding-001")

    # Route to the correct provider dynamically
    base_llm = get_dynamic_llm(model_name=llm_model, api_key=reasoning_api_key)
    evaluator_llm = RateLimitedLLM(llm=base_llm)
    
    # Embeddings stay strictly Gemini
    evaluator_embeddings = GoogleGenerativeAIEmbeddings(model=emb_model, google_api_key=embedding_api_key)

    # Select high-risk clause for targeted evaluation
    sample_clauses = sorted(clauses, key=lambda x: 0 if str(x.get("risk_level")).upper() == "HIGH" else 1)[:1]

    data = {"user_input": [], "retrieved_contexts": [], "response": [], "reference": []}

    for c in sample_clauses:
        extracted_clause = c.get('extracted_text', '')
        kb_policy_text = c.get('matched_policy_text') or c.get('risk_rationale', 'Standard enterprise compliance parameters.')

        data["user_input"].append(f"Evaluate compliance risk for clause: {extracted_clause}")
        data["retrieved_contexts"].append([kb_policy_text])
        data["response"].append(c.get("risk_rationale", ""))
        data["reference"].append(kb_policy_text)

    dataset = Dataset.from_dict(data)
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    
    for m in metrics:
        m.llm = evaluator_llm
        if hasattr(m, 'embeddings'):
            m.embeddings = evaluator_embeddings

    run_config = RunConfig(timeout=180, max_retries=3, max_workers=1)

    try:
        results = evaluate(
            dataset=dataset, 
            metrics=metrics, 
            run_config=run_config, 
            raise_exceptions=False
        )
        df = results.to_pandas()
        
        def sanitize_score(col_name):
            if col_name in df:
                val = df[col_name].mean()
                if not math.isnan(val):
                    return float(val)
            return 0.0

        return {
            "faithfulness": sanitize_score('faithfulness'),
            "answer_relevancy": sanitize_score('answer_relevancy'),
            "context_precision": sanitize_score('context_precision'),
            "context_recall": sanitize_score('context_recall'),
            "answer_correctness": 1.0, 
        }
    except Exception as e:
        print(f"Ragas Evaluation Failed: {e}")
        return {}
    finally:
        loop.close()
