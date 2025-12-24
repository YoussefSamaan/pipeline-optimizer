from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict

NodeType = Literal["source", "process", "sink"]
ModeType = Literal["lp"]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceData(StrictBaseModel):
    commodity: str = Field(min_length=1)
    supply_cap: float = Field(ge=0)
    unit_cost: float = 0.0


class SinkData(StrictBaseModel):
    commodity: str = Field(min_length=1)
    demand_cap: float = Field(ge=0)
    unit_value: float = 0.0


class ProcessIO(StrictBaseModel):
    commodity: str = Field(min_length=1)
    qty: float = Field(gt=0)  # per 1 unit run


class ProcessData(StrictBaseModel):
    inputs: List[ProcessIO] = Field(default_factory=list)
    outputs: List[ProcessIO] = Field(default_factory=list)
    run_cap: Optional[float] = Field(default=None, ge=0)
    run_cost: float = 0.0


class NodeSpec(StrictBaseModel):
    id: str = Field(min_length=1)
    type: NodeType
    name: Optional[str] = None

    source: Optional[SourceData] = None
    sink: Optional[SinkData] = None
    process: Optional[ProcessData] = None

    @model_validator(mode="after")
    def _check_payload_matches_type(self) -> "NodeSpec":
        required = {
            "source": self.source is not None,
            "sink": self.sink is not None,
            "process": self.process is not None,
        }

        if self.type == "source":
            if not required["source"]:
                raise ValueError("Node type 'source' requires 'source' field.")
            if required["sink"] or required["process"]:
                raise ValueError("Node type 'source' forbids 'sink'/'process' fields.")

        elif self.type == "sink":
            if not required["sink"]:
                raise ValueError("Node type 'sink' requires 'sink' field.")
            if required["source"] or required["process"]:
                raise ValueError("Node type 'sink' forbids 'source'/'process' fields.")

        elif self.type == "process":
            if not required["process"]:
                raise ValueError("Node type 'process' requires 'process' field.")
            if required["source"] or required["sink"]:
                raise ValueError("Node type 'process' forbids 'source'/'sink' fields.")

        return self


class EdgeSpec(StrictBaseModel):
    id: str = Field(min_length=1)
    u: str = Field(min_length=1)
    v: str = Field(min_length=1)

    commodity: str = Field(min_length=1)
    cap: Optional[float] = Field(default=None, ge=0)
    unit_cost: float = 0.0


class SolveObjective(StrictBaseModel):
    kind: Literal["max_profit", "max_flow_to_sink"] = "max_profit"
    sink_node_id: Optional[str] = None


class SolveOptions(StrictBaseModel):
    mode: ModeType = "lp"
    objective: SolveObjective = Field(default_factory=SolveObjective)


class SolveRequest(StrictBaseModel):
    nodes: List[NodeSpec]
    edges: List[EdgeSpec]
    options: SolveOptions = Field(default_factory=SolveOptions)


class TightConstraint(StrictBaseModel):
    name: str
    slack: float


class SolveResult(StrictBaseModel):
    status: Literal["optimal", "infeasible", "unbounded", "error"]
    objective_value: Optional[float] = None

    edge_flows: Dict[str, float] = Field(default_factory=dict)
    process_runs: Dict[str, float] = Field(default_factory=dict)
    sink_delivered: Dict[str, float] = Field(default_factory=dict)

    tight_constraints: List[TightConstraint] = Field(default_factory=list)
    message: Optional[str] = None
