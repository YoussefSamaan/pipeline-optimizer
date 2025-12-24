import pytest
from app.domain.validate import validate_request
from app.core.errors import DomainError
from tests.graph_scenario_factory import GraphScenarioFactory


class TestValidate:
    def test_validate_request_valid(self):
        """Test a perfectly valid request."""
        # Simple Water -> Sink flow
        req = GraphScenarioFactory.simple_source_sink()
        # Should not raise
        validate_request(req)

    def test_duplicate_node_ids(self):
        req = GraphScenarioFactory.duplicate_node_ids()
        with pytest.raises(DomainError, match="Duplicate node IDs found"):
            validate_request(req)

    def test_duplicate_edge_ids(self):
        req = GraphScenarioFactory.duplicate_edge_ids()
        with pytest.raises(DomainError, match="Duplicate edge IDs found"):
            validate_request(req)

    def test_from_edge_references_missing_node(self):
        req = GraphScenarioFactory.missing_u_node()
        with pytest.raises(
            DomainError, match="Edge 'e1' references missing node u='missing_node'"
        ):
            validate_request(req)

    def test_to_edge_references_missing_node(self):
        req = GraphScenarioFactory.missing_v_node()
        with pytest.raises(
            DomainError, match="Edge 'e1' references missing node v='missing_node'"
        ):
            validate_request(req)

    def test_edge_self_loop(self):
        req = GraphScenarioFactory.self_loop_edge()
        with pytest.raises(DomainError, match="Edge 'e1' has self-loop 'n1'"):
            validate_request(req)

    def test_process_node_no_inputs(self):
        req = GraphScenarioFactory.process_no_inputs_domain()
        with pytest.raises(
            DomainError, match="Process node 'p1' must have at least one input"
        ):
            validate_request(req)

    def test_process_node_no_outputs(self):
        req = GraphScenarioFactory.process_no_outputs_domain()
        with pytest.raises(
            DomainError, match="Process node 'p1' must have at least one output"
        ):
            validate_request(req)

    def test_max_flow_no_sink_id(self):
        """Test that max_flow_to_sink requires a sink_node_id."""
        req = GraphScenarioFactory.simple_source_sink()
        req.options.objective.kind = "max_flow_to_sink"
        req.options.objective.sink_node_id = None

        with pytest.raises(DomainError, match="requires objective.sink_node_id"):
            validate_request(req)

    def test_max_flow_invalid_sink_id(self):
        """Test that max_flow_to_sink fails if sink_node_id does not exist."""
        req = GraphScenarioFactory.simple_source_sink()
        req.options.objective.kind = "max_flow_to_sink"
        req.options.objective.sink_node_id = "missing"

        with pytest.raises(
            DomainError, match="objective.sink_node_id 'missing' not found"
        ):
            validate_request(req)

    def test_max_flow_sink_id_not_sink_type(self):
        """Test that sink_node_id must point to a node of type 'sink'."""
        req = GraphScenarioFactory.simple_source_sink()
        req.options.objective.kind = "max_flow_to_sink"
        # 'src' is a source node, not a sink
        req.options.objective.sink_node_id = "src"

        with pytest.raises(
            DomainError,
            match="objective.sink_node_id must point to a node of type 'sink'",
        ):
            validate_request(req)

    def test_sink_reachability_no_producer(self):
        # Sink demands 'B' (gold), but only 'A' (water) is produced
        req = GraphScenarioFactory.sink_unproduced_commodity()

        # The factory scenario has Sink(Gold) and Source(Water).
        # Verify validation error message matches.
        with pytest.raises(
            DomainError, match="demands 'gold', but no node produces 'gold'"
        ):
            validate_request(req)

    def test_sink_demands_no_producers_zero_cap(self):
        """
        If a sink demands a commodity that no one produces, but demand_cap is 0,
        it should NOT raise an error (it's effectively a disabled sink).
        """
        req = GraphScenarioFactory.simple_source_sink()
        # Change sink to demand "Unknown" but with 0 cap
        req.nodes[1].sink.commodity = "Unknown"
        req.nodes[1].sink.demand_cap = 0.0

        validate_request(req)

    def test_sink_demands_no_producers_positive_cap(self):
        """
        If a sink demands a commodity that no one produces, and demand_cap > 0,
        it MUST raise an error.
        """
        req = GraphScenarioFactory.simple_source_sink()
        # Change sink to demand "Unknown" with positive cap
        req.nodes[1].sink.commodity = "Unknown"
        req.nodes[1].sink.demand_cap = 10.0

        with pytest.raises(
            DomainError, match="demands 'Unknown', but no node produces 'Unknown'"
        ):
            validate_request(req)

    def test_sink_reachability_disconnected(self):
        # 'A' is produced, but not connected to sink
        req = GraphScenarioFactory.sink_disconnected()
        with pytest.raises(
            DomainError, match="demands 'a', but no producer can reach it"
        ):
            validate_request(req)

    def test_sink_reachability_valid_process_chain(self):
        # Source(A) -> Process(A->B) -> Sink(B)
        req = GraphScenarioFactory.process_chain()
        validate_request(req)
