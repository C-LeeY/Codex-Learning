from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
import pytest


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None


def create_test_app(rag_system: Any) -> FastAPI:
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "RAG Chatbot API"}

    @app.post("/api/query")
    async def query(request: QueryRequest) -> dict[str, Any]:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        result = await rag_system.query(request.query, request.session_id)
        return {
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "session_id": request.session_id,
        }

    @app.get("/api/courses")
    async def courses() -> dict[str, Any]:
        return rag_system.get_course_analytics()

    return app


@pytest.fixture
def client(mock_rag_system: Any) -> TestClient:
    return TestClient(create_test_app(mock_rag_system))


def test_root_endpoint_returns_api_status(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "RAG Chatbot API"}


def test_courses_endpoint_returns_course_analytics(
    client: TestClient, sample_courses: list[dict[str, Any]]
) -> None:
    response = client.get("/api/courses")

    assert response.status_code == 200
    assert response.json() == {
        "total_courses": 1,
        "course_titles": [sample_courses[0]["title"]],
    }


def test_query_endpoint_returns_answer_and_sources(
    client: TestClient, mock_rag_system: Any
) -> None:
    response = client.post(
        "/api/query",
        json={"query": "What is RAG?", "session_id": "test-session"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Retrieval augmented generation combines search with generation."
    assert payload["session_id"] == "test-session"
    assert len(payload["sources"]) == 1
    mock_rag_system.query.assert_awaited_once_with("What is RAG?", "test-session")


def test_query_endpoint_allows_missing_session_id(
    client: TestClient, mock_rag_system: Any
) -> None:
    response = client.post("/api/query", json={"query": "Explain retrieval"})

    assert response.status_code == 200
    assert response.json()["session_id"] is None
    mock_rag_system.query.assert_awaited_once_with("Explain retrieval", None)


@pytest.mark.parametrize("query", ["", "   "])
def test_query_endpoint_rejects_empty_query(client: TestClient, query: str) -> None:
    response = client.post("/api/query", json={"query": query})

    assert response.status_code == 400
    assert response.json()["detail"] == "Query cannot be empty"


def test_query_endpoint_validates_required_query(client: TestClient) -> None:
    response = client.post("/api/query", json={"session_id": "test-session"})

    assert response.status_code == 422
