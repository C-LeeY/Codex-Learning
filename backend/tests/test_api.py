from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

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
def ui_sample_course() -> dict[str, Any]:
    return {
        "title": "Introduction to RAG",
        "instructor": "Test Instructor",
        "course_link": "https://example.com/rag",
        "lessons": [
            {
                "lesson_number": 1,
                "lesson_title": "Retrieval Basics",
                "lesson_link": "https://example.com/rag/lesson-1",
            }
        ],
    }


@pytest.fixture
def ui_sample_courses(ui_sample_course: dict[str, Any]) -> list[dict[str, Any]]:
    return [ui_sample_course]


@pytest.fixture
def ui_mock_rag_system(ui_sample_courses: list[dict[str, Any]]) -> Mock:
    rag_system = Mock()
    rag_system.query = AsyncMock(
        return_value={
            "answer": "Retrieval augmented generation combines search with generation.",
            "sources": [
                {
                    "text": "RAG combines retrieval with generation.",
                    "course_title": ui_sample_courses[0]["title"],
                    "lesson_title": ui_sample_courses[0]["lessons"][0]["lesson_title"],
                    "lesson_number": ui_sample_courses[0]["lessons"][0]["lesson_number"],
                    "source_url": ui_sample_courses[0]["lessons"][0]["lesson_link"],
                }
            ],
        }
    )
    rag_system.get_course_analytics.return_value = {
        "total_courses": len(ui_sample_courses),
        "course_titles": [course["title"] for course in ui_sample_courses],
    }
    return rag_system


@pytest.fixture
def ui_client(ui_mock_rag_system: Any) -> TestClient:
    return TestClient(create_test_app(ui_mock_rag_system))


def test_root_endpoint_returns_api_status(ui_client: TestClient) -> None:
    response = ui_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "RAG Chatbot API"}


def test_courses_endpoint_returns_course_analytics(
    ui_client: TestClient, ui_sample_courses: list[dict[str, Any]]
) -> None:
    response = ui_client.get("/api/courses")

    assert response.status_code == 200
    assert response.json() == {
        "total_courses": 1,
        "course_titles": [ui_sample_courses[0]["title"]],
    }


def test_query_endpoint_returns_answer_and_sources(
    ui_client: TestClient, ui_mock_rag_system: Any
) -> None:
    response = ui_client.post(
        "/api/query",
        json={"query": "What is RAG?", "session_id": "test-session"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Retrieval augmented generation combines search with generation."
    assert payload["session_id"] == "test-session"
    assert len(payload["sources"]) == 1
    ui_mock_rag_system.query.assert_awaited_once_with("What is RAG?", "test-session")


def test_query_endpoint_allows_missing_session_id(
    ui_client: TestClient, ui_mock_rag_system: Any
) -> None:
    response = ui_client.post("/api/query", json={"query": "Explain retrieval"})

    assert response.status_code == 200
    assert response.json()["session_id"] is None
    ui_mock_rag_system.query.assert_awaited_once_with("Explain retrieval", None)


@pytest.mark.parametrize("query", ["", "   "])
def test_query_endpoint_rejects_empty_query(ui_client: TestClient, query: str) -> None:
    response = ui_client.post("/api/query", json={"query": query})

    assert response.status_code == 400
    assert response.json()["detail"] == "Query cannot be empty"


def test_query_endpoint_validates_required_query(ui_client: TestClient) -> None:
    response = ui_client.post("/api/query", json={"session_id": "test-session"})

    assert response.status_code == 422
