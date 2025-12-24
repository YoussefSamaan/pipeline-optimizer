from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Set

from app.core.errors import DomainError
from app.domain.schema import SolveRequest


def validate_request(req: SolveRequest) -> None:
    # Unique node IDs
    node_ids = [n.id for n in req.nodes]
    if len(set(node_ids)) != len(node_ids):
        raise DomainError("Duplicate node IDs found.")

    nodes_by_id = {n.id: n for n in req.nodes}

    # Unique edge IDs
    edge_ids = [e.id for e in req.edges]
    if len(set(edge_ids)) != len(edge_ids):
        raise DomainError("Duplicate edge IDs found.")

    # Edges reference valid nodes
    for e in req.edges:
        if e.u not in nodes_by_id:
            raise DomainError(f"Edge '{e.id}' references missing node u='{e.u}'.")
        if e.v not in nodes_by_id:
            raise DomainError(f"Edge '{e.id}' references missing node v='{e.v}'.")
        if e.u == e.v:
            raise DomainError(
                f"Edge '{e.id}' has self-loop '{e.u}'. Not currently supported."
            )

    # Process nodes need at least 1 input and 1 output
    for n in req.nodes:
        if n.type == "process":
            assert n.process is not None
            if len(n.process.inputs) == 0:
                raise DomainError(
                    f"Process node '{n.id}' must have at least one input."
                )
            if len(n.process.outputs) == 0:
                raise DomainError(
                    f"Process node '{n.id}' must have at least one output."
                )

    # Objective sanity
    obj = req.options.objective
    if obj.kind == "max_flow_to_sink":
        if not obj.sink_node_id:
            raise DomainError(
                "objective.kind='max_flow_to_sink' requires objective.sink_node_id."
            )
        if obj.sink_node_id not in nodes_by_id:
            raise DomainError(f"objective.sink_node_id '{obj.sink_node_id}' not found.")
        if nodes_by_id[obj.sink_node_id].type != "sink":
            raise DomainError(
                "objective.sink_node_id must point to a node of type 'sink'."
            )

    # Quick reachability sanity:
    # For each sink commodity, ensure there exists a directed path from *some* producer
    # (source or process that outputs that commodity) to that sink node.
    _validate_sink_reachability(req)


def _validate_sink_reachability(req: SolveRequest) -> None:
    adj = defaultdict(list)
    for e in req.edges:
        adj[e.u].append(e.v)

    # Producer set by commodity: sources that provide it OR processes that output it
    producers_by_comm: Dict[str, Set[str]] = defaultdict(set)
    for n in req.nodes:
        if n.type == "source" and n.source is not None:
            producers_by_comm[n.source.commodity].add(n.id)
        if n.type == "process" and n.process is not None:
            for out in n.process.outputs:
                producers_by_comm[out.commodity].add(n.id)

    for n in req.nodes:
        if n.type != "sink" or n.sink is None:
            continue
        comm = n.sink.commodity
        producers = producers_by_comm.get(comm, set())
        if not producers:
            # no one produces the commodity at all (still might be ok if demand_cap=0, but keep strict)
            if n.sink.demand_cap > 0:
                raise DomainError(
                    f"Sink '{n.id}' demands '{comm}', but no node produces '{comm}'."
                )
            continue

        if not _any_path_exists(adj, producers, n.id):
            if n.sink.demand_cap > 0:
                raise DomainError(
                    f"Sink '{n.id}' demands '{comm}', but no producer can reach it in the graph."
                )


def _any_path_exists(adj: Dict[str, list], starts: Set[str], target: str) -> bool:
    q = deque(starts)
    seen = set(starts)
    while q:
        u = q.popleft()
        if u == target:
            return True
        for v in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                q.append(v)
    return target in seen
