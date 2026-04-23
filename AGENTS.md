# Repository Guidelines

## Project Structure & Module Organization

This repository contains a small full-stack RAG application. Backend source code
lives in `backend/` and is served by FastAPI from `backend/app.py`. Core behavior
is split across `rag_system.py`, `vector_store.py`, `document_processor.py`,
`ai_generator.py`, and `session_manager.py`. Shared request and response models
are in `backend/models.py`; runtime settings are in `backend/config.py`.

The static UI lives in `frontend/` with `index.html`, `style.css`, and
`script.js`. Course transcript files used as the RAG corpus are in `docs/`.
Tests live in `tests/`.

## Build, Test, and Development Commands

- `uv sync --dev`: install Python 3.13 dependencies and test tools from
  `uv.lock`.
- `cp .env.example .env`: create local configuration, then set `ZAI_API_KEY`.
- `./run.sh`: start the application from the repository root.
- `cd backend && uv run uvicorn app:app --reload --port 8000`: start the
  FastAPI server manually with reload enabled.
- `uv run pytest`: run the Python test suite.

The web app runs at `http://localhost:8000`; API docs are available at
`http://localhost:8000/docs`.

## Coding Style & Naming Conventions

Use 4-space indentation for Python. Prefer type hints at module boundaries,
small functions, and focused modules. Use `snake_case` for files, functions, and
variables; use `PascalCase` for classes such as `RAGSystem` and `QueryRequest`.

Frontend files are plain HTML, CSS, and JavaScript. Keep behavior in
`frontend/script.js` and styling in `frontend/style.css`; do not add frontend
build tooling unless it is clearly needed.

## Testing Guidelines

Tests use `pytest` and should be named `test_<module>.py`. Add or update tests
when changing document parsing, vector search, sessions, API responses, or model
contracts. For API changes, also verify the affected endpoint through `/docs` or
an HTTP client.

## Commit & Pull Request Guidelines

The current Git history uses short subjects such as `added lab files` and
`updated lab files`. Keep commit messages concise and focused on the changed
area.

Pull requests should include the purpose, main files changed, test results, and
screenshots for visible frontend changes. Link related issues when available.

## Security & Configuration Tips

Keep secrets only in `.env`; never commit API keys, caches, local databases, or
uploaded files. The files in `docs/` are source corpus material, so preserve
provider and model names there as original transcript content.
