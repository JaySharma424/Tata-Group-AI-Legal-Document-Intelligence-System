import os
import json
import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevance,
    context_precision,
    context_recall,
    answer_correctness,
)

# Import LangChain Gemini integration matching your exact requirements.txt stack
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

# -------------------------------------------------------------------------
# 1. INITIALIZE GEMINI EVALUATOR MODELS (Matching Render Environment)
# -------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY environment variable is missing!")

# Use Gemini 1.5 Flash for fast, low-latency evaluation scoring
evaluator_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0
)

evaluator_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GEMINI_API_KEY
)

# -------------------------------------------------------------------------
# 2. LOAD & PREPARE EVALUATION DATASET
# -------------------------------------------------------------------------
EVAL_DATASET_PATH = "tests/ai_output_tests/eval_dataset.json"

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

# -------------------------------------------------------------------------
# 3. RUN RAGAS EVALUATION PIPELINE
# -------------------------------------------------------------------------
def run_evaluation():
    print("🚀 Starting Tata AI Legal RAGAS Evaluation (Gemini & Render Engine)...")

    dataset = load_dataset_for_ragas(EVAL_DATASET_PATH)

    # List of metrics to evaluate
    metrics = [
        faithfulness,
        answer_relevance,
        context_precision,
        context_recall,
        answer_correctness,
    ]

    # Explicitly bind Gemini LLM & Embeddings to all RAGAS metrics
    for metric in metrics:
        metric.llm = evaluator_llm
        if hasattr(metric, 'embeddings') and metric.embeddings is not None:
            metric.embeddings = evaluator_embeddings

    # Run RAGAS scoring
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings
    )

    # -------------------------------------------------------------------------
    # 4. EXPORT & PRINT SCORECARD
    # -------------------------------------------------------------------------
    df_results = results.to_pandas()

    print("\n=================== TATA AI RAGAS EVALUATION SCORECARD ===================")
    print(f"📊 Faithfulness (Groundedness):    {results.get('faithfulness', 0):.4f}")
    print(f"📊 Context Precision (Retrieval):  {results.get('context_precision', 0):.4f}")
    print(f"📊 Context Recall (KB Coverage):    {results.get('context_recall', 0):.4f}")
    print(f"📊 Answer Correctness (Accuracy):  {results.get('answer_correctness', 0):.4f}")
    print("==========================================================================\n")

    output_csv = "tests/ai_output_tests/ragas_gemini_scorecard.csv"
    df_results.to_csv(output_csv, index=False)
    print(f"✅ Full metric evaluation saved to: {output_csv}")

if __name__ == "__main__":
    run_evaluation()