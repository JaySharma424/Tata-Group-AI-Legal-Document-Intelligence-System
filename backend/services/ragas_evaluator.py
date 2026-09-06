import os
import re
import math
import asyncio
from typing import List, Dict, Any
from datasets import Dataset
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

def clean_json_output(raw_text: Any) -> str:
    text = str(raw_text).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    md_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if md_match:
        text = md_match.group(1).strip()
        
    idx_list = text.find('[')
    idx_dict = text.find('{')
    if idx_list == -1 and idx_dict == -1:
        return text
    start_idx = min(i for i in (idx_dict, idx_list) if i != -1)
    text = text[start_idx:]

    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    text += ('}' * max(0, open_braces)) + (']' * max(0, open_brackets))
    return text

class RateLimitedLLM(BaseChatModel):
    llm: BaseChatModel
    
    @property
    def _llm_type(self) -> str:
        return "rate_limited_llm"
        
    def _generate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        result = self.llm._generate(messages, stop, run_manager, **kwargs)
        for gen in result.generations:
            if hasattr(gen, 'text'):
                gen.text = clean_json_output(gen.text)
            if hasattr(gen, 'message') and hasattr(gen.message, 'content'):
                gen.message.content = clean_json_output(gen.message.content)
        return result

    async def _agenerate(self, messages: List[BaseMessage], stop: List[str] | None = None, run_manager: Any | None = None, **kwargs: Any) -> ChatResult:
        result = await self.llm._agenerate(messages, stop, run_manager, **kwargs)
        for gen in result.generations:
            if hasattr(gen, 'text'):
                gen.text = clean_json_output(gen.text)
            if hasattr(gen, 'message') and hasattr(gen.message, 'content'):
                gen.message.content = clean_json_output(gen.message.content)
        return result

def generate_ragas_scorecard(clauses: List[Dict[str, Any]]) -> Dict[str, float]:
    if not clauses:
        return {}

    config = get_llm_config()
    google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    eval_model_name = config.get("llm_model", os.getenv("RAGAS_LLM_MODEL", "gemini-1.5-flash"))
    emb_model = config.get("embedding_model", os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"))

    if not google_key:
        print("[WARN] Google API key missing. RAGAS evaluation bypassed.")
        return {}

    evaluator_embeddings = GoogleGenerativeAIEmbeddings(model=emb_model, google_api_key=google_key)

    model_lower = eval_model_name.lower()
    if "nvidia" in model_lower or "nemotron" in model_lower:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        base_llm = ChatNVIDIA(model=eval_model_name, api_key=config.get("api_key", ""), temperature=0)
    elif "gpt" in model_lower:
        from langchain_openai import ChatOpenAI
        base_llm = ChatOpenAI(model=eval_model_name, api_key=config.get("api_key", ""), temperature=0)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        base_llm = ChatGoogleGenerativeAI(model=eval_model_name, google_api_key=google_key, temperature=0)

    evaluator_llm = RateLimitedLLM(llm=base_llm)
    sample_clauses = sorted(clauses, key=lambda x: 0 if str(x.get("risk_level")).upper() == "HIGH" else 1)[:3]

    data = {
        "user_input": [f"Evaluate compliance risk for: {c.get('extracted_text', '')}" for c in sample_clauses],
        "retrieved_contexts": [[c.get('matched_policy_text', '')] for c in sample_clauses],
        "response": [c.get("risk_rationale", "") for c in sample_clauses],
        "reference": [c.get('matched_policy_text', '') for c in sample_clauses]
    }

    dataset = Dataset.from_dict(data)
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    
    for m in metrics:
        m.llm = evaluator_llm
        if hasattr(m, 'embeddings'):
            m.embeddings = evaluator_embeddings

    run_config = RunConfig(timeout=90, max_retries=2, max_workers=2)

    try:
        results = evaluate(dataset=dataset, metrics=metrics, run_config=run_config, raise_exceptions=False)
        df = results.to_pandas()

        def compute_mean(metric_col: str) -> float:
            if metric_col in df and not math.isnan(df[metric_col].mean()):
                return round(float(df[metric_col].mean()), 4)
            return 0.0

        return {
            "faithfulness": compute_mean('faithfulness'),
            "answer_relevancy": compute_mean('answer_relevancy'),
            "context_precision": compute_mean('context_precision'),
            "context_recall": compute_mean('context_recall')
        }
    except Exception as e:
        print(f"[WARN] Evaluation failed: {e}")
        return {}