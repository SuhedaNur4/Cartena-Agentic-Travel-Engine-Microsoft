"""
Domain service: PromptBuilder.

Pure function — no I/O, no external dependencies, fully unit-testable.
Assembles the RAG-augmented prompt string from structured inputs.
"""

from __future__ import annotations

from backend.domain.models.trip_request import BudgetLevel, TripRequest
from backend.domain.services import constraint_map as _constraint_map

# ── Prompt template ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are Cartena, an elite travel architect and local expert.
Your task is to craft a highly specific, thoughtful, and pragmatic day-by-day itinerary.

[CRITICAL RULES & PERSONA]
1. DO NOT be repetitive. Avoid using the same verbs repeatedly (e.g., "Start your day with...", "Head over to...").
2. DO NOT use generic filler ("This bustling market is a feast for the senses").
3. DO NOT recommend physically impossible schedules (allow time for transit and rest).
4. DO NOT repeat the same activity or restaurant across multiple days.
5. Provide actionable, insider-level advice.
6. The `why_recommended` field must be brief and specific (e.g., "Best sunset view in the city, usually less crowded on weekdays.").

[STRICT OUTPUT CONTRACT v1]
- NO CONVERSATIONAL PREAMBLE OR REASONING: Do NOT write introductory thoughts, chain-of-thought, or conversational text (e.g. "Okay, let's see...", "First, I will structure...", "Here is your itinerary...").
- START IMMEDIATELY WITH: Your very first characters MUST be "Day 1: " followed by the day's title.
- REQUIRED STRUCTURE FOR EVERY DAY: You MUST include Morning, Afternoon, Evening, Breakfast, Lunch, Dinner, and Tips for every single day. Do not skip any section.
- CONCISE WRITING: Keep activity descriptions concise and punchy (1-2 short sentences per block) to ensure the entire multi-day itinerary completes within the token budget.
"""

_USER_TEMPLATE = """\
[USER REQUEST & CONSTRAINTS]
Destination: {destination}
Duration: {duration_days} days
Budget level: {budget}
Interests: {interests}

[CRITICAL USER NOTES]
The user specifically requested:
{notes}
>> YOU MUST TAILOR THE ENTIRE ITINERARY AROUND THESE NOTES. IF THEY MENTION DIETARY RESTRICTIONS (e.g., Vegetarian), DO NOT SUGGEST INCOMPATIBLE MEALS. IF THEY HAVE MOBILITY LIMITATIONS, KEEP TRANSIT EASY.

[BUDGET GUIDANCE]
Budget level: {budget} — estimated daily spending for {destination}: {budget_guidance}
This is a planning reference. The actual financial validation is done server-side.
Do NOT exceed this budget tier when recommending restaurants, tours, or entrance fees.

[RETRIEVED LOCAL KNOWLEDGE]
{knowledge_header}
{rag_context}
{online_context_block}

Generate a complete {duration_days}-day itinerary for {destination}.
You MUST format your response as Markdown text following exactly this {duration_days}-day skeleton structure:

{skeleton_block}

[OUTPUT CONTRACT v1 — CRITICAL INSTRUCTIONS]
1. DO NOT output JSON. DO NOT output any introductory text, reasoning, or conversational preamble.
2. YOUR VERY FIRST WORDS MUST BE "Day 1: ". Do NOT say "Here is..." or "Okay...".
3. Write concisely so that all {duration_days} days (from Day 1 to Day {duration_days}) are fully generated without being cut off.
"""

_ON_TOPIC_HEADER = """\
The following facts about {destination} were retrieved from our curated knowledge base.
Use this information ONLY if it is highly relevant to the user's interests. Do not blindly copy-paste facts."""

_OFF_TOPIC_HEADER = """\
Our curated knowledge base has no entries for {destination}.
The notes below are examples from OTHER destinations and are NOT about {destination}.
Use them ONLY as a style reference for tone and level of detail.
DO NOT state any of these facts as if they applied to {destination}."""

_NO_KNOWLEDGE_HEADER = """\
No specific local knowledge is available for {destination} in our curated knowledge base.
Use your best general knowledge, and prefer concrete, verifiable specifics over generic filler."""


