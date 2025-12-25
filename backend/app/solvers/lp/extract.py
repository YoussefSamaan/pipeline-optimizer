from __future__ import annotations

from typing import Dict, List, Literal, Optional

from ortools.linear_solver import pywraplp

from app.domain.schema import SolveRequest, SolveResult, TightConstraint
from app.solvers.lp.build import LPBuild


_APIStatus = Literal["optimal", "infeasible", "unbounded", "error"]


def extract_solution(
    spec: SolveRequest, built: LPBuild, eps: float = 1e-7
) -> SolveResult:
    s = built.solver
    status = s.Solve()

    # --- status mapping / early returns ---
    if status == pywraplp.Solver.OPTIMAL:
        api_status: _APIStatus = "optimal"
        message: Optional[str] = None
    elif status == pywraplp.Solver.FEASIBLE:
        # GLOP typically returns OPTIMAL, but keep this for completeness.
        api_status = "optimal"
        message = "Solver returned FEASIBLE (treated as optimal)."
    elif status == pywraplp.Solver.INFEASIBLE:
        return _empty_result("infeasible", "Model is infeasible.")
    elif status == pywraplp.Solver.UNBOUNDED:
        return _empty_result("unbounded", "Model is unbounded.")
    elif status == pywraplp.Solver.MODEL_INVALID:
        return _empty_result(
            "error", "Model is invalid (NaN/Inf coefficients or malformed constraints)."
        )
    elif status == pywraplp.Solver.NOT_SOLVED:
        return _empty_result(
            "error", "Model not solved (solver did not run or stopped early)."
        )
    elif status == pywraplp.Solver.ABNORMAL:
        return _empty_result("error", "Solver ended abnormally.")
    else:
        return _empty_result("error", f"Unknown solver status: {status}")

    # --- extract variables ---
    edge_flows: Dict[str, float] = {
        eid: var.solution_value() for eid, var in built.f_edge.items()
    }
    process_runs: Dict[str, float] = {
        nid: var.solution_value() for nid, var in built.r_proc.items()
    }

    # delivered to sinks = inflow of sink commodity (as built)
    sink_delivered: Dict[str, float] = {}
    for n in spec.nodes:
        if n.type == "sink" and n.sink is not None:
            expr = built.sink_delivered_expr.get(n.id, 0.0)
            # expr might be float 0.0 or LinearExpr-like
            try:
                val = float(expr.solution_value())
            except AttributeError:
                val = float(expr)
            sink_delivered[n.id] = val

    tight: List[TightConstraint] = _compute_tight_constraints(
        spec, built, edge_flows, process_runs, eps=eps
    )

    return SolveResult(
        status=api_status,
        message=message,
        objective_value=s.Objective().Value(),
        edge_flows=edge_flows,
        process_runs=process_runs,
        sink_delivered=sink_delivered,
        tight_constraints=tight,
    )


def _empty_result(status: _APIStatus, message: str) -> SolveResult:
    """
    Always returns a SolveResult that is valid even if your schema requires fields
    like edge_flows/process_runs/etc. (keeps API responses consistent).
    """
    return SolveResult(
        status=status,
        message=message,
        objective_value=None,
        edge_flows={},
        process_runs={},
        sink_delivered={},
        tight_constraints=[],
    )


def _compute_tight_constraints(
    spec: SolveRequest,
    built: LPBuild,
    edge_flows: Dict[str, float],
    process_runs: Dict[str, float],
    eps: float = 1e-6,
) -> List[TightConstraint]:
    tight: List[TightConstraint] = []

    # Edge caps
    for eid, cap in built.edge_caps.items():
        slack = cap - edge_flows.get(eid, 0.0)
        if slack <= eps:
            tight.append(TightConstraint(name=f"edge_cap:{eid}", slack=slack))

    nodes = {n.id: n for n in spec.nodes}

    # Source supply
    for nid, cap in built.source_supply_caps.items():
        n = nodes[nid]
        c = n.source.commodity  # type: ignore[union-attr]
        out_ids = built.edges_by_u_comm.get((nid, c), [])
        used = sum(edge_flows.get(eid, 0.0) for eid in out_ids)
        slack = cap - used
        if slack <= eps:
            tight.append(TightConstraint(name=f"source_supply:{nid}", slack=slack))

    # Sink demand
    for nid, cap in built.sink_demand_caps.items():
        n = nodes[nid]
        c = n.sink.commodity  # type: ignore[union-attr]
        in_ids = built.edges_by_v_comm.get((nid, c), [])
        used = sum(edge_flows.get(eid, 0.0) for eid in in_ids)
        slack = cap - used
        if slack <= eps:
            tight.append(TightConstraint(name=f"sink_demand:{nid}", slack=slack))

    # Process run caps
    for nid, cap in built.proc_run_caps.items():
        used = process_runs.get(nid, 0.0)
        slack = cap - used
        if slack <= eps:
            tight.append(TightConstraint(name=f"process_run_cap:{nid}", slack=slack))

    tight.sort(key=lambda x: x.slack)
    return tight
