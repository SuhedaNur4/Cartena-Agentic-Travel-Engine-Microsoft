import asyncio
import os
import sys
import uuid
import copy

from backend.core.config import Settings
from backend.core.container import build
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
from backend.domain.models.itinerary import Itinerary, Day, ActivityBlock, MealSuggestion

async def main():
    settings = Settings()
    container = build(settings)
    repo = container.itinerary_repo
    use_case = container.regenerate_day

    print("==================================================")
    print("SETTING UP INITIAL ITINERARY")
    print("==================================================")
    
    req = TripRequest(
        destination="Paris",
        duration_days=3,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,)
    )
    
    def dummy_day(num):
        return Day(
            day_number=num,
            title=f"Title {num}",
            morning=ActivityBlock(description=f"Original Day {num} Morning"),
            afternoon=ActivityBlock(description=f"Original Day {num} Afternoon"),
            evening=ActivityBlock(description=f"Original Day {num} Evening"),
            meals=MealSuggestion(),
            budget_estimate=BudgetLevel.MEDIUM,
            tips=[f"Tip {num}"]
        )

    # Create a baseline itinerary with 3 days
    itinerary_id = str(uuid.uuid4())
    itinerary = Itinerary(
        id=itinerary_id,
        trip_request=req,
        days=[dummy_day(1), dummy_day(2), dummy_day(3)],
        model_used="test"
    )
    await repo.save(itinerary)
    print(f"Created baseline itinerary: {itinerary_id}")

    original_llm = container.regenerate_day._llm

    # ─────────────────────────────────────────────────────────────────────────
    print("\n==================================================")
    print("CASE 1 & 2 & 4: Successful Replacement, Others Unchanged, Reason Injection")
    print("==================================================")
    
    class SuccessPartialLLMClient:
        def __init__(self, original):
            self.model_name = original.model_name
            self.last_user_prompt = ""
            
        async def stream(self, system_prompt, user_prompt, expected_days):
            self.last_user_prompt = user_prompt
            # Return ONLY Day 2
            yield "Day 2: Newly Generated Day 2\n"
            yield "Morning: New Museum Visit\n"
            yield "Afternoon: Walk by Seine\n"
            yield "Evening: New Dinner spot\n"
            yield "Breakfast: Croissant\n"
            yield "Lunch: Escargot\n"
            yield "Dinner: Steak Frites\n"
            yield "Tips:\n- Bring camera\n"

    success_llm = SuccessPartialLLMClient(original_llm)
    container.regenerate_day._llm = success_llm

    reason = "I want more museums"
    print(f"Requesting regeneration for Day 2 with reason: '{reason}'")
    
    async for event in use_case.execute(itinerary_id, 2, reason=reason):
        if event.get("type") == "error":
            print(f"ERROR: {event['message']}")
    
    # Verification
    # Case 4: Check if reason was injected
    if reason in success_llm.last_user_prompt and "Regenerate ONLY Day 2" in success_llm.last_user_prompt:
        print("[PASS] Case 4 Passed: Reason and Partial Mode instructions successfully injected into prompt.")
    else:
        print("[FAIL] Case 4 Failed: Prompt did not contain expected partial instructions.")
        sys.exit(1)

    # Fetch updated itinerary
    updated_itinerary = await repo.get(itinerary_id)
    
    # Case 1 & 2: Check day contents
    day1 = updated_itinerary.days[0]
    day2 = updated_itinerary.days[1]
    day3 = updated_itinerary.days[2]

    if day1.morning.description == "Original Day 1 Morning" and day3.morning.description == "Original Day 3 Morning":
        print("[PASS] Case 2 Passed: Day 1 and Day 3 remain completely unchanged.")
    else:
        print("[FAIL] Case 2 Failed: Other days were modified.")
        sys.exit(1)

    if day2.morning.description == "New Museum Visit":
        print("[PASS] Case 1 Passed: Day 2 successfully replaced with new generation.")
    else:
        print("[FAIL] Case 1 Failed: Day 2 was not replaced correctly.")
        sys.exit(1)

    # ─────────────────────────────────────────────────────────────────────────
    print("\n==================================================")
    print("CASE 3: Validation Failure Scenario")
    print("==================================================")

    class FailingPartialLLMClient:
        def __init__(self, original):
            self.model_name = original.model_name
            
        async def stream(self, system_prompt, user_prompt, expected_days):
            # We simulate a constraint violation.
            # Omit Afternoon to trigger a hard validation failure (Missing time-slot descriptions).
            yield "Day 2: Bad Generation\n"
            yield "Morning: Museum\n"
            yield "Evening: Nothing\n"
            yield "Breakfast: Coffee\n"
            yield "Tips:\n- Stay hydrated\n"

    container.regenerate_day._llm = FailingPartialLLMClient(original_llm)

    print("Requesting regeneration for Day 2 with an invalid LLM output...")
    
    error_caught = False
    async for event in use_case.execute(itinerary_id, 2, reason="Make it bad"):
        if event.get("type") == "error":
            print(f"Caught expected error: {event['message']}")
            error_caught = True

    if error_caught:
        print("[PASS] Case 3 Passed: Validation failure was correctly caught and emitted as an error.")
    else:
        print("[FAIL] Case 3 Failed: No error was emitted during a validation failure.")
        sys.exit(1)

    # Verify that the DB was not overwritten with the bad day
    final_itinerary = await repo.get(itinerary_id)
    if final_itinerary.days[1].morning.description == "New Museum Visit":
        print("[PASS] Case 3 Extra Pass: Database was protected; the invalid itinerary was not saved.")
    else:
        print("[FAIL] Case 3 Failed: Database was overwritten with an invalid itinerary!")
        sys.exit(1)

    print("\nALL TESTS PASSED FOR PARTIAL REGENERATION!")

if __name__ == "__main__":
    asyncio.run(main())
