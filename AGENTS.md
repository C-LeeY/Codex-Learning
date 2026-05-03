# Repository Guidelines

## Project Structure & Module Organization

This repository contains a small full-stack RAG chatbot. The FastAPI backend lives in `backend/`, with `app.py` defining routes and static serving, `rag_system.py` coordinating retrieval and generation, and helper modules for document processing, sessions, vector storage, models, configuration, and search tools. The browser UI is static and lives in `frontend/` (`index.html`, `style.css`, `script.js`). Course source material is stored as plain text in `docs/`. Root-level files include `pyproject.toml` and `uv.lock` for Python dependencies, `.env.example` for configuration, and `run.sh` for local startup.

## Build, Test, and Development Commands

- `uv sync`: install the Python 3.13 dependencies pinned in `uv.lock`.
- `./run.sh`: start the development server from the repository root. On Windows, run this from Git Bash.
- `cd backend && uv run uvicorn app:app --reload --port 8000`: manually start the API and static frontend.

When running locally, open `http://localhost:8000` for the UI and `http://localhost:8000/docs` for FastAPI-generated API docs.

## Coding Style & Naming Conventions

Use standard Python style with 4-space indentation, type hints where they clarify API boundaries, and concise docstrings for route handlers or public classes. Keep backend module names lowercase with underscores, matching the existing pattern (`document_processor.py`, `session_manager.py`). Use Pydantic models for request and response schemas. Frontend files should stay framework-free unless the project intentionally adopts a build step.

## Testing Guidelines

No automated test suite is currently present. For new backend behavior, prefer adding `pytest` tests under a future `tests/` directory with names like `test_rag_system.py` or `test_api_query.py`. Until tests are added, verify changes manually by running the server, checking `/api/courses`, sending a sample `/api/query` request, and confirming the frontend loads without console errors.

## Commit & Pull Request Guidelines

The current Git history uses short, plain-English commit messages such as `initial commit` and `added lab files`. Continue using concise imperative or descriptive summaries, for example `add query validation` or `update course loader`. Pull requests should include a brief description, manual test steps, any configuration changes, and screenshots when UI behavior changes.

## Security & Configuration Tips

Do not commit real secrets. Copy `.env.example` to `.env` and set `ZHIPU_API_KEY` locally. Keep generated logs, local vector stores, and machine-specific files out of version control unless they are intentionally part of the project.
