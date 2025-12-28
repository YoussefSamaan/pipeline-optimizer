# Backend - Production Planning Optimizer

The backend is a high-performance FastAPI service that solves production-planning problems as linear programs (LPs) using Google OR-Tools. It exposes a stateless JSON API that accepts a network model and returns the optimal flows, process runs, and objective value.

## Vision & Capabilities
- **Constraint satisfaction**: Enforces flow conservation, capacity limits, and topology validity before touching the solver.
- **Profit & flow optimization**: Supports max-profit and max-flow objectives with clear objective encoding.
- **Extensibility**: The solver layer is isolated, making it straightforward to add MIP or alternative backends later.

## Tech Stack
- **Framework**: FastAPI (Python 3.12+)
- **Server**: Uvicorn
- **Solver**: Google OR-Tools (LP)
- **Validation**: Pydantic models plus domain validators
- **Testing**: Pytest with coverage gates

## Directory Structure
- `app/api`: Versioned API routers (`/v1` exposes `/solve` and `/health`).
- `app/domain`: Pydantic schemas, normalization hooks, and validation of graph consistency.
- `app/solvers`: OR-Tools linear-programming builder/extractor/solver glue.
- `tests`: Unit and integration tests covering API surface, validation, and solver behavior.

## Running Locally

### 1. Unified Run Script (recommended)
The root `config.yml` controls which checks run. By default linting is disabled, formatting/type checks and tests are enabled, and coverage must meet or exceed the configured threshold (90% by default).
```bash
# From the project root
./run_backend.sh           # setup + checks + run server
./run_backend.sh test      # setup + checks only
./run_backend.sh fix       # auto-fix formatting/lint where possible
```

### 2. Manual installation
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API Contract
- **Solve**: `POST /v1/solve` accepts a supply/process/sink graph and returns the optimal objective value, flows, and process runs.
- **Health**: `GET /health` and `GET /v1/health` both return `{ "status": "ok" }`.

The OpenAPI spec is available at `http://localhost:8000/docs` once the server is running. Application metadata currently reports **Pipeline Optimizer API v1.0.0**.

## Testing & Coverage
```bash
./run_backend.sh test
```
Tests run with coverage enforced at the configured threshold. Use `config.yml` to raise the bar (e.g., to 100%) or to enable linting on CI/local runs.
