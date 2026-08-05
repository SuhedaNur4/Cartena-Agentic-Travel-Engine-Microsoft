import asyncio
import os
import shutil
import uuid
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.core.config import Settings
from backend.core.container import build
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest

async def main():
    settings = Settings()
    # Clean up checkpoints for a fresh test
    checkpoints_dir = os.path.join(os.path.dirname(settings.sqlite_db_path), ".checkpoints")
    if os.path.exists(checkpoints_dir):
        shutil.rmtree(checkpoints_dir)
    
    container = build(settings)
    use_case = container.generate_itinerary

    print("==================================================")
    print("TEST 1: Normal generation regression test")
    print("==================================================")
    req = TripRequest(
        destination="London",
        duration_days=2,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,)
    )
    
    original_llm = container.generate_itinerary._engine._llm
    
    class SuccessLLMClient:
        def __init__(self, original):
            self.original = original
            self.model_name = original.model_name
            
        async def stream(self, system_prompt, user_prompt, expected_days):
            print("\n>>> MOCK LLM: Returning valid mock itinerary...")
            yield f"Day 1: Exploring\n"
            yield "Morning: Visit Museum\n"
            yield "Afternoon: Walk in Park\n"
            yield "Evening: Night Market\n"
            yield "Breakfast: Cafe\n"
            yield "Lunch: Sandwich\n"
            yield "Dinner: Restaurant\n"
            yield "Tips: Bring water\n"
            if expected_days > 1:
                yield f"Day 2: More Exploring\n"
                yield "Morning: Another Museum\n"
                yield "Afternoon: Another Park\n"
                yield "Evening: Another Market\n"
                yield "Breakfast: Another Cafe\n"
                yield "Lunch: Another Sandwich\n"
                yield "Dinner: Another Restaurant\n"
                yield "Tips: Bring more water\n"

    container.generate_itinerary._engine._llm = SuccessLLMClient(original_llm)
    
    normal_id = str(uuid.uuid4())
    async for event in use_case.execute(request=req, workflow_id=normal_id):
        if event.get("type") == "chunk":
            print(event["content"], end="", flush=True)
        else:
            print(f"\nEVENT: {event}")
    
    print("\n\n==================================================")
    print("TEST 2 & 3: Forced interruption and checkpoint creation")
    print("==================================================")
    
    original_llm = container.generate_itinerary._engine._llm
    
    class FaultyLLMClient:
        def __init__(self, original):
            self.original = original
            self.model_name = original.model_name
            
        async def stream(self, system_prompt, user_prompt, expected_days):
            print("\n>>> MOCK LLM: Injecting forced exception to simulate failure!")
            yield "Day 1: "
            raise Exception("Forced LLM Interruption")

    class SuccessLLMClient:
        def __init__(self, original):
            self.original = original
            self.model_name = original.model_name
            
        async def stream(self, system_prompt, user_prompt, expected_days):
            print("\n>>> MOCK LLM: Returning valid mock itinerary...")
            yield f"Day 1: Exploring\n"
            yield "Morning: Visit Museum\n"
            yield "Afternoon: Walk in Park\n"
            yield "Evening: Night Market\n"
            yield "Breakfast: Cafe\n"
            yield "Lunch: Sandwich\n"
            yield "Dinner: Restaurant\n"
            yield "Tips: Bring water\n"

    # Inject the faulty LLM
    container.generate_itinerary._engine._llm = FaultyLLMClient(original_llm)
    
    interrupt_req = TripRequest(
        destination="Tokyo",
        duration_days=1,
        budget=BudgetLevel.LOW,
        interests=(Interest.FOOD,)
    )
    interrupt_id = str(uuid.uuid4())
    
    async for event in use_case.execute(request=interrupt_req, workflow_id=interrupt_id):
        if event.get("type") == "chunk":
            print(event["content"], end="", flush=True)
        else:
            print(f"\nEVENT: {event}")
        
    print(f"\n\nVerifying checkpoint exists for {interrupt_id}...")
    repo = container.checkpoint_repo
    state = await repo.get(interrupt_id)
    if state:
        print(f"✅ Checkpoint found! resume_from_node = '{state.resume_from_node}'")
    else:
        print("❌ Checkpoint NOT found!")
        sys.exit(1)
        
    print("\n==================================================")
    print("TEST 4: Resume execution test using the same workflow_id")
    print("==================================================")
    
    # Restore with Success LLM to complete the run
    container.generate_itinerary._engine._llm = SuccessLLMClient(original_llm)
    
    print(f"Resuming workflow {interrupt_id} without sending a new request...")
    async for event in use_case.execute(workflow_id=interrupt_id):
        if event.get("type") == "chunk":
            print(event["content"], end="", flush=True)
        else:
            print(f"\nEVENT: {event}")
        
    print("\n\nDone!")

if __name__ == "__main__":
    asyncio.run(main())
