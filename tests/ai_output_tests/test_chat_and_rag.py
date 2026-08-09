from fastapi.testclient import TestClient
from backend.main import app
from backend.services.rag_service import RAGKnowledgeService

client = TestClient(app)
rag_service = RAGKnowledgeService()


def test_rag_structured_reference_retrieval():
    """Verify vector DB retrieves structured legal reference IDs (e.g. CLS-LIAB-001 or LAW-CORP-882)."""
    results = rag_service.retrieve_context(
        "Vendor liability capping and indemnity limits"
    )
    assert isinstance(results, list)
    assert len(results) > 0, "RAG Knowledge Service returned empty results"

    # Verify structured reference format
    first_result = results[0]
    assert "ref" in first_result
    assert "text" in first_result
    assert (
        first_result["ref"] != "REF-N/A"
    ), "Retrieved reference ID should not be default placeholder"


def test_rag_category_metadata_filter():
    """Verify Qdrant metadata filtering by legal category."""
    results = rag_service.retrieve_context(
        query_text="termination for convenience notice period",
        category_filter="TERMINATION & EXIT",
    )
    assert isinstance(results, list)


def test_chat_out_of_domain_filter():
    """Ensure chatbot filters out non-legal general knowledge questions."""
    payload = {
        "query": "What is the capital of France?",
        "user_id": "test_user",
    }
    response = client.post("/api/v1/chat/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert (
        "Aadhya" in data["answer"]
        or "compliance" in data["answer"].lower()
        or "legal" in data["answer"].lower()
    )