from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List, Set

from app.core.errors import DomainError
from app.domain.schema import EdgeSpec, NodeSpec, NodeType, SolveRequest, ObjectiveKind


def validate_request(req: SolveRequest) -> None:
    # Unique ID validation
    node_ids = [n.id for n in req.nodes]
    if len(set(node_ids)) != len(node_ids):
        raise DomainError("Duplicate node IDs found.")

    edge_ids = [e.id for e in req.edges]
    if len(set(edge_ids)) != len(edge_ids):
        raise DomainError("Duplicate edge IDs found.")

    nodes_by_id: Dict[str, NodeSpec] = {n.id: n for n in req.nodes}

    # Node level validation
    for n in req.nodes:
        _validate_node_shape(n)
        if n.type == NodeType.PROCESS:
            _validate_process_node(n)

    # Edge level validation
    for e in req.edges:
        _edge_references_valid_node(e, nodes_by_id)
        _edge_direction_is_correct(e, nodes_by_id)

        u = nodes_by_id[e.u]
        v = nodes_by_id[e.v]

        _edge_commodity_is_produced_by_u(e, u)
        _edge_commodity_is_accepted_by_v(e, v)

    # Objective level validation
    obj = req.options.objective
    if obj.kind != ObjectiveKind.MAX_PROFIT:
        raise DomainError(f"Objective '{obj.kind}' is not yet implemented.")

    # Sanity: if a sink has positive demand, some producer of that commodity should reach it via that commodity's edges.
    _validate_sink_reachability(req)


def _validate_node_shape(n: NodeSpec) -> None:
    if n.type == NodeType.SOURCE:
        if n.source is None:
            raise DomainError(f"Source node '{n.id}' must include 'source' spec.")
    elif n.type == NodeType.SINK:
        if n.sink is None:
            raise DomainError(f"Sink node '{n.id}' must include 'sink' spec.")
    elif n.type == NodeType.PROCESS:
        if n.process is None:
            raise DomainError(f"Process node '{n.id}' must include 'process' spec.")


def _validate_process_node(n: NodeSpec) -> None:
    assert n.process is not None

    if not n.process.inputs:
        raise DomainError(f"Process node '{n.id}' must have at least one input.")
    if not n.process.outputs:
        raise DomainError(f"Process node '{n.id}' must have at least one output.")

    # Input and output commodities must be unique
    _validate_unique_io_commodities(
        n.id, "inputs", [io.commodity for io in n.process.inputs]
    )
    _validate_unique_io_commodities(
        n.id, "outputs", [io.commodity for io in n.process.outputs]
    )


def _validate_unique_io_commodities(node_id: str, field: str, comms: List[str]) -> None:
    if len(set(comms)) == len(comms):
        return

    counts: Dict[str, int] = defaultdict(int)
    for c in comms:
        counts[c] += 1
    dups = sorted([c for c, k in counts.items() if k > 1])

    raise DomainError(
        f"Process node '{node_id}' has duplicate commodities in process.{field}: {dups}. "
        f"Use a single entry per commodity."
    )


def _edge_references_valid_node(e: EdgeSpec, nodes_by_id: Dict[str, NodeSpec]) -> None:
    if e.u not in nodes_by_id:
        raise DomainError(f"Edge '{e.id}' references missing node u='{e.u}'.")
    if e.v not in nodes_by_id:
        raise DomainError(f"Edge '{e.id}' references missing node v='{e.v}'.")
    if e.u == e.v:
        raise DomainError(f"Edge '{e.id}' has self-loop '{e.u}'. Not supported.")


def _edge_direction_is_correct(e: EdgeSpec, nodes_by_id: Dict[str, NodeSpec]) -> None:
    node_u = nodes_by_id[e.u]
    node_v = nodes_by_id[e.v]

    if node_u.type == NodeType.SINK:
        raise DomainError(
            f"Edge '{e.id}' cannot originate from sink node '{node_u.id}'."
        )
    if node_v.type == NodeType.SOURCE:
        raise DomainError(f"Edge '{e.id}' cannot point into source node '{node_v.id}'.")


def _edge_commodity_is_produced_by_u(e: EdgeSpec, u: NodeSpec) -> None:
    produced = _produced_commodities(u)
    if e.commodity not in produced:
        raise DomainError(
            f"Edge '{e.id}' carries '{e.commodity}', but node '{u.id}' (type={u.type.value}) "
            f"does not produce it. Produces: {sorted(produced) if produced else '∅'}"
        )


def _edge_commodity_is_accepted_by_v(e: EdgeSpec, v: NodeSpec) -> None:
    accepted = _accepted_commodities(v)
    if e.commodity not in accepted:
        raise DomainError(
            f"Edge '{e.id}' carries '{e.commodity}', but node '{v.id}' (type={v.type.value}) "
            f"does not accept it. Accepts: {sorted(accepted) if accepted else '∅'}"
        )


def _produced_commodities(n: NodeSpec) -> Set[str]:
    if n.type == NodeType.SOURCE:
        return {n.source.commodity} if n.source else set()
    if n.type == NodeType.PROCESS:
        return {io.commodity for io in n.process.outputs} if n.process else set()
    return set()


def _accepted_commodities(n: NodeSpec) -> Set[str]:
    if n.type == NodeType.SINK:
        return {n.sink.commodity} if n.sink else set()
    if n.type == NodeType.PROCESS:
        return {io.commodity for io in n.process.inputs} if n.process else set()
    return set()


def _validate_sink_reachability(req: SolveRequest) -> None:
    # Reverse adjacency per commodity: radj[commodity][v] = [u...]
    radj: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for e in req.edges:
        radj[e.commodity][e.v].append(e.u)

    # Producers per commodity: sources that provide it OR processes that output it
    producers_by_comm: Dict[str, Set[str]] = defaultdict(set)
    for n in req.nodes:
        if n.type == NodeType.SOURCE and n.source is not None:
            producers_by_comm[n.source.commodity].add(n.id)
        elif n.type == NodeType.PROCESS and n.process is not None:
            for out in n.process.outputs:
                producers_by_comm[out.commodity].add(n.id)

    # For each sink node with positive demand, check at least one producer can reach it
    for n in req.nodes:
        if n.type != NodeType.SINK or n.sink is None:
            continue

        comm = n.sink.commodity
        if n.sink.demand_cap <= 0:
            continue

        producers = producers_by_comm.get(comm, set())
        if not producers:
            raise DomainError(
                f"Sink '{n.id}' demands '{comm}', but no node produces '{comm}'."
            )

        if not _reverse_reachable_from_any_producer(radj[comm], producers, n.id):
            raise DomainError(
                f"Sink '{n.id}' demands '{comm}', but no producer of '{comm}' can reach it "
                f"via edges carrying '{comm}'."
            )


def _reverse_reachable_from_any_producer(
    radj_comm: Dict[str, List[str]],
    producers: Set[str],
    sink_id: str,
) -> bool:
    q: Deque[str] = deque([sink_id])
    seen = {sink_id}

    while q:
        v = q.popleft()
        if v in producers:
            return True
        for u in radj_comm.get(v, []):
            if u not in seen:
                seen.add(u)
                q.append(u)

    return False
