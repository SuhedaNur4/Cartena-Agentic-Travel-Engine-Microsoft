import json
import os
import glob
from datetime import datetime
from backend.application.ports.trace_repo_port import ITraceRepository
from backend.domain.models.trace import WorkflowTrace, TraceEvent

class JSONFileTraceRepository(ITraceRepository):
    def __init__(self, directory: str):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)
        
    async def save(self, trace: WorkflowTrace) -> None:
        file_path = os.path.join(self.directory, f"{trace.workflow_id}.json")
        data = {
            "workflow_id": trace.workflow_id,
            "start_time": trace.start_time.isoformat() if trace.start_time else None,
            "end_time": trace.end_time.isoformat() if trace.end_time else None,
            "final_status": trace.final_status,
            "total_duration_ms": trace.total_duration_ms,
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "node": e.node,
                    "duration_ms": e.duration_ms,
                    "planning_mode": e.planning_mode,
                    "repair_count": e.repair_count,
                    "workflow_status": e.workflow_status,
                    "validation_result": e.validation_result,
                    "model_name": e.model_name,
                    "error_type": e.error_type,
                    "metadata": e.metadata
                }
                for e in trace.events
            ]
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    async def get_all(self) -> list[WorkflowTrace]:
        traces = []
        for file_path in glob.glob(os.path.join(self.directory, "*.json")):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            events = [
                TraceEvent(
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                    node=e["node"],
                    duration_ms=e["duration_ms"],
                    planning_mode=e["planning_mode"],
                    repair_count=e["repair_count"],
                    workflow_status=e["workflow_status"],
                    validation_result=e["validation_result"],
                    model_name=e["model_name"],
                    error_type=e["error_type"],
                    metadata=e.get("metadata", {})
                )
                for e in data.get("events", [])
            ]
            
            trace = WorkflowTrace(
                workflow_id=data["workflow_id"],
                start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
                end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
                final_status=data.get("final_status", "RUNNING"),
                total_duration_ms=data.get("total_duration_ms", 0.0),
                events=events
            )
            traces.append(trace)
        return traces
