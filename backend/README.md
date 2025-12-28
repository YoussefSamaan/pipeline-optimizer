# Backend - Production Planning Optimizer

The backend is a high-performance REST API built with **FastAPI** that serves as the calculation engine for the application.

## Tech Stack
- **Framework**: FastAPI (Python 3.12+)
- **Server**: Uvicorn

## Directory Structure
- `app/api`: Versioned API routers (`/v1` includes `/solve` and a versioned health check)
- `app/domain`: Pydantic schemas plus request normalization and validation
- `app/solvers`: OR-Tools linear-programming builder/extractor/solver
- `tests`: Pytest suite covering API, domain validation, and solver behavior

## Running Locally

### 1. Unified Run Script (Recommended)
This script enforces **>90% test coverage** before starting the server. Linting/formatting/type checks can be toggled from `config.yml` (linting is currently disabled there by default).
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
GET http://localhost:8000/health  
GET http://localhost:8000/v1/health
```json
{"status": "ok"}
```

## API Metadata
- Title: `Pipeline Optimizer API`  
- Version: `0.2.0`
