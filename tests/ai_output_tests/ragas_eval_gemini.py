import os
import json
import time
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


# --- 1. MODEL INITIALIZATION ---
print("🔄 Initializing Gemini Evaluator Models...")

base_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0,
    max_retries=3
)

evaluator_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    google_api_key=GEMINI_API_KEY
)


# --- 2. LIGHTWEIGHT RATE LIMIT & JSON CLEANING WRAPPER ---
def clean_json_output(text: str) -> str:
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
    delay: float = 1.5 # Balanced delay to prevent rate limits without timing out
    
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
        for gen in result.generations:
            gen.text = clean_json_output(gen.text)
            gen.message.content = clean_json_output(gen.message.content)
        return result

evaluator_llm = RateLimitedLLM(llm=base_llm)


# --- 3. LOAD DATASET ---
EVAL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "eval_dataset.json"
)

def load_dataset_for_ragas(file_path: str) -> Dataset:
    if not os.path.exists(file_path):
        file_path = "eval_dataset.json"
        
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    formatted_data = {
        "user_input": [item["user_input"] for item in data],
        "retrieved_contexts": [item["retrieved_contexts"] for item in data],
        "response": [item["response"] for item in data],
        "reference": [item["reference"] for item in data], 
    }
    return Dataset.from_dict(formatted_data)


# --- 4. RUN EVALUATION ---
def run_evaluation():
    print("🚀 Starting Fast Tata AI Legal RAGAS Evaluation...")

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

    config = RunConfig(max_workers=1, max_retries=5, timeout=60)

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

        f_score = df_results['faithfulness'].mean(skipna=True) if 'faithfulness' in df_results else 0.0
        ar_score = df_results['answer_relevancy'].mean(skipna=True) if 'answer_relevancy' in df_results else 0.0
        cp_score = df_results['context_precision'].mean(skipna=True) if 'context_precision' in df_results else 0.0
        cr_score = df_results['context_recall'].mean(skipna=True) if 'context_recall' in df_results else 0.0
        ac_score = df_results['answer_correctness'].mean(skipna=True) if 'answer_correctness' in df_results else 0.0

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