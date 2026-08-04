"""
Phase 5: Agentic Observability & Evaluation Engine
Evaluates the State Graph agent by running multiple diverse cases and aggregating performance metrics.
"""

import asyncio
import os
import json
import logging
from typing import Any
from pydantic import BaseModel
from datetime import datetime, timezone

from backend.core.config import Settings
from backend.core.container import build
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Evaluation Dataset
TEST_CASES = [
    TripRequest(
        destination="Kyoto",
        duration_days=2,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE, Interest.FOOD),
        notes="First time in Japan. Temples and traditional food."
    ),
    TripRequest(
        destination="New York",
        duration_days=3,
        budget=BudgetLevel.HIGH,
        interests=(Interest.ADVENTURE, Interest.SHOPPING),
        notes="Want to walk a lot and see the highlights."
    ),
    TripRequest(
        destination="Paris",
        duration_days=1,
        budget=BudgetLevel.LOW,
        interests=(Interest.NATURE, Interest.CULTURE),
        notes="Very tight budget, only free or cheap things. Closed on Monday.",
    ),
    TripRequest(
        destination="Rome",
        duration_days=2,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        notes="Very low walking tolerance. Must have group nearby required."
    ),
    TripRequest(
        destination="Tokyo",
        duration_days=3,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.FOOD, Interest.ADVENTURE),
        notes="I love ramen and anime."
    )
]

class EvaluationMetrics(BaseModel):
    total_cases: int = 0
    first_pass_success: int = 0
    hitl_triggered: int = 0
    repair_success: int = 0
    failures: int = 0
    
    avg_total_latency_ms: float = 0.0
    avg_generation_latency_ms: float = 0.0
    avg_validation_latency_ms: float = 0.0
    avg_repair_count: float = 0.0
    
    def print_report(self):
        print("\n" + "="*50)
        print("AGENT EVALUATION REPORT")
        print("="*50)
        print(f"Total Cases Run         : {self.total_cases}")
        print(f"First-Pass Success Rate : {self.first_pass_success / self.total_cases:.1%}")
        print(f"HITL Trigger Rate       : {self.hitl_triggered / self.total_cases:.1%}")
        print(f"Repair Success Rate     : {self.repair_success / self.total_cases:.1%}")
        print(f"Total Failure Rate      : {self.failures / self.total_cases:.1%}")
        print("-" * 50)
        print(f"Avg Total Latency       : {self.avg_total_latency_ms / 1000:.2f} s")
        print(f"Avg Generation Latency  : {self.avg_generation_latency_ms / 1000:.2f} s")
        print(f"Avg Validation Latency  : {self.avg_validation_latency_ms / 1000:.2f} s")
        print(f"Avg Repair Count        : {self.avg_repair_count:.2f}")
        print("="*50 + "\n")


async def evaluate_agent():
    settings = Settings()
    # Ensure test uses a specific trace dir if needed, but we'll use the default setup in container
    container = build(settings)
    use_case = container.generate_itinerary
    
    metrics = EvaluationMetrics(total_cases=len(TEST_CASES))
    
    total_latency_sum = 0
    gen_latency_sum = 0
    val_latency_sum = 0
    repair_count_sum = 0
    
    gen_counts = 0
    val_counts = 0

    print("Starting evaluation...")
    
    for i, request in enumerate(TEST_CASES, 1):
        print(f"\n[Case {i}/{len(TEST_CASES)}] Processing request for {request.destination}...")
        
        # Run workflow
        workflow_id = f"eval-wf-{i}-{int(datetime.now(timezone.utc).timestamp())}"
        
        try:
            async for event in use_case.execute(request, workflow_id=workflow_id):
                if event.get("type") == "error":
                    print(f"   => Error: {event.get('message')}")
        except Exception as e:
            print(f"   => Exception: {e}")
            
        # The trace repo should have saved the trace in background task
        # Let's wait briefly to ensure async file write completes
        await asyncio.sleep(0.5)
        
        # Load the trace directly from the file to analyze it
        trace_file = os.path.join(container.trace_repo.directory, f"{workflow_id}.json")
        if not os.path.exists(trace_file):
            print(f"   => [WARNING] Trace file {trace_file} not found!")
            metrics.failures += 1
            continue
            
        with open(trace_file, "r", encoding="utf-8") as f:
            trace_data = json.load(f)
            
        status = trace_data.get("final_status", "")
        events = trace_data.get("events", [])
        
        repairs = max([e.get("repair_count", 0) for e in events]) if events else 0
        repair_count_sum += repairs
        total_latency_sum += trace_data.get("total_duration_ms", 0.0)
        
        case_gen_latency = sum(e["duration_ms"] for e in events if e["node"] == "generate")
        case_val_latency = sum(e["duration_ms"] for e in events if e["node"] == "validate")
        
        gen_latency_sum += case_gen_latency
        val_latency_sum += case_val_latency
        
        gen_counts += sum(1 for e in events if e["node"] == "generate")
        val_counts += sum(1 for e in events if e["node"] == "validate")
        
        if status == "SUCCESS":
            if repairs == 0:
                metrics.first_pass_success += 1
                print("   => Result: FIRST-PASS SUCCESS")
            else:
                metrics.repair_success += 1
                print(f"   => Result: REPAIR SUCCESS ({repairs} repairs)")
        elif status == "WAITING_FOR_HUMAN":
            metrics.hitl_triggered += 1
            print("   => Result: HITL TRIGGERED")
        else:
            metrics.failures += 1
            print(f"   => Result: FAILED (Status: {status})")

    # Aggregate
    if metrics.total_cases > 0:
        metrics.avg_total_latency_ms = total_latency_sum / metrics.total_cases
        metrics.avg_repair_count = repair_count_sum / metrics.total_cases
        
    if gen_counts > 0:
        metrics.avg_generation_latency_ms = gen_latency_sum / gen_counts
        
    if val_counts > 0:
        metrics.avg_validation_latency_ms = val_latency_sum / val_counts
        
    metrics.print_report()
    
    # Save report
    os.makedirs("reports", exist_ok=True)
    report_file = f"reports/eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        f.write(metrics.model_dump_json(indent=2))
        
    print(f"Report saved to {report_file}")

if __name__ == "__main__":
    asyncio.run(evaluate_agent())
