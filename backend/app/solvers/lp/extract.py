from __future__ import annotations

from typing import Dict, List, Optional

from ortools.linear_solver import pywraplp

from app.domain.schema import (
    NodeType,
    SolveRequest,
    SolveResult,
    SolveStatus,
    TightConstraint,
)
from app.solvers.lp.build import LPBuild

# OR-Tools returns an int status code; this alias makes typing intent explicit.
_LpStatus = int


def extract_solution(
    spec: SolveRequest, built: LPBuild, eps: float = 1e-7
) -> SolveResult:
    s = built.solver
    status_code = s.Solve()

    # Status mapping (treat FEASIBLE as "optimal" for now, but add a message)
    status_map: Dict[_LpStatus, SolveStatus] = {
        pywraplp.Solver.OPTIMAL: SolveStatus.OPTIMAL,
        pywraplp.Solver.FEASIBLE: SolveStatus.OPTIMAL,
        pywraplp.Solver.INFEASIBLE: SolveStatus.INFEASIBLE,
        pywraplp.Solver.UNBOUNDED: SolveStatus.UNBOUNDED,
    }
    result_status = status_map.get(status_code, SolveStatus.ERROR)

    if result_status == SolveStatus.INFEASIBLE:
        return _empty_result(SolveStatus.INFEASIBLE, "Model is infeasible.")
    if result_status == SolveStatus.UNBOUNDED:
        return _empty_result(SolveStatus.UNBOUNDED, "Model is unbounded.")
    if result_status == SolveStatus.ERROR:
        return _empty_result(SolveStatus.ERROR, _status_message(status_code))

    message: Optional[str] = None
    if status_code == pywraplp.Solver.FEASIBLE:
        message = "Solver returned FEASIBLE (treated as optimal)."

    # Solution values
    edge_flows: Dict[str, float] = {
        eid: var.solution_value() for eid, var in built.f_edge.items()
    }
    process_runs: Dict[str, float] = {
        nid: var.solution_value() for nid, var in built.r_proc.items()
    }

    # Delivered to sinks = total incoming flow for each sink's commodity
    sink_delivered = _compute_sink_delivered(spec, built, edge_flows)

    tight = _compute_tight_constraints(spec, built, edge_flows, process_runs, eps=eps)

    return SolveResult(
        status=result_status,
        message=message,
        objective_value=s.Objective().Value(),
        edge_flows=edge_flows,
        process_runs=process_runs,
        sink_delivered=sink_delivered,
        tight_constraints=tight,
    )


def _status_message(status_code: int) -> str:
    if status_code == pywraplp.Solver.MODEL_INVALID:
        return "Model is invalid (NaN/Inf coefficients or malformed constraints)."
    if status_code == pywraplp.Solver.NOT_SOLVED:
        return "Model not solved (solver did not run or stopped early)."
    if status_code == pywraplp.Solver.ABNORMAL:
        return "Solver ended abnormally."
    return f"Unknown solver status: {status_code}"


def _empty_result(status: SolveStatus, message: Optional[str] = None) -> SolveResult:
    return SolveResult(
        status=status,
        message=message,
        objective_value=None,
        edge_flows={},
        process_runs={},
        sink_delivered={},
        tight_constraints=[],
    )


def _compute_sink_delivered(
    spec: SolveRequest, built: LPBuild, edge_flows: Dict[str, float]
) -> Dict[str, float]:
    sink_delivered: Dict[str, float] = {}
    for n in spec.nodes:
        if n.type != NodeType.SINK or n.sink is None:
            continue
        c = n.sink.commodity
        in_ids = built.edges_by_v_comm.get((n.id, c), [])
        sink_delivered[n.id] = sum(edge_flows.get(eid, 0.0) for eid in in_ids)
    return sink_delivered


def _compute_tight_constraints(
    spec: SolveRequest,
    built: LPBuild,
    edge_flows: Dict[str, float],
    process_runs: Dict[str, float],
    eps: float = 1e-6,
) -> List[TightConstraint]:
    tight: List[TightConstraint] = []
    nodes = {n.id: n for n in spec.nodes}

    # Edge caps: cap - flow
    for eid, cap in built.edge_caps.items():
        slack = cap - edge_flows.get(eid, 0.0)
        if slack <= eps:
            tight.append(TightConstraint(name=f"edge_cap:{eid}", slack=slack))

    # Source supply: cap - total outgoing flow for its commodity
    for nid, cap in built.source_supply_caps.items():
        n = nodes[nid]
        assert n.source is not None
        c = n.source.commodity
        out_ids = built.edges_by_u_comm.get((nid, c), [])
        used = sum(edge_flows.get(eid, 0.0) for eid in out_ids)
        slack = cap - used
        if slack <= eps:
            tight.append(TightConstraint(name=f"source_supply:{nid}", slack=slack))

    # Sink demand: cap - total incoming flow for its commodity
    for nid, cap in built.sink_demand_caps.items():
        n = nodes[nid]
        assert n.sink is not None
        c = n.sink.commodity
        in_ids = built.edges_by_v_comm.get((nid, c), [])
        used = sum(edge_flows.get(eid, 0.0) for eid in in_ids)
        slack = cap - used
        if slack <= eps:
            tight.append(TightConstraint(name=f"sink_demand:{nid}", slack=slack))

    # Process run caps: cap - runs
    for nid, cap in built.proc_run_caps.items():
        used = process_runs.get(nid, 0.0)
        slack = cap - used
        if slack <= eps:
            tight.append(TightConstraint(name=f"process_run_cap:{nid}", slack=slack))

    tight.sort(key=lambda x: x.slack)
    return tight
