"""
Phase 6: Agent Evaluation Framework
Evaluates the State Graph agent by running multiple diverse cases from a dataset
and comparing actual trace metrics with expected behaviors.
Outputs JSON and Markdown reports.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import logging
from typing import Any, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from backend.core.config import Settings
from backend.core.container import build
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CaseResult(BaseModel):
    case_id: str
    category: str
    expected_status: str
    actual_status: str
    passed: bool
    latency_ms: float
    repair_count: int
    tokens: Dict[str, int] = Field(default_factory=lambda: {"input": 0, "output": 0})

class EvaluationReport(BaseModel):
    dataset_name: str
    timestamp: str
    total_cases: int = 0
    passed_cases: int = 0
    first_pass_success: int = 0
    repair_recovery: int = 0
    repair_triggered: int = 0
    hitl_escalation: int = 0
    failure_handling: int = 0
    
    avg_total_latency_ms: float = 0.0
    avg_generation_latency_ms: float = 0.0
    avg_validation_latency_ms: float = 0.0
    avg_repair_count: float = 0.0
    
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0

    results: List[CaseResult] = []

    def print_console(self):
        print("\n" + "="*50)
        print("AGENT EVALUATION REPORT")
        print("="*50)
        print(f"Dataset                 : {self.dataset_name}")
        print(f"Total Cases Run         : {self.total_cases}")
        print(f"Overall Pass Rate       : {self.passed_cases / max(1, self.total_cases):.1%}")
        print(f"First-Pass Success Rate : {self.first_pass_success / max(1, self.total_cases):.1%}")
        
        rep_rec = self.repair_recovery / max(1, self.repair_triggered) if self.repair_triggered > 0 else 0
        print(f"Repair Recovery Rate    : {rep_rec:.1%} ({self.repair_recovery}/{self.repair_triggered})")
        print(f"HITL Escalation Rate    : {self.hitl_escalation / max(1, self.total_cases):.1%}")
        print(f"Failure Handling Rate   : {self.failure_handling / max(1, self.total_cases):.1%}")
        print("-" * 50)
        print(f"Avg Total Latency       : {self.avg_total_latency_ms / 1000:.2f} s")
        print(f"Avg Input Tokens        : {self.avg_input_tokens:.0f}")
        print(f"Avg Output Tokens       : {self.avg_output_tokens:.0f}")
        print("="*50 + "\n")

    def export_markdown(self, filepath: str):
        rep_rec = self.repair_recovery / max(1, self.repair_triggered) if self.repair_triggered > 0 else 0
        md = f"""# Cartena Evaluation Report

**Dataset:** `{self.dataset_name}`
**Date:** {self.timestamp}
**Total Cases:** {self.total_cases}
**Overall Pass Rate:** {self.passed_cases / max(1, self.total_cases):.1%}

## Reliability Metrics
- **First Pass Success:** {self.first_pass_success / max(1, self.total_cases):.1%}
- **Repair Recovery:** {rep_rec:.1%} ({self.repair_recovery}/{self.repair_triggered})
- **HITL Escalation:** {self.hitl_escalation / max(1, self.total_cases):.1%}
- **Controlled Failures:** {self.failure_handling / max(1, self.total_cases):.1%}

## Efficiency Metrics
- **Average Latency:** {self.avg_total_latency_ms / 1000:.2f} s
- **Average Repair Count:** {self.avg_repair_count:.2f}
- **Average Input Tokens:** {self.avg_input_tokens:.0f}
- **Average Output Tokens:** {self.avg_output_tokens:.0f}

