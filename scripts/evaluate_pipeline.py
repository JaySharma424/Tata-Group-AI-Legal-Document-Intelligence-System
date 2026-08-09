import os
import sys
import json
from dotenv import load_dotenv

# 1. Load environment variables (.env)
load_dotenv()

# 2. Add project root to sys.path for clean module resolution
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from langsmith import Client
from langsmith.evaluation import evaluate
from backend.document_pipeline.legal_graph import legal_pipeline_graph

# Initialize LangSmith Client
client = Client()
DATASET_NAME = "Tata_Legal_Contract_Benchmark_v1.1"

# --- 1. Create Ground Truth Benchmark Dataset ---
def setup_benchmark_dataset():
    """Seeds or verifies the LangSmith benchmark dataset with enterprise contract test cases."""
    if client.has_dataset(dataset_name=DATASET_NAME):
        print(f"✅ Benchmark Dataset '{DATASET_NAME}' verified in LangSmith.")
        return

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Comprehensive benchmark dataset for Tata Group legal contract risk extraction, taxonomy normalization, and RAG policy citation."
    )

    examples = [
        # Example 1: High Risk Uncapped Indemnification
        (
            {
                "ocr_text": "Vendor shall indemnify, defend, and hold harmless Company against all third-party claims, liabilities, damages, penalties, and expenses arising out of intellectual property infringement or data breaches without any financial cap.",
                "user_role": "Senior Reviewer",
                "business_unit": "Procurement",
                "file_path": "sample_indemnity_contract.pdf"
            },
            {
                "expected_risk_level": "HIGH",
                "expected_clause_type": "Indemnification & Hold Harmless",
                "expected_ref_pattern": "RISK-IND"
            }
        ),
        # Example 2: Medium/High Risk Non-Standard Liability Cap
        (
            {
                "ocr_text": "Excluding indemnification obligations and gross negligence, neither party's aggregate liability under this agreement shall exceed 300% of the total fees paid in the preceding 12 months.",
                "user_role": "Compliance Officer",
                "business_unit": "Enterprise Legal",
                "file_path": "sample_liability_contract.pdf"
            },
            {
                "expected_risk_level": "HIGH",
                "expected_clause_type": "Limitation of Liability",
                "expected_ref_pattern": "CLS-LIAB"
            }
        ),
        # Example 3: Low Risk Standard Governing Law (India / Mumbai)
        (
            {
                "ocr_text": "This Agreement shall be governed by and construed in accordance with the substantive laws of India. The parties agree that competent courts in Mumbai, Maharashtra shall have exclusive jurisdiction.",
                "user_role": "Compliance Officer",
                "business_unit": "Enterprise",
                "file_path": "sample_governing_law.pdf"
            },
            {
                "expected_risk_level": "LOW",
                "expected_clause_type": "Governing Law, Jurisdiction & Dispute Resolution",
                "expected_ref_pattern": "LAW-MUM"
            }
        ),
        # Example 4: Standard Confidentiality Terms
        (
            {
                "ocr_text": "Both parties agree to protect all confidential information using at least a reasonable degree of care. Confidentiality obligations shall survive termination of this Agreement for a period of five (5) years.",
                "user_role": "Senior Reviewer",
                "business_unit": "Corporate Strategy",
                "file_path": "sample_nda.pdf"
            },
            {
                "expected_risk_level": "LOW",
                "expected_clause_type": "Confidential Information & Data Security",
                "expected_ref_pattern": "CLS-NDA"
            }
        )
    ]

    for inputs, outputs in examples:
        client.create_example(inputs=inputs, outputs=outputs, dataset_id=dataset.id)
    print(f"✅ Benchmark Dataset '{DATASET_NAME}' created with {len(examples)} examples.")

