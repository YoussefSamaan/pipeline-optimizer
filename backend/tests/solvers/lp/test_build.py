import math
import copy
import pytest
from ortools.linear_solver import pywraplp

from app.core.errors import DomainError
from app.domain.schema import EdgeSpec
from app.solvers.lp.build import build_lp
from tests.graph_scenario_factory import GraphScenarioFactory


def assert_optimal(built):
    status = built.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL
    return status


class TestBuild:
    def test_build_simple_source_sink_vars_exist(self):
        req = GraphScenarioFactory.simple_source_sink()
        built = build_lp(req)
        assert_optimal(built)

        assert "e1" in built.f_edge
        assert built.f_edge["e1"].Lb() == 0.0

    def test_solve_simple_source_sink_hits_demand(self):
        req = GraphScenarioFactory.simple_source_sink()
        built = build_lp(req)
        assert_optimal(built)

        assert math.isclose(
            built.f_edge["e1"].solution_value(), 50.0, rel_tol=0, abs_tol=1e-6
        )

    def test_edge_capacity_binds(self):
        req = GraphScenarioFactory.bottleneck_edge()
        built = build_lp(req)
        assert_optimal(built)

        assert math.isclose(
            built.f_edge["e_in"].solution_value(), 7.0, rel_tol=0, abs_tol=1e-6
        )

    def test_objective_max_flow(self):
        req = GraphScenarioFactory.max_flow_objective()
        built = build_lp(req)
        assert_optimal(built)

        assert math.isclose(
            built.f_edge["e1"].solution_value(), 100.0, rel_tol=0, abs_tol=1e-6
        )

    def test_max_flow_missing_sink_id_raises(self):
        # This is a *defensive* build_lp check (normally caught by validate_request)
        req = copy.deepcopy(GraphScenarioFactory.max_flow_objective())
        req.options.objective.sink_node_id = None

        with pytest.raises(DomainError, match="requires objective.sink_node_id"):
            build_lp(req)

    def test_create_solver_none_raises(self, monkeypatch):
        import app.solvers.lp.build as build_mod

        def _fake_create_solver(*args, **kwargs):
            return None

        monkeypatch.setattr(
            build_mod.pywraplp.Solver,
            "CreateSolver",
            staticmethod(_fake_create_solver),
        )

        req = GraphScenarioFactory.simple_source_sink()
        with pytest.raises(RuntimeError, match="Failed to create OR-Tools GLOP solver"):
            build_mod.build_lp(req)

    def test_topology_sanity_forces_source_inflow_and_sink_outflow_to_zero(self):
        # coverage for "no_in_to_source" and "no_out_from_sink"
        req = copy.deepcopy(GraphScenarioFactory.simple_source_sink())
        req.edges.append(EdgeSpec(id="e_bad", u="snk", v="src", commodity="water"))

        built = build_lp(req)
        assert_optimal(built)

        assert math.isclose(
            built.f_edge["e_bad"].solution_value(), 0.0, rel_tol=0, abs_tol=1e-6
        )
        assert built.f_edge["e1"].solution_value() > 0

    def test_process_run_cap_binds(self):
        req = GraphScenarioFactory.process_chain_with_run_cap()
        built = build_lp(req)
        assert_optimal(built)

        assert math.isclose(
            built.r_proc["p"].solution_value(), 3.0, rel_tol=0, abs_tol=1e-6
        )
        assert math.isclose(
            built.f_edge["e_out"].solution_value(), 3.0, rel_tol=0, abs_tol=1e-6
        )
