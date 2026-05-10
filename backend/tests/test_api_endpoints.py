from fastapi import status


def test_root_returns_frontend_entrypoint(client):
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]
    assert "RAG Chatbot" in response.text


def test_courses_endpoint_returns_available_courses(client, sample_courses):
    response = client.get("/api/courses")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"courses": sample_courses}


def test_query_endpoint_returns_answer_sources_and_session(client, mock_rag_system):
    response = client.post(
        "/api/query",
        json={"query": "What is retrieval augmented generation?", "session_id": "session-1"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["answer"] == "Test answer for: What is retrieval augmented generation?"
    assert body["session_id"] == "session-1"
    assert body["sources"] == [
        {
            "course_id": "rag-basics",
            "course_title": "RAG Basics",
            "chunk_index": 0,
        }
    ]
    assert mock_rag_system.calls == [
        {
            "query": "What is retrieval augmented generation?",
            "session_id": "session-1",
        }
    ]


def test_query_endpoint_rejects_empty_query(client):
    response = client.post("/api/query", json={"query": "   "})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Query cannot be empty"}


def test_query_endpoint_validates_required_query(client):
    response = client.post("/api/query", json={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
