from __future__ import annotations

from app.domain.schema import SolveRequest, SolveResult
from app.solvers.lp.build import build_lp
from app.solvers.lp.extract import extract_solution


def solve_lp(spec: SolveRequest) -> SolveResult:
    built = build_lp(spec)
    return extract_solution(spec, built)
