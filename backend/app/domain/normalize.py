from __future__ import annotations
from app.domain.schema import SolveRequest


def normalize_request(req: SolveRequest) -> SolveRequest:
    """
    normalization:
    - ensure lists exist via pydantic defaults
    - keep as-is (frontend is source of truth)
    """
    return req
