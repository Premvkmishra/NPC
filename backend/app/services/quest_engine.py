import json
import random
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models import PlayerModel, PreferencesModel, QuestModel
from app.schemas import (
    Category, Difficulty, Quest, QuestLocation, QuestSource,
    Preferences
)
from app.services.serp import get_experiences_for_category, DEFAULT_MUMBAI_LAT, DEFAULT_MUMBAI_LNG
from app.services.llm import call_llm, mock_quest_builder

XP_MAP: Dict[Difficulty, int] = {
    "easy": 50,
    "medium": 100,
    "hard": 150
}

ALL_CATEGORIES: List[Category] = ["explore", "social", "creativity", "courage", "awareness"]

NO_LOCATION_FALLBACKS: Dict[Category, Dict[str, Any]] = {
    "explore": {
        "title": "Take a completely different route home",
        "description": "Turn down a street you usually walk past. Walk it slowly and look up at the second-floor balconies and street signs.",
        "why_selected": "Small daily route detours break autopilot and re-train your spatial curiosity.",
        "difficulty": "easy",
        "duration_minutes": 25,
        "estimated_cost_inr": 0,
        "cost_label": "Free",
        "reflection_prompt": "What did you see on that street that made you wonder why you'd never taken it before?"
    },
    "creativity": {
        "title": "Ten-minute blind contour sketch",
        "description": "Find an everyday object or view. Without lifting your pen or looking down at your paper for 5 minutes, draw its contours.",
        "why_selected": "Pure creativity without perfectionism or performance pressure.",
        "difficulty": "easy",
        "duration_minutes": 20,
        "estimated_cost_inr": 0,
        "cost_label": "Free",
        "reflection_prompt": "How did it feel to let go of trying to make it look 'good'?"
    },
    "social": {
        "title": "Ask for an authentic recommendation",
        "description": "Next time you are at a counter or stall, ask the person: 'What is your favourite thing around here that people overlook?'",
        "why_selected": "A gentle, respectful micro-interaction with someone who knows the area.",
        "difficulty": "easy",
        "duration_minutes": 15,
        "estimated_cost_inr": 0,
        "cost_label": "Free",
        "reflection_prompt": "What did they tell you, and did their expression change when you asked?"
    },
    "courage": {
        "title": "Eat somewhere with no online reviews",
        "description": "Choose a small local eatery or tapri based purely on the smell and the crowd, not a star rating on your phone.",
        "why_selected": "A low-stakes courage challenge to trust your senses over algorithmic ratings.",
        "difficulty": "medium",
        "duration_minutes": 35,
        "estimated_cost_inr": None,
        "cost_label": "Cost unknown",
        "reflection_prompt": "Was taking a small gamble worth the experience?"
    },
    "awareness": {
        "title": "Pocket your phone for a 15-minute walk",
        "description": "Leave your phone completely in your pocket or bag. Walk a single block and count ten things you would have missed while staring at a screen.",
        "why_selected": "An unplugged sensory reset to bring you back into your surroundings.",
        "difficulty": "easy",
        "duration_minutes": 15,
        "estimated_cost_inr": 0,
        "cost_label": "Free",
        "reflection_prompt": "Which of the ten things surprised you the most?"
    }
}

def choose_category(
    requested_category: Optional[Category],
    prefs: Preferences,
    recent_quests: List[QuestModel]
) -> Category:
    # 1. If explicit category requested, use it
    if requested_category and requested_category in ALL_CATEGORIES:
        return requested_category

    # 2. Check last 2 categories to avoid repeating > 2 times in a row
    last_two = [q.category for q in recent_quests[:2]]
    forbidden: Optional[str] = None
    if len(last_two) >= 2 and last_two[0] == last_two[1]:
        forbidden = last_two[0]

    available = [c for c in ALL_CATEGORIES if c != forbidden]

    # Count historical completions by category
    counts = {c: 0 for c in ALL_CATEGORIES}
    for q in recent_quests:
        if q.status == "completed" and q.category in counts:
            counts[q.category] += 1

    # Weight towards least completed categories
    sorted_cats = sorted(available, key=lambda c: counts.get(c, 0))

    # Stretch category chance ~25% scaled by comfort level (1..5)
    stretch_chance = 0.25 * (prefs.comfort_level / 3.0)
    if random.random() < stretch_chance and len(sorted_cats) > 1:
        # Pick from the second half or random available
        return random.choice(sorted_cats)

    return sorted_cats[0]

