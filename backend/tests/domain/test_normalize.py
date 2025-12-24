from app.domain.normalize import normalize_request
from tests.graph_scenario_factory import GraphScenarioFactory


class TestNormalize:
    def test_normalize_request_identity(self):
        """Ensure normalize_request returns the request as-is (current behavior)."""
        req = GraphScenarioFactory.simple_source_sink()
        normalized = normalize_request(req)
        assert normalized == req
        assert normalized is req
