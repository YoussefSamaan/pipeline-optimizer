from typing import Dict, List, Any
from app.domain.schema import (
    SolveRequest,
    NodeSpec,
    EdgeSpec,
    SolveOptions,
    SolveObjective,
    SourceData,
    SinkData,
    ProcessData,
    ProcessIO,
)

JsonPayload = Dict[str, Any]


class GraphScenarioFactory:
    """Model-first factory.

    - Scenario methods return SolveRequest objects (strong typing).
    - Use to_json(req) when you need the HTTP payload.

    Note: Some schema-invalid cases cannot be constructed as models
    (Pydantic will raise immediately). For those, this class provides
    `json_*` helpers that return dict payloads.
    """

    @staticmethod
    def to_json(req: SolveRequest) -> JsonPayload:
        return req.model_dump(mode="json", exclude_none=True)

    # ----------------------------
    # Valid scenarios (models)
    # ----------------------------

    @staticmethod
    def simple_source_sink() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="src",
                    type="source",
                    source=SourceData(commodity="water", supply_cap=100, unit_cost=1),
                ),
                NodeSpec(
                    id="snk",
                    type="sink",
                    sink=SinkData(commodity="water", demand_cap=50, unit_value=10),
                ),
            ],
            edges=[EdgeSpec(id="e1", u="src", v="snk", commodity="water")],
            options=SolveOptions(
                mode="lp", objective=SolveObjective(kind="max_profit")
            ),
        )

    @staticmethod
    def process_chain() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="farm",
                    type="source",
                    source=SourceData(commodity="wheat", supply_cap=100, unit_cost=1),
                ),
                NodeSpec(
                    id="mill",
                    type="process",
                    process=ProcessData(
                        inputs=[ProcessIO(commodity="wheat", qty=2)],
                        outputs=[ProcessIO(commodity="flour", qty=1)],
                        run_cap=None,
                        run_cost=5,
                    ),
                ),
                NodeSpec(
                    id="bakery",
                    type="sink",
                    sink=SinkData(commodity="flour", demand_cap=100, unit_value=20),
                ),
            ],
            edges=[
                EdgeSpec(id="e1", u="farm", v="mill", commodity="wheat"),
                EdgeSpec(id="e2", u="mill", v="bakery", commodity="flour"),
            ],
            options=SolveOptions(
                mode="lp", objective=SolveObjective(kind="max_profit")
            ),
        )

    @staticmethod
    def cooking() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="water",
                    type="source",
                    source=SourceData(commodity="water", supply_cap=10, unit_cost=0),
                ),
                NodeSpec(
                    id="rice",
                    type="source",
                    source=SourceData(commodity="rice", supply_cap=10, unit_cost=0),
                ),
                NodeSpec(
                    id="cook",
                    type="process",
                    process=ProcessData(
                        inputs=[
                            ProcessIO(commodity="water", qty=1),
                            ProcessIO(commodity="rice", qty=2),
                        ],
                        outputs=[ProcessIO(commodity="cooked_rice", qty=1)],
                        run_cost=0,
                    ),
                ),
                NodeSpec(
                    id="plate",
                    type="sink",
                    sink=SinkData(
                        commodity="cooked_rice", demand_cap=100, unit_value=1
                    ),
                ),
            ],
            edges=[
                EdgeSpec(id="e1", u="water", v="cook", commodity="water"),
                EdgeSpec(id="e2", u="rice", v="cook", commodity="rice"),
                EdgeSpec(id="e3", u="cook", v="plate", commodity="cooked_rice"),
            ],
            options=SolveOptions(
                mode="lp", objective=SolveObjective(kind="max_profit")
            ),
        )

    @staticmethod
    def bottleneck_edge() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="iron",
                    type="source",
                    source=SourceData(commodity="iron", supply_cap=100, unit_cost=0),
                ),
                NodeSpec(
                    id="smelt",
                    type="process",
                    process=ProcessData(
                        inputs=[ProcessIO(commodity="iron", qty=1)],
                        outputs=[ProcessIO(commodity="plate", qty=1)],
                    ),
                ),
                NodeSpec(
                    id="sink",
                    type="sink",
                    sink=SinkData(commodity="plate", demand_cap=100, unit_value=1),
                ),
            ],
            edges=[
                EdgeSpec(id="e_in", u="iron", v="smelt", commodity="iron", cap=7),
                EdgeSpec(id="e_out", u="smelt", v="sink", commodity="plate"),
            ],
            options=SolveOptions(
                mode="lp", objective=SolveObjective(kind="max_profit")
            ),
        )

    @staticmethod
    def water_bottle_scenario() -> SolveRequest:
        """
        Bottle Manufacturing Scenario:
        Plastic -> Make Bottle (-> Bottle)
        Bottle + Water -> Fill Bottle -> Water Bottle
        """
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="src_plastic",
                    type="source",
                    source=SourceData(commodity="plastic", supply_cap=100, unit_cost=1),
                ),
                NodeSpec(
                    id="src_water",
                    type="source",
                    source=SourceData(commodity="water", supply_cap=100, unit_cost=1),
                ),
                # Make Bottle: 1 Plastic -> 1 Bottle
                NodeSpec(
                    id="proc_make_bottle",
                    type="process",
                    process=ProcessData(
                        inputs=[ProcessIO(commodity="plastic", qty=1)],
                        outputs=[ProcessIO(commodity="bottle", qty=1)],
                        run_cost=1,
                    ),
                ),
                # Fill Bottle: 1 Bottle + 1 Water -> 1 Water Bottle
                NodeSpec(
                    id="proc_fill_bottle",
                    type="process",
                    process=ProcessData(
                        inputs=[
                            ProcessIO(commodity="bottle", qty=1),
                            ProcessIO(commodity="water", qty=1),
                        ],
                        outputs=[ProcessIO(commodity="water_bottle", qty=1)],
                        run_cost=1,
                    ),
                ),
                NodeSpec(
                    id="snk",
                    type="sink",
                    sink=SinkData(
                        commodity="water_bottle", demand_cap=50, unit_value=10
                    ),
                ),
            ],
            edges=[
                EdgeSpec(
                    id="e1", u="src_plastic", v="proc_make_bottle", commodity="plastic"
                ),
                EdgeSpec(
                    id="e2",
                    u="proc_make_bottle",
                    v="proc_fill_bottle",
                    commodity="bottle",
                ),
                EdgeSpec(
                    id="e3", u="src_water", v="proc_fill_bottle", commodity="water"
                ),
                EdgeSpec(
                    id="e4", u="proc_fill_bottle", v="snk", commodity="water_bottle"
                ),
            ],
            options=SolveOptions(
                mode="lp", objective=SolveObjective(kind="max_profit")
            ),
        )

    @staticmethod
    def multiple_sinks_same_commodity() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="src",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=10, unit_cost=0),
                ),
                NodeSpec(
                    id="hi",
                    type="sink",
                    sink=SinkData(commodity="a", demand_cap=10, unit_value=10),
                ),
                NodeSpec(
                    id="lo",
                    type="sink",
                    sink=SinkData(commodity="a", demand_cap=10, unit_value=1),
                ),
            ],
            edges=[
                EdgeSpec(id="e1", u="src", v="hi", commodity="a"),
                EdgeSpec(id="e2", u="src", v="lo", commodity="a"),
            ],
            options=SolveOptions(
                mode="lp", objective=SolveObjective(kind="max_profit")
            ),
        )

    @staticmethod
    def max_flow_objective() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="src",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=100, unit_cost=0),
                ),
                NodeSpec(
                    id="snk",
                    type="sink",
                    sink=SinkData(commodity="a", demand_cap=100, unit_value=0),
                ),
            ],
            edges=[EdgeSpec(id="e1", u="src", v="snk", commodity="a")],
            options=SolveOptions(
                mode="lp",
                objective=SolveObjective(kind="max_flow_to_sink", sink_node_id="snk"),
            ),
        )

    # ----------------------------
    # Domain-invalid scenarios (models that pass Pydantic)
    # ----------------------------

    @staticmethod
    def duplicate_node_ids() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="n1",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=10, unit_cost=0),
                ),
                NodeSpec(
                    id="n1",
                    type="sink",
                    sink=SinkData(commodity="a", demand_cap=10, unit_value=0),
                ),
            ],
            edges=[],
            options=SolveOptions(),
        )

    @staticmethod
    def duplicate_edge_ids() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="n1",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=10, unit_cost=0),
                ),
                NodeSpec(
                    id="n2",
                    type="sink",
                    sink=SinkData(commodity="a", demand_cap=10, unit_value=0),
                ),
            ],
            edges=[
                EdgeSpec(id="e1", u="n1", v="n2", commodity="a"),
                EdgeSpec(id="e1", u="n1", v="n2", commodity="a"),
            ],
            options=SolveOptions(),
        )

    @staticmethod
    def missing_u_node() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="n1",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=10, unit_cost=0),
                )
            ],
            edges=[EdgeSpec(id="e1", u="missing_node", v="n1", commodity="a")],
            options=SolveOptions(),
        )

    @staticmethod
    def missing_v_node() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="n1",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=10, unit_cost=0),
                )
            ],
            edges=[EdgeSpec(id="e1", u="n1", v="missing_node", commodity="a")],
            options=SolveOptions(),
        )

    @staticmethod
    def self_loop_edge() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="n1",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=10, unit_cost=0),
                )
            ],
            edges=[EdgeSpec(id="e1", u="n1", v="n1", commodity="a")],
            options=SolveOptions(),
        )

    @staticmethod
    def process_no_inputs_domain() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="p1",
                    type="process",
                    process=ProcessData(
                        inputs=[], outputs=[ProcessIO(commodity="b", qty=1)], run_cost=0
                    ),
                )
            ],
            edges=[],
            options=SolveOptions(),
        )

    @staticmethod
    def process_no_outputs_domain() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="p1",
                    type="process",
                    process=ProcessData(
                        inputs=[ProcessIO(commodity="a", qty=1)], outputs=[], run_cost=0
                    ),
                )
            ],
            edges=[],
            options=SolveOptions(),
        )

    @staticmethod
    def sink_unproduced_commodity() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="src",
                    type="source",
                    source=SourceData(commodity="water", supply_cap=10, unit_cost=0),
                ),
                NodeSpec(
                    id="snk",
                    type="sink",
                    sink=SinkData(commodity="gold", demand_cap=1, unit_value=1),
                ),
            ],
            edges=[],
            options=SolveOptions(),
        )

    @staticmethod
    def sink_disconnected() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="src",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=10, unit_cost=0),
                ),
                NodeSpec(
                    id="snk",
                    type="sink",
                    sink=SinkData(commodity="a", demand_cap=10, unit_value=1),
                ),
            ],
            edges=[],
            options=SolveOptions(),
        )

    @staticmethod
    def objective_max_flow_missing_sink_id() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="src",
                    type="source",
                    source=SourceData(commodity="a", supply_cap=10, unit_cost=0),
                ),
                NodeSpec(
                    id="snk",
                    type="sink",
                    sink=SinkData(commodity="a", demand_cap=10, unit_value=0),
                ),
            ],
            edges=[EdgeSpec(id="e1", u="src", v="snk", commodity="a")],
            options=SolveOptions(
                mode="lp",
                objective=SolveObjective(kind="max_flow_to_sink", sink_node_id=None),
            ),
        )

    # ----------------------------
    # Schema-invalid scenarios (raw dicts; cannot instantiate models)
    # ----------------------------

    @staticmethod
    def json_negative_supply_cap() -> JsonPayload:
        return {
            "nodes": [
                {
                    "id": "src",
                    "type": "source",
                    "source": {"commodity": "a", "supply_cap": -1, "unit_cost": 0},
                }
            ],
            "edges": [],
            "options": {"mode": "lp"},
        }

    @staticmethod
    def json_negative_edge_cap() -> JsonPayload:
        return {
            "nodes": [
                {
                    "id": "src",
                    "type": "source",
                    "source": {"commodity": "a", "supply_cap": 10, "unit_cost": 0},
                },
                {
                    "id": "snk",
                    "type": "sink",
                    "sink": {"commodity": "a", "demand_cap": 10, "unit_value": 1},
                },
            ],
            "edges": [
                {"id": "e1", "u": "src", "v": "snk", "commodity": "a", "cap": -1}
            ],
            "options": {"mode": "lp"},
        }

    @staticmethod
    def json_process_io_qty_zero() -> JsonPayload:
        return {
            "nodes": [
                {
                    "id": "p1",
                    "type": "process",
                    "process": {
                        "inputs": [{"commodity": "a", "qty": 0}],
                        "outputs": [{"commodity": "b", "qty": 1}],
                    },
                }
            ],
            "edges": [],
            "options": {"mode": "lp"},
        }

    @staticmethod
    def json_source_missing_source_field() -> JsonPayload:
        return {
            "nodes": [{"id": "src", "type": "source"}],
            "edges": [],
            "options": {"mode": "lp"},
        }

    @staticmethod
    def json_sink_missing_sink_field() -> JsonPayload:
        return {
            "nodes": [{"id": "snk", "type": "sink"}],
            "edges": [],
            "options": {"mode": "lp"},
        }

    @staticmethod
    def json_process_missing_process_field() -> JsonPayload:
        return {
            "nodes": [{"id": "p1", "type": "process"}],
            "edges": [],
            "options": {"mode": "lp"},
        }

    @staticmethod
    def process_chain_with_run_cap() -> SolveRequest:
        return SolveRequest(
            nodes=[
                NodeSpec(
                    id="src",
                    type="source",
                    source=SourceData(commodity="A", supply_cap=100, unit_cost=0),
                ),
                NodeSpec(
                    id="p",
                    type="process",
                    process=ProcessData(
                        inputs=[ProcessIO(commodity="A", qty=1)],
                        outputs=[ProcessIO(commodity="B", qty=1)],
                        run_cap=3,
                        run_cost=0,
                    ),
                ),
                NodeSpec(
                    id="snk",
                    type="sink",
                    sink=SinkData(commodity="B", demand_cap=100, unit_value=1),
                ),
            ],
            edges=[
                EdgeSpec(id="e_in", u="src", v="p", commodity="A"),
                EdgeSpec(id="e_out", u="p", v="snk", commodity="B"),
            ],
            options=SolveOptions(
                mode="lp", objective=SolveObjective(kind="max_profit")
            ),
        )

    # ----------------------------
    # Curated lists for pytest parametrization
    # ----------------------------

    @staticmethod
    def valid() -> List[SolveRequest]:
        return [
            GraphScenarioFactory.simple_source_sink(),
            GraphScenarioFactory.process_chain(),
            GraphScenarioFactory.cooking(),
            GraphScenarioFactory.bottleneck_edge(),
            GraphScenarioFactory.water_bottle_scenario(),
            GraphScenarioFactory.multiple_sinks_same_commodity(),
            GraphScenarioFactory.max_flow_objective(),
            GraphScenarioFactory.process_chain_with_run_cap(),
        ]

    @staticmethod
    def domain_invalid() -> List[SolveRequest]:
        return [
            GraphScenarioFactory.duplicate_node_ids(),
            GraphScenarioFactory.duplicate_edge_ids(),
            GraphScenarioFactory.missing_u_node(),
            GraphScenarioFactory.missing_v_node(),
            GraphScenarioFactory.self_loop_edge(),
            GraphScenarioFactory.process_no_inputs_domain(),
            GraphScenarioFactory.process_no_outputs_domain(),
            GraphScenarioFactory.sink_unproduced_commodity(),
            GraphScenarioFactory.sink_disconnected(),
            GraphScenarioFactory.objective_max_flow_missing_sink_id(),
        ]

    @staticmethod
    def schema_invalid() -> List[JsonPayload]:
        return [
            GraphScenarioFactory.json_negative_supply_cap(),
            GraphScenarioFactory.json_negative_edge_cap(),
            GraphScenarioFactory.json_process_io_qty_zero(),
            GraphScenarioFactory.json_source_missing_source_field(),
            GraphScenarioFactory.json_sink_missing_sink_field(),
            GraphScenarioFactory.json_process_missing_process_field(),
        ]
