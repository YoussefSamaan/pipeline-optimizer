# Backend - Production Planning Optimizer

The backend is a high-performance REST API built with **FastAPI** that serves as the calculation engine for the application.

## Tech Stack
- **Framework**: FastAPI (Python 3.12+)
- **Server**: Uvicorn

## Directory Structure
- `app/api`: API route handlers
- `app/models`: Pydantic data models
- `app/algorithms`: Solver implementations
- `tests`: Unit tests

## Running Locally

### 1. Unified Run Script (Recommended)
This script enforces **>90% test coverage** before starting the server.
```bash
# From the project root
./run_backend.sh
```

### 2. Manual Installation
```bash
pip install -r requirements.txt
```

## Testing & Coverage
We enforce a strict **90% coverage** threshold. If coverage falls below this, the server will not start in `run` mode.
```bash
# Run tests only
./run_backend.sh test
```

## Health Check
GET http://localhost:8000/api/v1/health
```json
{"status": "ok"}
```