def build(
    request: TripRequest,
    rag_chunks: list[str],
    online_context: list[str] | None = None,
    chunks_are_off_topic: bool = False,
) -> tuple[str, str]:
    """
    RAG destekli prompt üretir.

    Args:
        rag_chunks: Prompt'a eklenecek bilgi parçaları.
        online_context: Canlı gerçek dünya verisi (hava durumu, POI).
            Boş/None ise prompt'a hiç blok eklenmez.
        chunks_are_off_topic: True ise chunk'lar hedef şehre AİT DEĞİLDİR
            (KB miss fallback'i). Prompt bunu modele açıkça söyler; aksi
            hâlde model başka şehrin gerçeklerini hedef şehre atfeder.

    Returns:
        (system_prompt, user_prompt)
    """
    # Üç bilgi durumu. Başlık ile içerik asla çelişmemeli: önceki hâl,
    # chunk yokken bile "şu gerçekler getirildi" diyordu.
    if not rag_chunks:
        knowledge_header = _NO_KNOWLEDGE_HEADER.format(destination=request.destination)
        rag_context = ""
    elif chunks_are_off_topic:
        knowledge_header = _OFF_TOPIC_HEADER.format(destination=request.destination)
        # Payload sanitization: label each off-topic chunk explicitly so the LLM
        # cannot silently misattribute another city's facts to the destination.
        rag_context = "\n\n".join(
            f"[STYLE REFERENCE — NOT about {request.destination}]\n{chunk}"
            for chunk in rag_chunks
        )
    else:
        knowledge_header = _ON_TOPIC_HEADER.format(destination=request.destination)
        # Payload sanitization: label each chunk with its origin so the LLM
        # treats each piece as a distinct, citable fact rather than a continuous block.
        # This mirrors the principle of never sending raw ambiguous data to the LLM —
        # each chunk is pre-labelled to constrain how the model can interpret it.
        rag_context = "\n\n".join(
            f"[KB FACT {i} — {request.destination}]\n{chunk}"
            for i, chunk in enumerate(rag_chunks, 1)
        )

    # Canlı bağlam (hava durumu, POI). Adapter'lar bugün stub ve boş liste
    # döndürüyor; blok yalnızca gerçek veri geldiğinde görünür.
    online_context_block = ""
    if online_context:
        items = "\n".join(f"• {item}" for item in online_context)
        online_context_block = (
            f"\n[LIVE CONTEXT]\n"
            f"Current real-world information for {request.destination}:\n{items}\n"
        )

    interests_str = ", ".join(i.value for i in request.interests)
    notes_str = request.notes.strip() if request.notes else "None provided."
    skeleton_block = get_skeleton(request.duration_days)
    budget_guidance = _build_budget_guidance(request)

    user_prompt = _USER_TEMPLATE.format(
        destination=request.destination,
        duration_days=request.duration_days,
        budget=request.budget.value,
        interests=interests_str,
        notes=notes_str,
        knowledge_header=knowledge_header,
        rag_context=rag_context,
        online_context_block=online_context_block,
        skeleton_block=skeleton_block,
        budget_guidance=budget_guidance,
    )

    return _SYSTEM_PROMPT, user_prompt


def get_skeleton(duration_days: int) -> str:
    """Returns a visual multi-day Markdown skeleton anchor for the LLM."""
    lines = []
    for day_num in range(1, duration_days + 1):
        lines.append(f"Day {day_num}: [Title of Day {day_num}]")
        lines.append("Morning: [description of morning activities with location/costs]")
        lines.append("Afternoon: [description of afternoon activities with location/costs]")
        lines.append("Evening: [description of evening activities with location/costs]")
        lines.append("Breakfast: [meal suggestion]")
        lines.append("Lunch: [meal suggestion]")
        lines.append("Dinner: [meal suggestion]")
        lines.append("Tips:")
        lines.append("- [tip 1]")
        lines.append("- [tip 2]")
        if day_num < duration_days:
            lines.append("")
    return "\n".join(lines)


def _build_budget_guidance(request: TripRequest) -> str:
    """
    Produce a concise, destination-aware budget sentence for the LLM.

    Examples:
      "~$60/day (activities + meals; budget tier: low)"
      "~$130/day (activities + meals; budget tier: medium)"

    The actual arithmetic enforcement is done by the Python Validator —
    this is only a planning reference to anchor the LLM's suggestions.
    """
    limit = _constraint_map._daily_budget_usd(request.budget, request.destination)
    tier = request.budget.value
    if limit is None:
        return f"Luxury tier — no daily ceiling. Prioritize quality and exclusivity."
    return f"~${limit}/day (activities + meals; budget tier: {tier})"