## Detailed Results
| Case ID | Category | Expected | Actual | Passed | Latency (s) | Repairs | Tokens (In/Out) |
|---|---|---|---|---|---|---|---|
"""
        for r in self.results:
            pass_str = "✅" if r.passed else "❌"
            lat = f"{r.latency_ms/1000:.1f}s"
            toks = f"{r.tokens.get('input',0)} / {r.tokens.get('output',0)}"
            md += f"| {r.case_id} | {r.category} | {r.expected_status} | {r.actual_status} | {pass_str} | {lat} | {r.repair_count} | {toks} |\n"
            
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)


async def evaluate_agent(dataset_file: str):
    settings = Settings()
    container = build(settings)
    use_case = container.generate_itinerary
    
    if not os.path.exists(dataset_file):
        print(f"Dataset {dataset_file} not found!")
        return
        
    with open(dataset_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    dataset_name = os.path.basename(dataset_file).replace(".json", "")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = EvaluationReport(dataset_name=dataset_name, timestamp=timestamp, total_cases=len(dataset))
    
    total_lat = 0
    total_gen_lat = 0
    total_val_lat = 0
    total_reps = 0
    total_in_toks = 0
    total_out_toks = 0
    
    print(f"Starting evaluation with {len(dataset)} cases from {dataset_file}...")
    
    for i, case_data in enumerate(dataset, 1):
        case_id = case_data["id"]
        category = case_data["category"]
        expected = case_data["expected"]["status"]
        inp = case_data["input"]
        
        print(f"\n[{i}/{len(dataset)}] Case {case_id} ({category})...")
        
        # Convert strings to Enums carefully
        try:
            budget = BudgetLevel(inp.get("budget", "medium").lower())
        except ValueError:
            budget = BudgetLevel.MEDIUM
            
        interests = []
        for it in inp.get("interests", []):
            try:
                interests.append(Interest(it.lower()))
            except ValueError:
                # If they passed an invalid interest, we'll force a failure if list is empty
                pass
                
        workflow_id = f"eval-{case_id}-{int(datetime.now(timezone.utc).timestamp())}"
        
        request_failed = False
        try:
            request = TripRequest(
                destination=inp.get("destination", ""),
                duration_days=inp.get("duration_days", 1),
                budget=budget,
                interests=tuple(interests),
                notes=inp.get("notes", "")
            )
        except ValueError as ve:
            logger.debug(f"Input validation failure (expected if failure test): {ve}")
            request_failed = True
            actual_status = "ERROR"
            latency = 0
            repairs = 0
            in_toks = 0
            out_toks = 0

        if not request_failed:
            # Execute workflow
            try:
                async for event in use_case.execute(request, workflow_id=workflow_id):
                    pass
            except Exception as e:
                logger.debug(f"Workflow exception (expected if failure test): {e}")
                
            # Give async trace writer a moment
            await asyncio.sleep(0.5)
            
            # Extract metrics strictly from ITraceRepository (JSON file)
            trace_file = os.path.join(container.trace_repo.directory, f"{workflow_id}.json")
            if not os.path.exists(trace_file):
                actual_status = "FATAL"
                latency = 0
                repairs = 0
                in_toks = 0
                out_toks = 0
            else:
                with open(trace_file, "r", encoding="utf-8") as f:
                    trace_data = json.load(f)
                    
                actual_status = trace_data.get("final_status", "UNKNOWN")
                if actual_status == "WAITING_HUMAN" and expected == "WAITING_FOR_HUMAN":
                    actual_status = "WAITING_HUMAN"
                    expected = "WAITING_HUMAN"
                    
                events = trace_data.get("events", [])
                latency = trace_data.get("total_duration_ms", 0.0)
                repairs = max([e.get("metadata", {}).get("repair_attempt", 0) for e in events if e.get("node") == "generator"], default=0)
                
                total_lat += latency
                total_reps += repairs
                
                total_gen_lat += sum(e["duration_ms"] for e in events if e["node"] == "generator")
                total_val_lat += sum(e["duration_ms"] for e in events if e["node"] == "validator")
                
                in_toks = 0
                out_toks = 0
                for e in events:
                    if e.get("node") == "generator" and "llm" in e.get("metadata", {}):
                        in_toks += e["metadata"]["llm"].get("input_tokens", 0)
                        out_toks += e["metadata"]["llm"].get("output_tokens", 0)
                        
                total_in_toks += in_toks
                total_out_toks += out_toks

        passed = False
        
        if category == "success":
            passed = (actual_status == expected and repairs == 0)
            if passed:
                report.first_pass_success += 1
        elif category == "repair":
            report.repair_triggered += 1
            passed = (actual_status == expected)
            if passed:
                report.repair_recovery += 1
        elif category == "hitl":
            passed = (actual_status == expected and repairs == 0)
            if passed:
                report.hitl_escalation += 1
        elif category == "failure":
            passed = (actual_status in ["failed", "ERROR", "UNKNOWN", "FATAL"])
            if passed:
                report.failure_handling += 1
                
        if passed:
            report.passed_cases += 1
            
        pass_str = "[PASS]" if passed else "[FAIL]"
        print(f"   => Status: {actual_status} (Expected: {expected}) | Repairs: {repairs} | Passed: {pass_str}")
        
        res = CaseResult(
            case_id=case_id,
            category=category,
            expected_status=expected,
            actual_status=actual_status,
            passed=passed,
            latency_ms=latency,
            repair_count=repairs,
            tokens={"input": in_toks, "output": out_toks}
        )
        report.results.append(res)

    if report.total_cases > 0:
        report.avg_total_latency_ms = total_lat / report.total_cases
        report.avg_repair_count = total_reps / report.total_cases
        report.avg_input_tokens = total_in_toks / report.total_cases
        report.avg_output_tokens = total_out_toks / report.total_cases
        
    report.print_console()
    
    os.makedirs("reports", exist_ok=True)
    json_path = f"reports/eval_{dataset_name}_{timestamp}.json"
    md_path = f"reports/eval_{dataset_name}_{timestamp}.md"
    
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
    report.export_markdown(md_path)
    
    print(f"JSON Report saved to {json_path}")
    print(f"Markdown Report saved to {md_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Agent")
    parser.add_argument("--dataset", type=str, default="smoke", help="Dataset name (smoke or full)")
    args = parser.parse_args()
    
    file_path = f"tests/evaluation/dataset_{args.dataset}.json"
    asyncio.run(evaluate_agent(file_path))
