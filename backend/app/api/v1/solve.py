from fastapi import APIRouter
from app.domain.schema import SolveRequest, SolveResult
from app.domain.normalize import normalize_request
from app.domain.validate import validate_request
from app.solvers.lp.solver import solve_lp

router = APIRouter(tags=["solve"])


@router.post("/solve", response_model=SolveResult)
def solve(req: SolveRequest) -> SolveResult:
    spec = normalize_request(req)
    validate_request(spec)

    if spec.options.mode != "lp":
        return SolveResult(
            status="error",
            message=f"Mode '{spec.options.mode}' not implemented yet (supports mode='lp').",
        )

    return solve_lp(spec)
