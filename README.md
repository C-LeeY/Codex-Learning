# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Zhipu/Z.ai GLM models for AI generation, and provides a web interface for interaction.

The files in `docs/` are raw course-material transcripts used as the RAG corpus.
Any provider or model names that appear there are source content only; the
application itself uses the Zhipu/Z.ai configuration described below.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- A Zhipu/Z.ai API key
- **For Windows**: Git Bash is recommended for `run.sh`; PowerShell users can run the manual commands below.

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   On Windows, if `uv` is installed through Python but not on `PATH`, use `python -m uv` in place of `uv` for commands such as `python -m uv sync --dev`.

2. **Install Python dependencies**
   ```bash
   uv sync --dev
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ZAI_API_KEY=your_zhipu_api_key_here
   ZAI_MODEL=glm-4.7-flash
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

On Windows, run this script from Git Bash.

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Testing

Run the Python test suite from the repository root:

```bash
uv run pytest
```

The current tests cover the shared Pydantic models and are located in `tests/`. Add new tests as `tests/test_<module>.py` when changing backend behavior.

