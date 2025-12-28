import pytest
from unittest.mock import patch

from app.core.errors import DomainError
from app.domain.schema import (
    EdgeSpec,
    NodeSpec,
    NodeType,
    ProcessData,
    ProcessIO,
    SinkData,
    SolveObjective,
    SolveOptions,
    SolveRequest,
    SourceData,
    ObjectiveKind,
)
from app.domain.validate import validate_request
from tests.graph_scenario_factory import GraphScenarioFactory


def _req(nodes, edges=None, objective=None) -> SolveRequest:
    return SolveRequest(
        nodes=nodes,
        edges=edges or [],
        options=SolveOptions(
            objective=objective or SolveObjective(kind=ObjectiveKind.MAX_PROFIT)
        ),
    )


class TestValidate:
    @pytest.mark.parametrize("req", GraphScenarioFactory.valid())
    def test_validate_request_valid(self, req: SolveRequest):
        validate_request(req)

    @pytest.mark.parametrize(
        "req,pattern",
        [
            (GraphScenarioFactory.duplicate_node_ids(), r"Duplicate node IDs found"),
            (GraphScenarioFactory.duplicate_edge_ids(), r"Duplicate edge IDs found"),
            (
                GraphScenarioFactory.missing_u_node(),
                r"references missing node u='missing_node'",
            ),
            (
                GraphScenarioFactory.missing_v_node(),
                r"references missing node v='missing_node'",
            ),
            (GraphScenarioFactory.self_loop_edge(), r"has self-loop"),
            (
                GraphScenarioFactory.process_no_inputs_domain(),
                r"must have at least one input",
            ),
            (
                GraphScenarioFactory.process_no_outputs_domain(),
                r"must have at least one output",
            ),
            (
                GraphScenarioFactory.sink_unproduced_commodity(),
                r"no node produces 'gold'",
            ),
            (GraphScenarioFactory.sink_disconnected(), r"can reach it"),
        ],
    )
    def test_validate_request_domain_invalid(self, req: SolveRequest, pattern: str):
        with pytest.raises(DomainError, match=pattern):
            validate_request(req)

    def test_edge_cannot_originate_from_sink(self):
        sink = NodeSpec(
            id="s1", type=NodeType.SINK, sink=SinkData(commodity="a", demand_cap=1)
        )
        proc = NodeSpec(
            id="p1",
            type=NodeType.PROCESS,
            process=ProcessData(
                inputs=[ProcessIO(commodity="a", qty=1)],
                outputs=[ProcessIO(commodity="a", qty=1)],
            ),
        )
        e = EdgeSpec(id="e1", u="s1", v="p1", commodity="a")

        with pytest.raises(DomainError, match=r"cannot originate from sink"):
            validate_request(_req([sink, proc], [e]))

    def test_edge_cannot_point_into_source(self):
        src = NodeSpec(
            id="src",
            type=NodeType.SOURCE,
            source=SourceData(commodity="a", supply_cap=10),
        )
        proc = NodeSpec(
            id="p1",
            type=NodeType.PROCESS,
            process=ProcessData(
                inputs=[ProcessIO(commodity="a", qty=1)],
                outputs=[ProcessIO(commodity="a", qty=1)],
            ),
        )
        e = EdgeSpec(id="e1", u="p1", v="src", commodity="a")

        with pytest.raises(DomainError, match=r"cannot point into source"):
            validate_request(_req([src, proc], [e]))

    def test_edge_commodity_not_produced_by_u(self):
        src = NodeSpec(
            id="src",
            type=NodeType.SOURCE,
            source=SourceData(commodity="a", supply_cap=10),
        )
        sink = NodeSpec(
            id="snk", type=NodeType.SINK, sink=SinkData(commodity="b", demand_cap=1)
        )
        e = EdgeSpec(id="e1", u="src", v="snk", commodity="b")

        with pytest.raises(DomainError, match=r"does not produce it"):
            validate_request(_req([src, sink], [e]))

    def test_edge_commodity_not_accepted_by_v(self):
        src = NodeSpec(
            id="src",
            type=NodeType.SOURCE,
            source=SourceData(commodity="a", supply_cap=10),
        )
        sink = NodeSpec(
            id="snk", type=NodeType.SINK, sink=SinkData(commodity="b", demand_cap=1)
        )
        e = EdgeSpec(id="e1", u="src", v="snk", commodity="a")

        with pytest.raises(DomainError, match=r"does not accept it"):
            validate_request(_req([src, sink], [e]))

    def test_process_duplicate_input_commodities(self):
        proc = NodeSpec(
            id="p1",
            type=NodeType.PROCESS,
            process=ProcessData(
                inputs=[
                    ProcessIO(commodity="a", qty=1),
                    ProcessIO(commodity="a", qty=2),
                ],
                outputs=[ProcessIO(commodity="b", qty=1)],
            ),
        )

        with pytest.raises(
            DomainError, match=r"duplicate commodities in process\.inputs"
        ):
            validate_request(_req([proc], []))

    def test_process_duplicate_output_commodities(self):
        proc = NodeSpec(
            id="p1",
            type=NodeType.PROCESS,
            process=ProcessData(
                inputs=[ProcessIO(commodity="a", qty=1)],
                outputs=[
                    ProcessIO(commodity="b", qty=1),
                    ProcessIO(commodity="b", qty=2),
                ],
            ),
        )

        with pytest.raises(
            DomainError, match=r"duplicate commodities in process\.outputs"
        ):
            validate_request(_req([proc], []))

    @pytest.mark.parametrize(
        "kind",
        [
            ObjectiveKind.MAX_SINK_CONSUMPTION,
            ObjectiveKind.MAX_PRODUCTION,
            ObjectiveKind.MAX_PROCESS_RUNS,
            ObjectiveKind.MIN_COST,
            ObjectiveKind.MIN_TOTAL_PROCESS_RUNS,
        ],
    )
    def test_unimplemented_objective_raises(self, kind: ObjectiveKind):
        req = _req([], [])
        req.options.objective.kind = kind

        with pytest.raises(
            DomainError, match=f"Objective '{kind}' is not yet implemented"
        ):
            validate_request(req)

    def test_sink_demand_zero_skips_reachability(self):
        sink = NodeSpec(
            id="snk", type=NodeType.SINK, sink=SinkData(commodity="x", demand_cap=0)
        )
        validate_request(_req([sink], []))

    def test_node_shape_checks_are_defensive(self):
        bad_src = NodeSpec.model_construct(
            id="src",
            type=NodeType.SOURCE,
            name=None,
            source=None,
            sink=None,
            process=None,
        )
        bad_snk = NodeSpec.model_construct(
            id="snk",
            type=NodeType.SINK,
            name=None,
            source=None,
            sink=None,
            process=None,
        )
        bad_proc = NodeSpec.model_construct(
            id="p1",
            type=NodeType.PROCESS,
            name=None,
            source=None,
            sink=None,
            process=None,
        )

        req1 = SolveRequest.model_construct(
            nodes=[bad_src], edges=[], options=SolveOptions()
        )
        req2 = SolveRequest.model_construct(
            nodes=[bad_snk], edges=[], options=SolveOptions()
        )
        req3 = SolveRequest.model_construct(
            nodes=[bad_proc], edges=[], options=SolveOptions()
        )

        with pytest.raises(DomainError, match=r"must include 'source' spec"):
            validate_request(req1)
        with pytest.raises(DomainError, match=r"must include 'sink' spec"):
            validate_request(req2)
        with pytest.raises(DomainError, match=r"must include 'process' spec"):
            validate_request(req3)

    def test_reachability_failure_is_propagated_with_mock(self):
        req = GraphScenarioFactory.simple_source_sink()

        with patch(
            "app.domain.validate._reverse_reachable_from_any_producer",
            return_value=False,
        ):
            with pytest.raises(DomainError, match=r"can reach it"):
                validate_request(req)

    def test_produced_commodities_mock_forces_production_error(self):
        req = GraphScenarioFactory.simple_source_sink()

        with patch("app.domain.validate._produced_commodities", return_value=set()):
            with pytest.raises(DomainError, match=r"does not produce it"):
                validate_request(req)

    def test_accepted_commodities_mock_forces_accept_error(self):
        req = GraphScenarioFactory.simple_source_sink()

        with patch("app.domain.validate._accepted_commodities", return_value=set()):
            with pytest.raises(DomainError, match=r"does not accept it"):
                validate_request(req)

    def test_cover_produced_commodities_final_return_set_with_mock(self):
        # Edge level validation (force u=sink by bypassing direction check)
        u = NodeSpec(
            id="u_sink", type=NodeType.SINK, sink=SinkData(commodity="a", demand_cap=1)
        )
        v = NodeSpec(
            id="v_sink", type=NodeType.SINK, sink=SinkData(commodity="a", demand_cap=1)
        )
        e = EdgeSpec(id="e1", u="u_sink", v="v_sink", commodity="a")
        req = SolveRequest(nodes=[u, v], edges=[e], options=SolveOptions())

        with patch("app.domain.validate._edge_direction_is_correct", return_value=None):
            with pytest.raises(DomainError, match=r"does not produce it"):
                validate_request(req)

    def test_cover_accepted_commodities_final_return_set_with_mock(self):
        # Edge level validation (force v=source by bypassing direction check)
        u = NodeSpec(
            id="u_src",
            type=NodeType.SOURCE,
            source=SourceData(commodity="a", supply_cap=10),
        )
        v = NodeSpec(
            id="v_src",
            type=NodeType.SOURCE,
            source=SourceData(commodity="b", supply_cap=10),
        )
        e = EdgeSpec(id="e1", u="u_src", v="v_src", commodity="a")
        req = SolveRequest(nodes=[u, v], edges=[e], options=SolveOptions())

        with patch("app.domain.validate._edge_direction_is_correct", return_value=None):
            with pytest.raises(DomainError, match=r"does not accept it"):
                validate_request(req)
