from __future__ import annotations

import pytest
from ortools.linear_solver import pywraplp

from app.solvers.lp.build import build_lp
from app.solvers.lp.extract import extract_solution, _compute_tight_constraints

from tests.graph_scenario_factory import GraphScenarioFactory


class TestExtractSolution:
    # ----------------------------
    # Status mapping / early returns
    # ----------------------------

    def test_extract_solution_optimal_happy_path(self):
        req = GraphScenarioFactory.simple_source_sink()
        built = build_lp(req)

        res = extract_solution(req, built)

        assert res.status == "optimal"
        assert res.objective_value is not None
        assert res.message is None
        assert "e1" in res.edge_flows
        assert isinstance(res.process_runs, dict)
        assert "snk" in res.sink_delivered

    def test_extract_solution_feasible_maps_to_optimal_with_message(self, monkeypatch):
        req = GraphScenarioFactory.simple_source_sink()
        built = build_lp(req)

        monkeypatch.setattr(built.solver, "Solve", lambda: pywraplp.Solver.FEASIBLE)

        res = extract_solution(req, built)
        assert res.status == "optimal"
        assert res.message is not None
        assert "feasible" in res.message.lower()

    @pytest.mark.parametrize(
        "status, expected, msg_substr",
        [
            (pywraplp.Solver.INFEASIBLE, "infeasible", "infeasible"),
            (pywraplp.Solver.UNBOUNDED, "unbounded", "unbounded"),
            (pywraplp.Solver.MODEL_INVALID, "error", "invalid"),
            (pywraplp.Solver.NOT_SOLVED, "error", "not solved"),
            (pywraplp.Solver.ABNORMAL, "error", "abnormally"),
        ],
    )
    def test_extract_solution_nonoptimal_returns_empty_result(
        self, monkeypatch, status, expected, msg_substr
    ):
        req = GraphScenarioFactory.simple_source_sink()
        built = build_lp(req)

        monkeypatch.setattr(built.solver, "Solve", lambda: status)

        res = extract_solution(req, built)

        assert res.status == expected
        assert res.objective_value is None
        assert res.edge_flows == {}
        assert res.process_runs == {}
        assert res.sink_delivered == {}
        assert res.tight_constraints == []
        assert res.message is not None
        assert msg_substr in res.message.lower()

    def test_extract_solution_unknown_status_returns_error(self, monkeypatch):
        req = GraphScenarioFactory.simple_source_sink()
        built = build_lp(req)

        monkeypatch.setattr(built.solver, "Solve", lambda: 999999)

        res = extract_solution(req, built)

        assert res.status == "error"
        assert res.objective_value is None
        assert res.edge_flows == {}
        assert res.process_runs == {}
        assert res.sink_delivered == {}
        assert res.tight_constraints == []
        assert res.message is not None
        assert "unknown solver status" in res.message.lower()

    # ----------------------------
    # sink_delivered extraction: expr + float branches
    # ----------------------------

    def test_sink_delivered_expr_missing_uses_float_zero_branch(self):
        """
        Covers the `except AttributeError: val = float(expr)` branch by using a sink
        with no inflow edges so sink_delivered_expr.get(..., 0.0) returns float 0.0.
        """
        req = GraphScenarioFactory.sink_disconnected()
        built = build_lp(req)

        res = extract_solution(req, built)

        # Your LP (as written) is feasible with 0 flow, so should be optimal.
        assert res.status == "optimal"
        assert res.sink_delivered["snk"] == pytest.approx(0.0)

    # ----------------------------
    # Tight constraint detection (each type)
    # ----------------------------

    def test_tight_constraints_edge_cap_detected(self):
        """
        bottleneck_edge has edge e_in cap=7, profitable sink => optimal saturates e_in.
        """
        req = GraphScenarioFactory.bottleneck_edge()
        built = build_lp(req)

        res = extract_solution(req, built)

        assert res.status == "optimal"
        names = [tc.name for tc in res.tight_constraints]
        assert "edge_cap:e_in" in names

    def test_tight_constraints_process_run_cap_detected(self):
        """
        process_chain_with_run_cap has run_cap=3 and profitable sink => saturates run cap.
        """
        req = GraphScenarioFactory.process_chain_with_run_cap()
        built = build_lp(req)

        res = extract_solution(req, built)

        assert res.status == "optimal"
        assert res.process_runs["p"] == pytest.approx(3.0)
        names = [tc.name for tc in res.tight_constraints]
        assert "process_run_cap:p" in names

    def test_tight_constraints_sink_demand_detected_simple_source_sink(self):
        """
        In simple_source_sink: supply=100, demand=50, profit positive => demand binds.
        """
        req = GraphScenarioFactory.simple_source_sink()
        built = build_lp(req)

        res = extract_solution(req, built)

        assert res.status == "optimal"
        # demand should bind at 50
        assert res.sink_delivered["snk"] == pytest.approx(50.0)

        names = [tc.name for tc in res.tight_constraints]
        assert "sink_demand:snk" in names

    def test_tight_constraints_source_supply_detected_by_modifying_factory_scenario(
        self,
    ):
        """
        Creates a source-supply bottleneck by lowering supply_cap below demand_cap.
        This avoids needing a brand-new factory method.
        """
        req = GraphScenarioFactory.simple_source_sink()

        # Make supply the bottleneck: supply 7, demand 50
        for n in req.nodes:
            if n.type == "source" and n.source is not None:
                n.source.supply_cap = 7  # type: ignore[attr-defined]

        built = build_lp(req)
        res = extract_solution(req, built)

        assert res.status == "optimal"
        assert res.sink_delivered["snk"] == pytest.approx(7.0)

        names = [tc.name for tc in res.tight_constraints]
        assert "source_supply:src" in names

    # ----------------------------
    # _compute_tight_constraints: exclusion + sorting
    # ----------------------------

    def test_compute_tight_constraints_excludes_non_tight_and_sorts(self):
        req = GraphScenarioFactory.bottleneck_edge()
        built = build_lp(req)
        res = extract_solution(req, built)
        assert res.status == "optimal"

        # Start from true solution then make edge cap non-tight by reducing flow by 1
        edge_flows = dict(res.edge_flows)
        process_runs = dict(res.process_runs)

        edge_flows["e_in"] = max(0.0, edge_flows["e_in"] - 1.0)

        tight = _compute_tight_constraints(
            req, built, edge_flows, process_runs, eps=1e-6
        )
        names = [t.name for t in tight]

        assert "edge_cap:e_in" not in names  # now slack = 1.0, should not be included

        # Sorted by slack
        slacks = [t.slack for t in tight]
        assert slacks == sorted(slacks)
