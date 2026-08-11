import os
import json
import time
import re
import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv

# ==============================================================================
# 🛑 CRITICAL DEPENDENCY FIX FOR RAGAS + LANGCHAIN v1.0+
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
from ragas.run_config import RunConfig

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from typing import Any

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY environment variable is missing!")


# --- 1. DYNAMIC MODEL FALLBACK SELECTION ---
print("🔍 Discovering available Gemini models...")

llm_candidates = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite" "gemini-2.0-flash", "gemini-3.6-flash"]
base_llm = None

for model_name in llm_candidates:
    try:
        print(f"🔄 Testing LLM: {model_name}...")
        test_llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GEMINI_API_KEY,
            temperature=0,
            max_retries=3
        )
        test_llm.invoke("Test") 
        base_llm = test_llm
        print(f"✅ Successfully locked LLM: {model_name}")
        break
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            print(f"⚠️ Hit rate limit on {model_name} during test. Selecting it anyway.")
            base_llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=GEMINI_API_KEY, temperature=0, max_retries=10)
            break
        print(f"❌ LLM {model_name} failed: {err_msg}")
        time.sleep(1)

if not base_llm:
    raise RuntimeError("Could not find a working Gemini LLM model.")

embedding_candidates = ["gemini-embedding-001", "gemini-embedding-2-preview", "models/embedding-001"]
evaluator_embeddings = None

for model_name in embedding_candidates:
    try:
        print(f"🔄 Testing Embeddings: {model_name}...")
        test_emb = GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=GEMINI_API_KEY
        )
        test_emb.embed_query("Test")
        evaluator_embeddings = test_emb
        print(f"✅ Successfully locked Embeddings: {model_name}")
        break
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            print(f"⚠️ Hit rate limit on {model_name} during test. Selecting it anyway.")
            evaluator_embeddings = GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=GEMINI_API_KEY)
            break
        print(f"❌ Embedding {model_name} failed: {err_msg}")
        time.sleep(1)

if not evaluator_embeddings:
    raise RuntimeError("Could not find a working Gemini Embedding model.")


# --- 2. RATE LIMIT & JSON CLEANING WRAPPER ---
def clean_json_output(text: str) -> str:
    """Strips markdown formatting from JSON output so Ragas (Pydantic) doesn't crash."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

class RateLimitedLLM(BaseChatModel):
    llm: BaseChatModel
    delay: float = 4.0 
    
    @property
    def _llm_type(self) -> str:
        return "rate_limited_llm"
        
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        time.sleep(self.delay) 
        result = self.llm._generate(messages, stop, run_manager, **kwargs)
        # CRITICAL FIX: Clean the JSON before handing it back to Ragas
        for gen in result.generations:
            gen.text = clean_json_output(gen.text)
            gen.message.content = clean_json_output(gen.message.content)
        return result
        
    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        import asyncio
        await asyncio.sleep(self.delay) 
        result = await self.llm._agenerate(messages, stop, run_manager, **kwargs)
        # CRITICAL FIX: Clean the JSON before handing it back to Ragas
        for gen in result.generations:
            gen.text = clean_json_output(gen.text)
            gen.message.content = clean_json_output(gen.message.content)
        return result

evaluator_llm = RateLimitedLLM(llm=base_llm)


# --- 3. LOAD & PREPARE EVALUATION DATASET ---
EVAL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "eval_dataset.json"
)

def load_dataset_for_ragas(file_path: str) -> Dataset:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    formatted_data = {
        "user_input": [item["user_input"] for item in data],
        "retrieved_contexts": [item["retrieved_contexts"] for item in data],
        "response": [item["response"] for item in data],
        "reference": [item["ground_truth"] for item in data], 
    }
    return Dataset.from_dict(formatted_data)


# --- 4. RUN RAGAS EVALUATION PIPELINE ---
def run_evaluation():
    print("🚀 Starting Tata AI Legal RAGAS Evaluation (Throttled + Clean JSON)...")

    dataset = load_dataset_for_ragas(EVAL_DATASET_PATH)

    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
        answer_correctness,
    ]

    for metric in metrics:
        metric.llm = evaluator_llm
        if hasattr(metric, 'embeddings') and metric.embeddings is not None:
            metric.embeddings = evaluator_embeddings

    config = RunConfig(max_workers=1, max_retries=10, timeout=120)

    try:
        results = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
            run_config=config,
            raise_exceptions=False 
        )

        df_results = results.to_pandas()

        f_score = df_results['faithfulness'].mean() if 'faithfulness' in df_results else 0.0
        ar_score = df_results['answer_relevancy'].mean() if 'answer_relevancy' in df_results else 0.0
        cp_score = df_results['context_precision'].mean() if 'context_precision' in df_results else 0.0
        cr_score = df_results['context_recall'].mean() if 'context_recall' in df_results else 0.0
        ac_score = df_results['answer_correctness'].mean() if 'answer_correctness' in df_results else 0.0

        print("\n=================== TATA AI RAGAS EVALUATION SCORECARD ===================")
        print(f"📊 Faithfulness (Groundedness):    {f_score:.4f}")
        print(f"📊 Answer Relevancy:               {ar_score:.4f}")
        print(f"📊 Context Precision (Retrieval):  {cp_score:.4f}")
        print(f"📊 Context Recall (KB Coverage):   {cr_score:.4f}")
        print(f"📊 Answer Correctness (Accuracy):  {ac_score:.4f}")
        print("==========================================================================\n")

        output_csv = os.path.join(
            os.path.dirname(__file__), "ragas_gemini_scorecard.csv"
        )
        df_results.to_csv(output_csv, index=False)
        print(f"✅ Full metric evaluation saved to: {output_csv}")

    except Exception as e:
        print(f"❌ Ragas Evaluation Failed: {e}")

if __name__ == "__main__":
    run_evaluation()