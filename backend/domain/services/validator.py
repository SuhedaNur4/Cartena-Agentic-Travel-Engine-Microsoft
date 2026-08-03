"""
Domain service: ItineraryValidator (Validation & Constraint Engine).

Pure domain logic — zero external I/O or infrastructure dependencies.
Evaluates generated Itinerary objects against hard and soft constraints.
Produces a ViolationReport that can either certify validity or generate
a targeted repair prompt for the LLM re-plan loop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from backend.domain.models.itinerary import Itinerary, Day
from backend.domain.models.trip_request import BudgetLevel
from backend.domain.models.resolution import ResolutionOption


@dataclass
class ViolationReport:
    """Structured validation report separating hard violations from soft quality metrics."""
    is_valid: bool
    hard_violations: list[str] = field(default_factory=list)
    soft_warnings: list[str] = field(default_factory=list)
    resolutions: list[ResolutionOption] = field(default_factory=list)
    constraint_score: float = 1.0
    quality_score: float = 1.0

    def to_repair_prompt(self, expected_days: int | None = None) -> str:
        """
        Formats hard violations into an actionable, precise instruction for the LLM repair loop.
        Never says "write a better plan" — explicitly lists what failed and enforces the skeleton.
        """
        if self.is_valid or not self.hard_violations:
            return ""

        from backend.domain.services.prompt_builder import get_skeleton
        skeleton = get_skeleton(expected_days) if expected_days else ""
        skeleton_section = f"\nRequired structure:\n\n{skeleton}\n" if skeleton else ""

        violations_text = "\n".join(f"{idx}. {v}" for idx, v in enumerate(self.hard_violations, 1))
        return (
            "You produced an invalid itinerary.\n"
            "DO NOT change the output structure.\n"
            f"{skeleton_section}\n"
            "Violations:\n"
            f"{violations_text}\n\n"
            "Repair ONLY these violations.\n"
            "Return the COMPLETE itinerary.\n"
            "Do not explain your changes.\n"
            "Do not omit any day.\n"
            "Do not use a different format."
        )


class ItineraryValidator:
    """
    Evaluates an Itinerary against user requests and explicit evaluation constraints.
    """

    @classmethod
    def validate(
        cls,
        itinerary: Itinerary,
        constraints: dict | None = None,
    ) -> ViolationReport:
        """
        Executes all validation checks and returns a complete ViolationReport.
        """
        constraints = constraints or {}
        hard_violations: list[str] = []
        soft_warnings: list[str] = []

        total_hard_checks = 5
        passed_hard_checks = 0

        # ── 1. Duration & Structure Check (Hard) ─────────────────────────────
        if not itinerary.is_complete():
            hard_violations.append(
                f"Duration mismatch: You generated {len(itinerary.days)} days, but you MUST generate exactly {itinerary.duration_days} days (from Day 1 to Day {itinerary.duration_days}). Do not stop early or generate extra days."
            )
        else:
            passed_hard_checks += 1

        # ── 2. Budget Adherence Check (Hard) ─────────────────────────────────
        budget_passed = True
        daily_limit_jpy = constraints.get("daily_budget_limit") if constraints.get("currency") == "JPY" else None
        daily_limit_eur = constraints.get("daily_budget_limit") if constraints.get("currency") == "EUR" else None

        for day in itinerary.days:
            # Check if text explicitly mentions costs exceeding limits
            day_text = f"{day.morning.description} {day.afternoon.description} {day.evening.description} {day.morning.cost_estimate} {day.afternoon.cost_estimate} {day.evening.cost_estimate}"
            
            # Simple numeric regex check for JPY amounts exceeding limit
            if daily_limit_jpy:
                amounts = [int(re.sub(r"[^\d]", "", m)) for m in re.findall(r"(\d{1,3}(?:,\d{3})+|\d{4,6})\s*(?:JPY|yen|Yen|¥)", day_text)]
                if any(a > daily_limit_jpy for a in amounts):
                    hard_violations.append(f"Day {day.day_number}: Suggested activity cost exceeds daily budget limit of {daily_limit_jpy:,} JPY.")
                    budget_passed = False
                    break
            
            # Check for luxury mentions when budget is LOW/BUDGET
            if itinerary.trip_request.budget == BudgetLevel.LOW:
                if any(w in day_text.lower() for w in ["luxury", "fine dining", "expensive", "3-star michelin", "high-end"]):
                    hard_violations.append(f"Day {day.day_number}: Luxury/expensive dining or activity suggested for a budget-level trip.")
                    budget_passed = False
                    break

        if budget_passed:
            passed_hard_checks += 1

        # ── 3. Opening Hours & Date Constraints Check (Hard) ─────────────────
        hours_passed = True
        notes_lower = itinerary.trip_request.notes.lower()
        
        # Check Monday closures or early closing constraints
        for day in itinerary.days:
            day_full_text = f"{day.title} {day.morning.description} {day.afternoon.description} {day.evening.description}".lower()
            
            # Rule: If user notes mention Monday closure (e.g. Vatican/Museums), check if scheduled
            if "closed on monday" in notes_lower or "monday closure" in notes_lower:
                if "monday" in day.title.lower() and any(k in day_full_text for k in ["museum", "gallery", "vatican", "national museum"]):
                    hard_violations.append(f"Day {day.day_number} ({day.title}): Scheduled a museum/gallery on a Monday despite closure notes.")
                    hours_passed = False
                    break
            
            # Rule: If temple closing early at 17:00 (Kyoto rule), evening must not be temple visit
            if "kyoto" in itinerary.destination.lower() or "close early" in notes_lower or "17:00" in notes_lower:
                if any(k in day.evening.description.lower() for k in ["temple", "shrine", "kinkaku-ji", "kiyomizu-dera", "fushimi inari"]):
                    # Note: Fushimi Inari is open 24/7, but standard temples close at 17:00
                    if not any(open_late in day.evening.description.lower() for open_late in ["fushimi inari", "gion", "pontocho"]):
                        hard_violations.append(f"Day {day.day_number}: Evening activity suggests visiting a temple/shrine after typical 17:00 closing time.")
                        hours_passed = False
                        break

        if hours_passed:
            passed_hard_checks += 1

        # ── 4. Time Overlap & Flow Check (Hard) ──────────────────────────────
        flow_passed = True
        for day in itinerary.days:
            if not day.morning.description.strip() or not day.afternoon.description.strip() or not day.evening.description.strip():
                hard_violations.append(f"Day {day.day_number}: Missing time-slot descriptions (morning/afternoon/evening).")
                flow_passed = False
                break
            
            # Check repetition within the same day
            if day.morning.description.strip() == day.afternoon.description.strip():
                hard_violations.append(f"Day {day.day_number}: Morning and afternoon activities are identical.")
                flow_passed = False
                break

        if flow_passed:
            passed_hard_checks += 1

        # ── 5. Distance & Geographic Grouping Check (Hard) ───────────────────
        distance_passed = True
        walking_tol = constraints.get("walking_tolerance", "unspecified")
        group_required = constraints.get("group_nearby_required", False)

        # Only enforce walking distance when user has EXPLICITLY stated a low tolerance
        if walking_tol == "low":
            for day in itinerary.days:
                day_text = f"{day.morning.description} {day.afternoon.description} {day.evening.description}".lower()
                if any(k in day_text for k in ["long walk", "hike", "walk across the city", "hours of walking"]):
                    hard_violations.append(f"Day {day.day_number}: Suggests long walking/hiking despite low walking tolerance constraint.")
                    distance_passed = False
                    break

        if distance_passed:
            passed_hard_checks += 1

        # ── Calculate Hard Constraint Score ──────────────────────────────────
        constraint_score = max(0.0, passed_hard_checks / total_hard_checks)
        is_valid = len(hard_violations) == 0

        # ── 6. Soft Quality Metrics & Scoring (Soft) ─────────────────────────
        total_soft_checks = 4
        passed_soft_checks = 0

        # Quality 1: Preference Match
        interests = [i.value for i in itinerary.trip_request.interests]
        all_text_lower = " ".join(
            f"{d.title} {d.morning.description} {d.afternoon.description} {d.evening.description}"
            for d in itinerary.days
        ).lower()

        pref_matched = any(interest in all_text_lower or any(kw in all_text_lower for kw in _get_keywords_for_interest(interest)) for interest in interests)
        if pref_matched:
            passed_soft_checks += 1
        else:
            soft_warnings.append("Preference match warning: Generated activities do not strongly reflect user's selected interests.")

        # Quality 2: Meal Suggestions Presence
        meals_complete = all(d.meals.breakfast and d.meals.lunch and d.meals.dinner for d in itinerary.days)
        if meals_complete:
            passed_soft_checks += 1
        else:
            soft_warnings.append("Meal suggestions warning: Some days are missing specific breakfast, lunch, or dinner suggestions.")

        # Quality 3: Actionable Tips
        tips_present = all(len(d.tips) >= 1 for d in itinerary.days)
        if tips_present:
            passed_soft_checks += 1
        else:
            soft_warnings.append("Tips warning: Missing practical insider tips on some days.")

        # Quality 4: Absence of Cross-Day POI Repetition (soft warning)
        # Hard violations are NOT raised for repetition — some repeat visits are legitimate
        # (e.g., transiting through the same station). Only flag identical day titles.
        titles = [d.title.strip().lower() for d in itinerary.days if d.title.strip()]
        if len(titles) == len(set(titles)):
            passed_soft_checks += 1
        else:
            soft_warnings.append("Diversity warning: Repetitive daily titles or themes detected across days.")

        # Cross-day POI name repetition: soft warning only
        all_day_descriptions = []
        for d in itinerary.days:
            day_blob = (
                f"{d.morning.description} {d.afternoon.description} {d.evening.description}"
            ).lower()
            all_day_descriptions.append(day_blob)

        # Build a set of significant location tokens (3+ chars, not stop-words)
        _STOP = {"the", "and", "for", "with", "from", "that", "this", "are", "you", "your", "have"}
        seen_pois: dict[str, int] = {}   # poi_token -> first day number
        repeated: list[str] = []
        for day_idx, blob in enumerate(all_day_descriptions, start=1):
            tokens = set(t.strip(",.:;") for t in blob.split() if len(t) > 4 and t not in _STOP)
            for token in tokens:
                if token in seen_pois and seen_pois[token] != day_idx:
                    if token not in repeated:
                        repeated.append(token)
                else:
                    seen_pois.setdefault(token, day_idx)
        if repeated:
            soft_warnings.append(
                f"Cross-day repetition warning: The following activity references appear on multiple days: "
                + ", ".join(repeated[:5]) + "."
            )

        quality_score = max(0.0, passed_soft_checks / total_soft_checks)

        # ── 7. Generate HITL Resolutions for Hard Violations ────────────────
        resolutions = []
        if not is_valid:
            from backend.domain.models.resolution import ResolutionOption, ResolutionAction
            
            # Check if budget was a problem
            budget_failed = any("budget" in v.lower() for v in hard_violations)
            if budget_failed:
                if itinerary.trip_request.budget.value != "high":
                    resolutions.append(ResolutionOption(
                        id="increase_budget",
                        label="Günlük bütçeyi bir üst seviyeye çıkar",
                        action=ResolutionAction(type="update_budget", value="high")
                    ))
            
            # Generic resolutions
            resolutions.append(ResolutionOption(
                id="relax_constraints",
                label="Kısıtlamaları esnet (Aktiviteleri daha ucuz/uygun seç)",
                action=ResolutionAction(type="append_reason", value="Kısıtlamaları esnet")
            ))
            resolutions.append(ResolutionOption(
                id="retry",
                label="Tekrar Dene",
                action=ResolutionAction(type="retry", value="retry")
            ))

        return ViolationReport(
            is_valid=is_valid,
            hard_violations=hard_violations,
            soft_warnings=soft_warnings,
            resolutions=resolutions,
            constraint_score=round(constraint_score, 2),
            quality_score=round(quality_score, 2),
        )


def _get_keywords_for_interest(interest: str) -> list[str]:
    mapping = {
        "culture": ["museum", "temple", "shrine", "history", "art", "gallery", "heritage", "palace"],
        "food": ["restaurant", "sushi", "bistro", "tasting", "ramen", "market", "cafe", "dining", "food"],
        "entertainment": ["anime", "manga", "gaming", "akihabara", "tech", "shibuya", "nakano", "show", "theater"],
        "shopping": ["mall", "boutique", "market", "street", "shopping", "store", "ginza", "harajuku"],
        "nature": ["garden", "park", "bamboo", "river", "mountain", "scenic", "view", "walk"],
    }
    return mapping.get(interest.lower(), [interest.lower()])
