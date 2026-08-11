import os
import json
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

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY environment variable is missing!")

# 1. INITIALIZE GEMINI EVALUATOR MODELS
# FIX 1: Upgraded from deprecated 1.5 to active gemini-2.5-flash
evaluator_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0
)

evaluator_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    google_api_key=GEMINI_API_KEY
)

# 2. LOAD & PREPARE EVALUATION DATASET
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
        "ground_truth": [item["ground_truth"] for item in data],
    }
    return Dataset.from_dict(formatted_data)

# 3. RUN RAGAS EVALUATION PIPELINE
def run_evaluation():
    print("🚀 Starting Tata AI Legal RAGAS Evaluation...")

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

    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings
    )

    df_results = results.to_pandas()

    # FIX 2: Safely calculate the mean scores directly from the Pandas dataframe
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

if __name__ == "__main__":
    run_evaluation()