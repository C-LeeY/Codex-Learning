from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def sample_course() -> dict[str, Any]:
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
def sample_courses(sample_course: dict[str, Any]) -> list[dict[str, Any]]:
    return [sample_course]


@pytest.fixture
def mock_rag_system(sample_courses: list[dict[str, Any]]) -> Mock:
    rag_system = Mock()
    rag_system.query = AsyncMock(
        return_value={
            "answer": "Retrieval augmented generation combines search with generation.",
            "sources": [
                {
                    "text": "RAG combines retrieval with generation.",
                    "course_title": sample_courses[0]["title"],
                    "lesson_title": sample_courses[0]["lessons"][0]["lesson_title"],
                    "lesson_number": sample_courses[0]["lessons"][0]["lesson_number"],
                    "source_url": sample_courses[0]["lessons"][0]["lesson_link"],
                }
            ],
        }
    )
    rag_system.get_course_analytics.return_value = {
        "total_courses": len(sample_courses),
        "course_titles": [course["title"] for course in sample_courses],
    }
    return rag_system
