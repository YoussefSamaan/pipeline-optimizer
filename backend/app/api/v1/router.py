from fastapi import APIRouter
from app.api.v1.solve import router as solve_router

router = APIRouter()
router.include_router(solve_router)
