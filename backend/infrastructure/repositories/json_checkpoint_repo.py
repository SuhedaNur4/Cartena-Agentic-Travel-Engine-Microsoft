"""
Infrastructure: JSON File based Checkpoint Repository
"""

import json
import os
import copy
from typing import Any
from dataclasses import asdict
from datetime import date

from backend.application.ports.checkpoint_repo_port import ICheckpointRepository
from backend.application.use_cases.state_graph.state import CartenaState
from backend.domain.models.itinerary import Itinerary, Day, ActivityBlock, MealSuggestion
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
from backend.domain.models.resolution import ResolutionOption, ResolutionAction
from backend.domain.services.validator import ViolationReport


class StateEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        import enum
        if isinstance(obj, enum.Enum):
            return obj.value
        if isinstance(obj, date):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            # If it's a dataclass
            import dataclasses
            if dataclasses.is_dataclass(obj):
                return dataclasses.asdict(obj)
            return obj.__dict__
        return super().default(obj)


class JSONFileCheckpointRepository(ICheckpointRepository):
    def __init__(self, directory: str = ".checkpoints"):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def _get_path(self, workflow_id: str) -> str:
        return os.path.join(self.directory, f"{workflow_id}.json")

    async def save(self, workflow_id: str, state: CartenaState) -> None:
        """Saves pure data into JSON. Runtime objects are excluded."""
        data = json.dumps(state, cls=StateEncoder, indent=2)
        with open(self._get_path(workflow_id), "w", encoding="utf-8") as f:
            f.write(data)

    async def get(self, workflow_id: str) -> CartenaState | None:
        path = self._get_path(workflow_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return self._dict_to_state(data)

    def _dict_to_state(self, data: dict) -> CartenaState:
        # Reconstruct TripRequest
        tr_data = data["request"]
        tr = TripRequest(
            destination=tr_data["destination"],
            duration_days=tr_data["duration_days"],
            budget=BudgetLevel(tr_data["budget"]),
            interests=tuple(Interest(i) for i in tr_data["interests"]),
            notes=tr_data["notes"],
            start_date=date.fromisoformat(tr_data["start_date"]) if tr_data.get("start_date") else None
        )
        
        state = CartenaState(request=tr)
        
        # Primitive fields
        for key in ["visited_nodes", "workflow_id", "workflow_status", "resume_from_node", 
                    "user_decision", "planning_mode", "target_days", "user_replan_reason",
                    "online_context", "rag_chunks", "kb_miss", "system_prompt", "user_prompt",
                    "raw_response", "repair_count", "max_repairs", "itinerary_id", "error_message"]:
            if key in data:
                setattr(state, key, data[key])
                
        # Resolutions
        if "resolutions" in data and data["resolutions"]:
            resolutions = []
            for res in data["resolutions"]:
                action = ResolutionAction(**res["action"])
                resolutions.append(ResolutionOption(id=res["id"], label=res["label"], action=action))
            state.resolutions = resolutions

        # Itineraries
        def dict_to_itinerary(it_data: dict | None) -> Itinerary | None:
            if not it_data:
                return None
            days = []
            for d in it_data.get("days", []):
                days.append(Day(
                    day_number=d["day_number"],
                    title=d["title"],
                    morning=ActivityBlock(**d["morning"]),
                    afternoon=ActivityBlock(**d["afternoon"]),
                    evening=ActivityBlock(**d["evening"]),
                    meals=d["meals"] if isinstance(d["meals"], dict) else {},
                    budget_estimate=d["budget_estimate"],
                    tips=d.get("tips", [])
                ))
            it = Itinerary(trip_request=tr, days=days, model_used=it_data.get("model_used", ""))
            it.id = it_data.get("id")
            it.raw_response = it_data.get("raw_response", "")
            it.kb_miss = it_data.get("kb_miss", False)
            it.is_favorite = it_data.get("is_favorite", False)
            it.constraint_score = it_data.get("constraint_score", 1.0)
            it.quality_score = it_data.get("quality_score", 1.0)
            return it

        state.original_itinerary = dict_to_itinerary(data.get("original_itinerary"))
        state.parsed_itinerary = dict_to_itinerary(data.get("parsed_itinerary"))
        state.merged_itinerary = dict_to_itinerary(data.get("merged_itinerary"))
        
        # ValidationReport
        if data.get("validation_report"):
            vr = data["validation_report"]
            report = ViolationReport(
                is_valid=vr["is_valid"],
                hard_violations=vr.get("hard_violations", []),
                soft_warnings=vr.get("soft_warnings", []),
                constraint_score=vr.get("constraint_score", 1.0),
                quality_score=vr.get("quality_score", 1.0)
            )
            if vr.get("resolutions"):
                res_list = []
                for res in vr["resolutions"]:
                    action = ResolutionAction(**res["action"])
                    res_list.append(ResolutionOption(id=res["id"], label=res["label"], action=action))
                report.resolutions = res_list
            state.validation_report = report

        return state
