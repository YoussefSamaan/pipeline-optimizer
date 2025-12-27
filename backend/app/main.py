from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.errors import DomainError


def create_app() -> FastAPI:
    app = FastAPI(title="Pipeline Optimizer API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    def domain_error_handler(_, exc: DomainError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(v1_router, prefix="/v1")
    return app


def run() -> None:
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("RELOAD", "false").lower() == "true"

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    run()
