import pytest
from types import SimpleNamespace
from unittest.mock import patch

from tests.graph_scenario_factory import GraphScenarioFactory


class TestSolveAPI:
    def test_solve_api_valid(self, client):
        req = GraphScenarioFactory.simple_source_sink()
        payload = GraphScenarioFactory.to_json(req)

        r = client.post("/v1/solve", json=payload)
        data = r.json()

        assert r.status_code == 200
        assert data["status"] == "optimal"
        assert data["objective_value"] == pytest.approx(450.0)
        assert data["sink_delivered"]["snk"] == pytest.approx(50.0)
        assert "edge_flows" in data

    def test_solve_api_unsupported_mode(self, client):
        import app.api.v1.solve as solve_mod

        req = GraphScenarioFactory.simple_source_sink()
        body = GraphScenarioFactory.to_json(req)

        normalized_req = SimpleNamespace(options=SimpleNamespace(mode="invalid_mode"))

        with (
            patch.object(solve_mod, "normalize_request", return_value=normalized_req),
            patch.object(solve_mod, "validate_request", return_value=None),
        ):
            r = client.post("/v1/solve", json=body)

        data = r.json()

        assert r.status_code == 200
        assert data["status"] == "error"
        assert (
            data["message"]
            == "Mode 'invalid_mode' not implemented yet (supports mode='lp')."
        )
        assert data["objective_value"] is None

    def test_solve_api_domain_error_returns_400(self, client):
        import app.api.v1.solve as solve_mod
        from app.core.errors import DomainError

        req = GraphScenarioFactory.simple_source_sink()
        body = GraphScenarioFactory.to_json(req)

        with patch.object(
            solve_mod, "validate_request", side_effect=DomainError("bad graph")
        ):
            r = client.post("/v1/solve", json=body)

        assert r.status_code == 400

    def test_solve_api_schema_invalid_returns_422(self, client):
        body = GraphScenarioFactory.json_negative_supply_cap()
        r = client.post("/v1/solve", json=body)
        assert r.status_code == 422
