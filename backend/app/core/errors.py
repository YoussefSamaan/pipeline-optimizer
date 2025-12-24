class DomainError(ValueError):
    """Invalid graph/spec in a domain sense (bad IDs, unreachable demand, etc.)."""


class InfeasibleError(RuntimeError):
    """Raised for infeasible models (used optionally)."""
