from __future__ import annotations

import pytest

from app.solvers.lp.solver import solve_lp
from tests.graph_scenario_factory import GraphScenarioFactory


class TestLPSolver:
    def test_solve_lp_simple_source_sink_optimal(self):
        req = GraphScenarioFactory.simple_source_sink()
        res = solve_lp(req)

        assert res.status == "optimal"
        assert res.objective_value is not None
        assert res.edge_flows["e1"] == pytest.approx(50.0)
        assert res.sink_delivered["snk"] == pytest.approx(50.0)

    def test_solve_lp_bottleneck_edge_reports_tight_edge_cap(self):
        req = GraphScenarioFactory.bottleneck_edge()
        res = solve_lp(req)

        assert res.status == "optimal"
        names = [tc.name for tc in res.tight_constraints]
        assert "edge_cap:e_in" in names
