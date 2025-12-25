from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional

from ortools.linear_solver import pywraplp

from app.core.errors import DomainError
from app.domain.schema import SolveRequest


@dataclass
class LPBuild:
    solver: pywraplp.Solver
    f_edge: Dict[str, pywraplp.Variable]  # edge_id -> flow var
    r_proc: Dict[str, pywraplp.Variable]  # node_id -> run var

    # Helpers for extraction / slacks
    edge_caps: Dict[str, float]  # edge_id -> cap
    source_supply_caps: Dict[str, float]  # node_id -> cap
    sink_demand_caps: Dict[str, float]  # node_id -> cap
    proc_run_caps: Dict[str, float]  # node_id -> cap

    # convenience maps
    edges_by_u_comm: Dict[Tuple[str, str], List[str]]  # (u, commodity) -> [edge_id]
    edges_by_v_comm: Dict[Tuple[str, str], List[str]]  # (v, commodity) -> [edge_id]
    sink_delivered_expr: Dict[str, pywraplp.LinearExpr]  # sink_id -> delivered expr
    source_outflow_expr: Dict[str, pywraplp.LinearExpr]  # source_id -> outflow expr


def build_lp(spec: SolveRequest) -> LPBuild:
    s = pywraplp.Solver.CreateSolver("GLOP")  # Continuous LP
    if s is None:
        raise RuntimeError("Failed to create OR-Tools GLOP solver.")

    # Variables: f_e >= 0, r_p >= 0
    f_edge: Dict[str, pywraplp.Variable] = {}
    r_proc: Dict[str, pywraplp.Variable] = {}

    for e in spec.edges:
        f_edge[e.id] = s.NumVar(0.0, s.infinity(), f"f[{e.id}]")

    for n in spec.nodes:
        if n.type == "process":
            r_proc[n.id] = s.NumVar(0.0, s.infinity(), f"r[{n.id}]")

    # Build adjacency per commodity for conservation
    edges_by_u_comm: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    edges_by_v_comm: Dict[Tuple[str, str], List[str]] = defaultdict(list)

    # Collect commodities from edges + node payloads (more robust)
    commodities: Set[str] = set()
    for e in spec.edges:
        commodities.add(e.commodity)
        edges_by_u_comm[(e.u, e.commodity)].append(e.id)
        edges_by_v_comm[(e.v, e.commodity)].append(e.id)

    for n in spec.nodes:
        if n.type == "source" and n.source is not None:
            commodities.add(n.source.commodity)
        if n.type == "sink" and n.sink is not None:
            commodities.add(n.sink.commodity)
        if n.type == "process" and n.process is not None:
            for io in n.process.inputs:
                commodities.add(io.commodity)
            for io in n.process.outputs:
                commodities.add(io.commodity)

    # Edge capacity constraints
    edge_caps: Dict[str, float] = {}
    for e in spec.edges:
        if e.cap is not None:
            edge_caps[e.id] = float(e.cap)
            s.Add(f_edge[e.id] <= e.cap, f"cap_edge[{e.id}]")

    # Source supply constraints and store expr for objective
    source_supply_caps: Dict[str, float] = {}
    source_outflow_expr: Dict[str, pywraplp.LinearExpr] = {}
    for n in spec.nodes:
        if n.type != "source" or n.source is None:
            continue
        c = n.source.commodity
        out_ids = edges_by_u_comm.get((n.id, c), [])
        outflow = sum(f_edge[eid] for eid in out_ids) if out_ids else 0.0
        source_outflow_expr[n.id] = outflow
        source_supply_caps[n.id] = float(n.source.supply_cap)
        s.Add(outflow <= n.source.supply_cap, f"supply[{n.id}]")

    # Sink demand constraints and store delivered expr for objective
    sink_demand_caps: Dict[str, float] = {}
    sink_delivered_expr: Dict[str, pywraplp.LinearExpr] = {}
    for n in spec.nodes:
        if n.type != "sink" or n.sink is None:
            continue
        c = n.sink.commodity
        in_ids = edges_by_v_comm.get((n.id, c), [])
        inflow = sum(f_edge[eid] for eid in in_ids) if in_ids else 0.0
        sink_delivered_expr[n.id] = inflow
        sink_demand_caps[n.id] = float(n.sink.demand_cap)
        s.Add(inflow <= n.sink.demand_cap, f"demand[{n.id}]")

    # Process run capacity
    proc_run_caps: Dict[str, float] = {}
    for n in spec.nodes:
        if n.type == "process" and n.process is not None and n.process.run_cap is not None:
            proc_run_caps[n.id] = float(n.process.run_cap)
            s.Add(r_proc[n.id] <= n.process.run_cap, f"run_cap[{n.id}]")

    # (safety) enforce that sources don't accept inflow and sinks don't emit outflow.
    for n in spec.nodes:
        for c in commodities:
            out_ids = edges_by_u_comm.get((n.id, c), [])
            in_ids = edges_by_v_comm.get((n.id, c), [])
            outflow = sum(f_edge[eid] for eid in out_ids) if out_ids else 0.0
            inflow = sum(f_edge[eid] for eid in in_ids) if in_ids else 0.0

            if n.type == "source":
                # No inflow to sources (topology sanity)
                if in_ids:
                    s.Add(inflow == 0.0, f"no_in_to_source[{n.id},{c}]")
            elif n.type == "sink":
                # No outflow from sinks (topology sanity)
                if out_ids:
                    s.Add(outflow == 0.0, f"no_out_from_sink[{n.id},{c}]")

    # Flow conservation for each node and commodity:
    # For process: out - in = r * (produced - consumed)
    for n in spec.nodes:
        for c in commodities:
            out_ids = edges_by_u_comm.get((n.id, c), [])
            in_ids = edges_by_v_comm.get((n.id, c), [])

            outflow = sum(f_edge[eid] for eid in out_ids) if out_ids else 0.0
            inflow = sum(f_edge[eid] for eid in in_ids) if in_ids else 0.0

            if n.type == "process" and n.process is not None:
                produced = sum(o.qty for o in n.process.outputs if o.commodity == c)
                consumed = sum(i.qty for i in n.process.inputs if i.commodity == c)
                s.Add(
                    outflow - inflow == r_proc[n.id] * (produced - consumed),
                    f"cons[{n.id},{c}]",
                )
            # supply/demand constraints already handle these nodes

    # Objective
    obj = spec.options.objective
    objective_expr = 0.0

    if obj.kind == "max_profit":
        # Revenue from sinks
        for n in spec.nodes:
            if n.type == "sink" and n.sink is not None:
                delivered = sink_delivered_expr.get(n.id, 0.0)
                objective_expr += float(n.sink.unit_value) * delivered

        # Costs from sources
        for n in spec.nodes:
            if n.type == "source" and n.source is not None:
                outflow = source_outflow_expr.get(n.id, 0.0)
                objective_expr -= float(n.source.unit_cost) * outflow

        # Edge costs
        for e in spec.edges:
            objective_expr -= float(e.unit_cost) * f_edge[e.id]

        # Process costs
        for n in spec.nodes:
            if n.type == "process" and n.process is not None:
                objective_expr -= float(n.process.run_cost) * r_proc[n.id]

        s.Maximize(objective_expr)

    elif obj.kind == "max_flow_to_sink":
        sink_id = obj.sink_node_id
        if sink_id is None:
            raise DomainError("objective.kind='max_flow_to_sink' requires objective.sink_node_id.")
        delivered = sink_delivered_expr.get(sink_id, 0.0)
        s.Maximize(delivered)

    return LPBuild(
        solver=s,
        f_edge=f_edge,
        r_proc=r_proc,
        edge_caps=edge_caps,
        source_supply_caps=source_supply_caps,
        sink_demand_caps=sink_demand_caps,
        proc_run_caps=proc_run_caps,
        edges_by_u_comm=edges_by_u_comm,
        edges_by_v_comm=edges_by_v_comm,
        sink_delivered_expr=sink_delivered_expr,
        source_outflow_expr=source_outflow_expr,
    )
