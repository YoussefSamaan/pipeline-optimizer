from fastapi import APIRouter

from app.api.v1.solve import router as solve_router

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


router.include_router(solve_router)
