import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None


@pytest.fixture
def sample_courses() -> list[dict[str, str]]:
    return [
        {"id": "rag-basics", "title": "RAG Basics"},
        {"id": "vector-search", "title": "Vector Search"},
    ]


@pytest.fixture
def mock_rag_system(sample_courses):
    class MockRAGSystem:
        def __init__(self) -> None:
            self.calls: list[dict[str, str | None]] = []

        def query(self, query: str, session_id: str | None = None) -> dict:
            self.calls.append({"query": query, "session_id": session_id})
            return {
                "answer": f"Test answer for: {query}",
                "sources": [
                    {
                        "course_id": sample_courses[0]["id"],
                        "course_title": sample_courses[0]["title"],
                        "chunk_index": 0,
                    }
                ],
                "session_id": session_id or "test-session",
            }

        def get_courses(self) -> list[dict[str, str]]:
            return sample_courses

    return MockRAGSystem()


@pytest.fixture
def test_app(mock_rag_system) -> FastAPI:
    app = FastAPI()

    @app.get("/")
    def index() -> HTMLResponse:
        return HTMLResponse("<!doctype html><title>RAG Chatbot</title>")

    @app.post("/api/query")
    def query(request: QueryRequest) -> dict:
        query_text = request.query.strip()
        if not query_text:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        return mock_rag_system.query(query_text, request.session_id)

    @app.get("/api/courses")
    def courses() -> dict[str, list[dict[str, str]]]:
        return {"courses": mock_rag_system.get_courses()}

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)
