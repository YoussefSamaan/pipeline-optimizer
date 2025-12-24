import pytest
from pydantic import ValidationError

from app.domain.schema import (
    SourceData,
    SinkData,
    ProcessIO,
    ProcessData,
    NodeSpec,
    EdgeSpec,
    SolveRequest,
)


class TestSchema:
    def test_source_data_valid(self):
        data = SourceData(commodity="Water", supply_cap=100.0, unit_cost=1.5)
        assert data.commodity == "Water"
        assert data.supply_cap == 100.0
        assert data.unit_cost == 1.5

    def test_source_data_invalid(self):
        with pytest.raises(ValidationError):
            SourceData(commodity="", supply_cap=10.0)

        with pytest.raises(ValidationError):
            SourceData(commodity="A", supply_cap=-1.0)

    def test_sink_data_valid(self):
        data = SinkData(commodity="Product", demand_cap=50.0, unit_value=10.0)
        assert data.commodity == "Product"
        assert data.demand_cap == 50.0
        assert data.unit_value == 10.0

    def test_sink_data_invalid(self):
        with pytest.raises(ValidationError):
            SinkData(commodity="", demand_cap=10.0)

        with pytest.raises(ValidationError):
            SinkData(commodity="A", demand_cap=-5.0)

    def test_process_io_valid(self):
        io = ProcessIO(commodity="A", qty=2.0)
        assert io.commodity == "A"
        assert io.qty == 2.0

    def test_process_io_invalid(self):
        with pytest.raises(ValidationError):
            ProcessIO(commodity="", qty=1.0)

        with pytest.raises(ValidationError):
            ProcessIO(commodity="A", qty=0.0)
        with pytest.raises(ValidationError):
            ProcessIO(commodity="A", qty=-1.0)

    def test_process_data_valid(self):
        inputs = [ProcessIO(commodity="Water", qty=1.0)]
        outputs = [ProcessIO(commodity="Steam", qty=0.9)]
        data = ProcessData(inputs=inputs, outputs=outputs, run_cap=10.0)
        assert len(data.inputs) == 1
        assert len(data.outputs) == 1
        assert data.run_cap == 10.0

    def test_process_data_invalid(self):
        with pytest.raises(ValidationError):
            ProcessData(run_cap=-10.0)

    def test_node_spec_valid_source(self):
        source_data = SourceData(commodity="A", supply_cap=100.0)
        node = NodeSpec(id="n1", type="source", source=source_data)
        assert node.id == "n1"
        assert node.type == "source"
        assert node.source == source_data

    def test_node_spec_valid_process(self):
        proc_data = ProcessData(inputs=[], outputs=[])
        node = NodeSpec(id="n2", type="process", process=proc_data)
        assert node.type == "process"
        assert node.process == proc_data

    def test_node_spec_invalid_missing_payload(self):
        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n1", type="source")
        assert "requires 'source'" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n2", type="sink")
        assert "requires 'sink'" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n3", type="process")
        assert "requires 'process'" in str(exc.value)

    def test_node_spec_invalid_id(self):
        with pytest.raises(ValidationError):
            NodeSpec(id="", type="process", process=ProcessData())

    # ---- NEW: cover "forbids other payloads" branches ----

    def test_node_spec_source_forbids_sink_and_process(self):
        src = SourceData(commodity="A", supply_cap=1)
        snk = SinkData(commodity="A", demand_cap=1)
        proc = ProcessData()

        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n1", type="source", source=src, sink=snk)
        assert "forbids" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n2", type="source", source=src, process=proc)
        assert "forbids" in str(exc.value)

    def test_node_spec_sink_forbids_source_and_process(self):
        snk = SinkData(commodity="A", demand_cap=1)
        src = SourceData(commodity="A", supply_cap=1)
        proc = ProcessData()

        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n1", type="sink", sink=snk, source=src)
        assert "forbids" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n2", type="sink", sink=snk, process=proc)
        assert "forbids" in str(exc.value)

    def test_node_spec_process_forbids_source_and_sink(self):
        proc = ProcessData()
        src = SourceData(commodity="A", supply_cap=1)
        snk = SinkData(commodity="A", demand_cap=1)

        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n1", type="process", process=proc, source=src)
        assert "forbids" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            NodeSpec(id="n2", type="process", process=proc, sink=snk)
        assert "forbids" in str(exc.value)

    def test_edge_spec_valid(self):
        edge = EdgeSpec(id="e1", u="n1", v="n2", commodity="Water", cap=100.0, unit_cost=0.5)
        assert edge.id == "e1"
        assert edge.u == "n1"
        assert edge.v == "n2"
        assert edge.commodity == "Water"

    def test_edge_spec_invalid(self):
        with pytest.raises(ValidationError):
            EdgeSpec(id="", u="n1", v="n2", commodity="A")

        with pytest.raises(ValidationError):
            EdgeSpec(id="e1", u="", v="n2", commodity="A")

        with pytest.raises(ValidationError):
            EdgeSpec(id="e1", u="n1", v="n2", commodity="A", cap=-1.0)

    def test_extra_fields_are_forbidden(self):
        with pytest.raises(ValidationError):
            SourceData(commodity="A", supply_cap=1, unit_cost=0.0, surprise=123)

    def test_solve_request_valid(self):
        nodes = [
            NodeSpec(id="s1", type="source", source=SourceData(commodity="A", supply_cap=10)),
            NodeSpec(id="t1", type="sink", sink=SinkData(commodity="A", demand_cap=10)),
        ]
        edges = [EdgeSpec(id="e1", u="s1", v="t1", commodity="A")]
        req = SolveRequest(nodes=nodes, edges=edges)
        assert len(req.nodes) == 2
        assert len(req.edges) == 1

    def test_solve_request_defaults(self):
        nodes = [
            NodeSpec(id="s1", type="source", source=SourceData(commodity="A", supply_cap=1)),
            NodeSpec(id="t1", type="sink", sink=SinkData(commodity="A", demand_cap=1)),
        ]
        edges = [EdgeSpec(id="e1", u="s1", v="t1", commodity="A")]
        req = SolveRequest(nodes=nodes, edges=edges)

        assert req.options.mode == "lp"
        assert req.options.objective.kind == "max_profit"
        assert req.options.objective.sink_node_id is None
