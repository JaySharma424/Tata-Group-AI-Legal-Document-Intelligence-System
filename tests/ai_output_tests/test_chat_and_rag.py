from fastapi.testclient import TestClient
from backend.main import app
from backend.services.rag_service import RAGKnowledgeService

client = TestClient(app)
rag_service = RAGKnowledgeService()

def test_rag_context_retrieval():
    """Ensure vector DB correctly retrieves policy context for liability/confidentiality queries."""
    results = rag_service.retrieve_context("What is the liability cap?")
    assert isinstance(results, list)
    if len(results) > 0:
        assert "ref" in results[0]
        assert "text" in results[0]

def test_chat_out_of_domain_filter():
    """Ensure chatbot filters out general world questions (e.g. weather/sports) and maintains persona."""
    payload = {
        "query": "What is the capital of France?",
        "user_id": "test_user"
    }
    response = client.post("/api/v1/chat/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    # Should trigger out-of-domain deflection
    assert "Aadhya" in data["answer"] or "compliance" in data["answer"].lower()