# --- 2. Custom Evaluator Metric Functions ---
def risk_level_accuracy_evaluator(run, example) -> dict:
    """Evaluates if predicted risk level matches expected ground truth severity."""
    predicted_clauses = run.outputs.get("final_clauses", []) if run.outputs else []
    expected_risk = example.outputs.get("expected_risk_level", "LOW")
    
    if not predicted_clauses:
        return {"key": "risk_accuracy_score", "score": 0.0, "comment": "No clauses extracted."}
    
    predicted_risks = [c.get("risk_level", "").upper() for c in predicted_clauses]
    
    # Check if the target risk level was correctly identified in any extracted clause
    score = 1.0 if expected_risk in predicted_risks else 0.0
    
    return {
        "key": "risk_accuracy_score", 
        "score": score, 
        "comment": f"Expected Risk: {expected_risk} | Predicted Risks: {predicted_risks}"
    }

def rag_grounding_evaluator(run, example) -> dict:
    """Evaluates if the extracted clauses cite valid corporate RAG policy reference IDs."""
    predicted_clauses = run.outputs.get("final_clauses", []) if run.outputs else []
    
    if not predicted_clauses:
        return {"key": "rag_policy_citation_score", "score": 0.0, "comment": "No clauses extracted."}
    
    valid_citations = [
        c.get("rag_reference_used") for c in predicted_clauses 
        if c.get("rag_reference_used") and c.get("rag_reference_used") not in ["N/A", "Standard Policy"]
    ]
    
    has_valid_citation = len(valid_citations) > 0
    score = 1.0 if has_valid_citation else 0.0
    
    return {
        "key": "rag_policy_citation_score",
        "score": score,
        "comment": f"Valid Citations Found: {valid_citations}" if has_valid_citation else "Missing policy citation."
    }

def taxonomy_normalization_evaluator(run, example) -> dict:
    """Evaluates if raw LLM clause headings were mapped to official enterprise taxonomy headers."""
    predicted_clauses = run.outputs.get("final_clauses", []) if run.outputs else []
    expected_type = example.outputs.get("expected_clause_type")
    
    if not predicted_clauses:
        return {"key": "taxonomy_normalization_score", "score": 0.0, "comment": "No clauses extracted."}
    
    predicted_types = [c.get("clause_type", "") for c in predicted_clauses]
    matches = [t for t in predicted_types if expected_type.lower() in t.lower() or t.lower() in expected_type.lower()]
    score = 1.0 if len(matches) > 0 else 0.5
    
    return {
        "key": "taxonomy_normalization_score",
        "score": score,
        "comment": f"Expected: {expected_type} | Extracted Headers: {predicted_types}"
    }

# --- 3. Target Pipeline Execution Wrapper ---
def predict_legal_pipeline(inputs: dict) -> dict:
    """Target wrapper passed to LangSmith evaluator."""
    initial_state = {
        "ocr_text": inputs["ocr_text"],
        "file_path": inputs.get("file_path", ""),
        "user_role": inputs.get("user_role", "Senior Reviewer"),
        "business_unit": inputs.get("business_unit", "Enterprise"),
        "rag_context": [],
        "raw_clauses": [],
        "normalized_clauses": [],
        "final_clauses": []
    }
    return legal_pipeline_graph.invoke(initial_state)

# --- 4. Main Evaluation Runner ---
if __name__ == "__main__":
    setup_benchmark_dataset()
    print("\n🚀 Executing LangSmith Evaluation Experiment across Tata AI Pipeline...")
    
    results = evaluate(
        predict_legal_pipeline,
        data=DATASET_NAME,
        evaluators=[
            risk_level_accuracy_evaluator, 
            rag_grounding_evaluator,
            taxonomy_normalization_evaluator
        ],
        experiment_prefix="LangGraph-MultiModel-Cascade-Eval",
        metadata={
            "version": "1.1.0", 
            "ai_engine": "LangGraph State Machine",
            "model_cascade": "gemini-2.0-flash / gemini-1.5-flash / gemini-2.5-flash / gemini-3.5-flash / gemini-3.6-flash" ,
            "vector_store": "Qdrant In-Memory / Local Disk"
        }
    )
    print("\n✅ LangSmith Evaluation Experiment Complete!")
    print("📊 View detailed execution traces, node latency, and accuracy metrics in your LangSmith Dashboard.")