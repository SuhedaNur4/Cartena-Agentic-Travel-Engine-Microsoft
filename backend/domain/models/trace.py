from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TraceEvent:
    timestamp: datetime
    node: str
    duration_ms: float
    planning_mode: str
    repair_count: int
    workflow_status: str
    validation_result: bool | None = None
    model_name: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowTrace:
    workflow_id: str
    start_time: datetime
    end_time: datetime | None = None
    events: list[TraceEvent] = field(default_factory=list)
    final_status: str = "RUNNING"
    total_duration_ms: float = 0.0
    
    @property
    def total_repairs(self) -> int:
        if not self.events:
            return 0
        return max(e.repair_count for e in self.events)

    @property
    def hitl_triggered(self) -> bool:
        return any(e.workflow_status == "WAITING_FOR_HUMAN" for e in self.events)
        
    @property
    def first_pass_success(self) -> bool:
        """True if successfully finished with 0 repairs and no HITL."""
        return self.total_repairs == 0 and not self.hitl_triggered and self.final_status == "SUCCESS"