def validate_candidate(
    candidate: Dict[str, Any],
    exp: Any,
    prefs: Preferences,
    recent_titles: set,
    recent_exp_ids: set
) -> bool:
    # Duration check
    duration = candidate.get("duration_minutes", 45)
    if duration > prefs.free_time_minutes:
        return False

    # Distance check
    if exp and exp.distance_km is not None:
        if exp.distance_km > prefs.max_distance_km:
            return False

    # Budget check
    est_cost = candidate.get("estimated_cost_inr")
    if est_cost is not None and est_cost > prefs.budget_inr:
        return False

    # Title / Exp repeat check
    title = candidate.get("title", "")
    if title in recent_titles:
        return False
    if exp and exp.id in recent_exp_ids:
        return False

    # Accessibility check
    if prefs.accessibility_notes:
        notes_lower = prefs.accessibility_notes.lower()
        title_lower = title.lower()
        desc_lower = candidate.get("description", "").lower()
        if any(w in notes_lower for w in ["wheelchair", "walking", "stairs", "strenuous"]):
            if any(w in title_lower or w in desc_lower for w in ["steep", "hike", "stairs", "climb", "monolith"]):
                return False

    return True

def generate_quest(
    player: PlayerModel,
    prefs: Preferences,
    db: Session,
    requested_category: Optional[Category] = None
) -> Quest:
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. Profile: load history
    past_quests = db.query(QuestModel).filter(QuestModel.player_id == player.id).order_by(QuestModel.created_at.desc()).all()
    recent_titles = {q.title for q in past_quests[:15]}
    recent_exp_ids = set()
    for q in past_quests[:15]:
        if q.source:
            try:
                s_json = json.loads(q.source) if isinstance(q.source, str) else q.source
                if s_json.get("title"):
                    recent_exp_ids.add(s_json["title"])
            except Exception:
                pass

    # 2. Gap analysis
    target_category = choose_category(requested_category, prefs, past_quests)

    # 3. Search SerpApi
    experiences = get_experiences_for_category(
        category=target_category,
        city=prefs.city or "Mumbai",
        lat=prefs.lat,
        lng=prefs.lng,
        max_distance_km=prefs.max_distance_km,
        db=db
    )

    # Top candidates (up to 5)
    candidates = experiences[:5]

    # 4 & 5. Generate & Validate with up to 2 attempts before fallback
    selected_quest_data = None
    selected_exp = None
    failures = 0

    player_summary = {
        "display_name": prefs.display_name,
        "interests": prefs.interests,
        "free_time_minutes": prefs.free_time_minutes,
        "budget_inr": prefs.budget_inr,
        "max_distance_km": prefs.max_distance_km,
        "comfort_level": prefs.comfort_level
    }

    for exp in candidates:
        if failures >= 2:
            break

        exp_dict = {
            "id": exp.id,
            "kind": exp.kind,
            "title": exp.title,
            "subtitle": exp.subtitle,
            "tag": exp.tag,
            "address": exp.address,
            "price_label": exp.price_label,
            "why_worth_it": exp.why_worth_it,
            "distance_km": exp.distance_km
        }

        # Try generating via LLM or template
        quest_json = None
        prompt = (
            f"You are the Game Master for NPC, an adventure app. Create a side quest in strict JSON.\n"
            f"Profile: {json.dumps(player_summary)}\n"
            f"Target Category: {target_category}\n"
            f"Candidate Experience: {json.dumps(exp_dict)}\n"
            f"JSON Schema: {{\"title\": str, \"description\": str, \"why_selected\": str, \"difficulty\": \"easy\"|\"medium\"|\"hard\", "
            f"\"duration_minutes\": int, \"estimated_cost_inr\": int|null, \"cost_label\": str, \"reflection_prompt\": str, \"chosen_experience_id\": str}}\n"
            f"Rules: Tone must be playful and short. Never invent places. Must use chosen candidate."
        )
        llm_out = call_llm(prompt, json_mode=True)
        if llm_out:
            try:
                parsed = json.loads(llm_out)
                if isinstance(parsed, dict) and "title" in parsed and "description" in parsed:
                    quest_json = parsed
            except Exception:
                quest_json = None

        if not quest_json:
            quest_json = mock_quest_builder(target_category, exp_dict, player_summary)

        # Validate
        if validate_candidate(quest_json, exp, prefs, recent_titles, recent_exp_ids):
            selected_quest_data = quest_json
            selected_exp = exp
            break
        else:
            failures += 1

    # Fallback if invalid or no candidate
    if not selected_quest_data:
        fallback = NO_LOCATION_FALLBACKS.get(target_category, NO_LOCATION_FALLBACKS["explore"])
        diff: Difficulty = fallback["difficulty"]
        quest_id = f"q_{uuid.uuid4().hex[:10]}"
        new_quest = QuestModel(
            id=quest_id,
            player_id=player.id,
            title=fallback["title"],
            description=fallback["description"],
            why_selected=fallback["why_selected"],
            category=target_category,
            difficulty=diff,
            duration_minutes=fallback["duration_minutes"],
            estimated_cost_inr=fallback["estimated_cost_inr"],
            cost_label=fallback["cost_label"],
            xp_reward=XP_MAP[diff],
            status="suggested",
            location=None,
            source=None,
            reflection_prompt=fallback["reflection_prompt"],
            created_at=now_iso,
            started_at=None,
            completed_at=None
        )
        db.add(new_quest)
        db.commit()
        db.refresh(new_quest)
        return Quest(
            id=new_quest.id,
            title=new_quest.title,
            description=new_quest.description,
            why_selected=new_quest.why_selected,
            category=new_quest.category, # type: ignore
            difficulty=new_quest.difficulty, # type: ignore
            duration_minutes=new_quest.duration_minutes,
            estimated_cost_inr=new_quest.estimated_cost_inr,
            cost_label=new_quest.cost_label,
            xp_reward=new_quest.xp_reward,
            status=new_quest.status, # type: ignore
            location=None,
            source=None,
            reflection_prompt=new_quest.reflection_prompt,
            created_at=new_quest.created_at,
            started_at=new_quest.started_at,
            completed_at=new_quest.completed_at
        )

    # Build Quest from selected Experience
    diff = selected_quest_data.get("difficulty", "easy")
    if diff not in XP_MAP:
        diff = "easy"
    xp_reward = XP_MAP[diff]

    maps_url = selected_exp.link_url or f"https://www.google.com/maps/search/?api=1&query={selected_exp.title}"
    location = QuestLocation(
        name=selected_exp.title,
        address=selected_exp.address,
        lat=selected_exp.lat,
        lng=selected_exp.lng,
        distance_km=selected_exp.distance_km,
        maps_url=maps_url
    )
    source = QuestSource(
        type=selected_exp.source,
        title=selected_exp.title,
        url=selected_exp.link_url,
        thumbnail_url=selected_exp.thumbnail_url,
        fetched_at=selected_exp.fetched_at
    )

    quest_id = f"q_{uuid.uuid4().hex[:10]}"
    duration = min(int(selected_quest_data.get("duration_minutes", 45)), prefs.free_time_minutes)
    cost = selected_quest_data.get("estimated_cost_inr")
    cost_label = selected_quest_data.get("cost_label") or ("Free" if cost == 0 else "Cost unknown")

    new_quest = QuestModel(
        id=quest_id,
        player_id=player.id,
        title=selected_quest_data["title"],
        description=selected_quest_data["description"],
        why_selected=selected_quest_data["why_selected"],
        category=target_category,
        difficulty=diff,
        duration_minutes=duration,
        estimated_cost_inr=cost,
        cost_label=cost_label,
        xp_reward=xp_reward,
        status="suggested",
        location=location.model_dump_json(),
        source=source.model_dump_json(),
        reflection_prompt=selected_quest_data.get("reflection_prompt", "What stood out most about this visit?"),
        created_at=now_iso,
        started_at=None,
        completed_at=None
    )
    db.add(new_quest)
    db.commit()
    db.refresh(new_quest)

    return Quest(
        id=new_quest.id,
        title=new_quest.title,
        description=new_quest.description,
        why_selected=new_quest.why_selected,
        category=new_quest.category, # type: ignore
        difficulty=new_quest.difficulty, # type: ignore
        duration_minutes=new_quest.duration_minutes,
        estimated_cost_inr=new_quest.estimated_cost_inr,
        cost_label=new_quest.cost_label,
        xp_reward=new_quest.xp_reward,
        status=new_quest.status, # type: ignore
        location=location,
        source=source,
        reflection_prompt=new_quest.reflection_prompt,
        created_at=new_quest.created_at,
        started_at=new_quest.started_at,
        completed_at=new_quest.completed_at
    )

