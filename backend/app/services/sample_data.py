"""Builds a demo player with about two months of completed quests, so the analytics
tab has something rich to show without anyone playing for weeks first."""
import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import CompletionModel, PlayerAchievementModel, PlayerModel, PreferencesModel, QuestModel
from app.schemas import QuestLocation, QuestSource
from app.services.achievements import evaluate_achievements
from app.services.quest_engine import XP_MAP
from app.services.serp import haversine_km

HOME = ("Andheri, Mumbai", 19.1197, 72.8464)
IST = timezone(timedelta(hours=5, minutes=30))

# name, address, lat, lng
PLACES: Dict[str, Tuple[str, str, float, float]] = {
    "granth": ("Granth Book Store", "Juhu Tara Rd, Juhu", 19.1075, 72.8263),
    "lokhandwala": ("Lokhandwala Garden", "Lokhandwala Complex, Andheri West", 19.1418, 72.8256),
    "versova": ("Versova Beach", "Versova, Andheri West", 19.1340, 72.8110),
    "prithvi": ("Prithvi Theatre", "Juhu Church Rd, Juhu", 19.1060, 72.8270),
    "carter": ("Carter Road Promenade", "Carter Rd, Bandra West", 19.0700, 72.8220),
    "sgnp": ("Kanheri Caves, Sanjay Gandhi National Park", "Borivali East", 19.2060, 72.9060),
    "kalaghoda": ("Kala Ghoda Art Precinct", "Fort, Mumbai", 18.9281, 72.8317),
    "kumbharwada": ("Kumbharwada Potters' Lane", "Dharavi, Mumbai", 19.0380, 72.8540),
    "bandrafort": ("Bandra Fort", "Bandstand, Bandra West", 19.0418, 72.8188),
    "juhu": ("Juhu Beach", "Juhu, Mumbai", 19.0988, 72.8267),
    "aarey": ("Aarey Colony", "Goregaon East", 19.1550, 72.8740),
    "hajiali": ("Haji Ali Dargah", "Haji Ali, Mumbai", 18.9827, 72.8089),
}

# title, category, difficulty, minutes, cost, place key, reflection
TEMPLATES: List[Tuple[str, str, str, int, Optional[int], Optional[str], str]] = [
    ("Browse a bookstore you've never entered", "explore", "easy", 45, 0, "granth", "Picked a Marathi poetry book by its cover. Read the first page twice."),
    ("Ten minutes of sound-spotting", "awareness", "easy", 15, 0, "lokhandwala", "Counted 23 sounds. A koel won."),
    ("Sunset walk on the beach, phone in your bag", "awareness", "medium", 40, 0, "versova", "Didn't miss my phone once. Saw fishing boats come in."),
    ("Watch a play you know nothing about", "social", "medium", 120, 500, "prithvi", "Talked to the person next to me at the interval. We both cried a bit."),
    ("Ask a stranger for their favourite street food", "social", "medium", 20, 60, None, "A rickshaw driver sent me to a misal pav stall I'd walked past for years."),
    ("Sketch the sea wall in 10 minutes", "creativity", "easy", 30, 0, "carter", "Terrible drawing. Noticed the wall has handprints in it."),
    ("Hike to the Kanheri caves", "courage", "hard", 180, 120, "sgnp", "Legs hurt. Worth it. There were monkeys and no notifications."),
    ("Gallery-hop through Kala Ghoda", "explore", "medium", 90, 0, "kalaghoda", "Three galleries, one weird installation I keep thinking about."),
    ("Try a potter's wheel for the first time", "creativity", "hard", 120, 800, "kumbharwada", "Made a wonky bowl. The potter laughed kindly and fixed it."),
    ("Eat lunch somewhere with no reviews", "courage", "medium", 45, 150, None, "Hand-painted sign, best dal I've had this year."),
    ("Catch golden hour at an old fort", "explore", "easy", 50, 0, "bandrafort", "Sat on the ruins and watched the sea link light up."),
    ("Join a beach clean-up", "social", "hard", 120, 0, "juhu", "Filled two sacks. Got invited to the next one."),
    ("Write a four-line poem on a park bench", "creativity", "easy", 20, 0, "lokhandwala", "It rhymed by accident."),
    ("Cycle through the forest roads at dawn", "courage", "hard", 90, 200, "aarey", "Woke up at 5:30 on purpose. Saw a peacock."),
    ("Take a different train home", "courage", "easy", 40, 30, None, "Got off one stop early and found a lane full of old bungalows."),
    ("Walk out to the dargah at low tide", "awareness", "medium", 60, 0, "hajiali", "The walkway felt like walking on the sea."),
]

# (days ago, local hour, template index). Denser recently, so the trend climbs.
SCHEDULE: List[Tuple[int, int, int]] = [
    (55, 18, 0), (51, 7, 15), (47, 19, 4), (44, 17, 5), (40, 10, 7), (37, 19, 2),
    (34, 18, 3), (31, 8, 13), (29, 16, 9), (26, 20, 10), (23, 11, 8), (21, 7, 1),
    (19, 18, 14), (16, 6, 6), (14, 17, 12), (12, 9, 11), (10, 19, 2), (8, 13, 0),
    (6, 18, 15), (4, 7, 13), (2, 19, 10), (1, 12, 4),
]
DISMISSED = [2, 6, 11]  # template indices skipped once


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _location(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    name, address, lat, lng = PLACES[key]
    d = round(haversine_km(HOME[1], HOME[2], lat, lng), 1)
    return QuestLocation(
        name=name, address=address, lat=lat, lng=lng, distance_km=d,
        maps_url=f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}",
    ).model_dump_json()


def _quest(player_id: str, t_idx: int, status: str, created: datetime) -> QuestModel:
    title, cat, diff, minutes, cost, place, _ = TEMPLATES[t_idx]
    src = QuestSource(type="google_maps", title=PLACES[place][0], url=None, fetched_at=_iso(created)) if place else None
    return QuestModel(
        id=f"q_{uuid.uuid4().hex[:10]}", player_id=player_id, title=title,
        description="A sample quest from the demo save file.", why_selected="Part of the sample player's history.",
        category=cat, difficulty=diff, duration_minutes=minutes, estimated_cost_inr=cost,
        cost_label="Free" if cost == 0 else (f"About ₹{cost}" if cost else "Cost unknown"),
        xp_reward=XP_MAP[diff], status=status, location=_location(place),
        source=src.model_dump_json() if src else None,
        reflection_prompt="What surprised you?", created_at=_iso(created),
    )


def create_sample_player(db: Session) -> PlayerModel:
    now = datetime.now(IST)
    pid = f"p_{uuid.uuid4().hex[:10]}"
    city, lat, lng = HOME
    player = PlayerModel(
        id=pid, display_name="Riya (sample)", city=city, level=1, total_xp=0, xp_in_level=0,
        xp_for_next_level=1000, quests_completed=0, achievements_unlocked=0,
        created_at=_iso(now - timedelta(days=58)),
    )
    db.add(player)
    db.add(PreferencesModel(
        player_id=pid, display_name=player.display_name, interests=json.dumps(["food", "art", "outdoors", "culture"]),
        novelty_frequency="rarely", social_style="either", comfort_level=2, city=city, lat=lat, lng=lng,
        free_time_minutes=90, max_distance_km=30, budget_inr=800, accessibility_notes=None,
        last_first_time="this_year",
    ))

    counts = {c: 0 for c in ["explore", "social", "creativity", "courage", "awareness"]}
    unlocked: set = set()
    for days_ago, hour, t_idx in SCHEDULE:
        done = (now - timedelta(days=days_ago)).replace(hour=hour, minute=(t_idx * 7) % 60, second=0, microsecond=0)
        q = _quest(pid, t_idx, "completed", done - timedelta(hours=3))
        q.started_at = _iso(done - timedelta(minutes=TEMPLATES[t_idx][3]))
        q.completed_at = _iso(done)
        db.add(q)
        db.add(CompletionModel(
            id=f"c_{uuid.uuid4().hex[:10]}", quest_id=q.id, player_id=pid, reflection=TEMPLATES[t_idx][6],
            photo_path=None, xp_awarded=q.xp_reward, completed_at=q.completed_at,
        ))
        player.total_xp += q.xp_reward
        player.quests_completed += 1
        counts[q.category] += 1
        _, new = evaluate_achievements(player.quests_completed, counts, unlocked, q.completed_at)
        for a in new:
            unlocked.add(a.id)
            db.add(PlayerAchievementModel(player_id=pid, achievement_id=a.id, unlocked_at=q.completed_at))

    for i, t_idx in enumerate(DISMISSED):
        db.add(_quest(pid, t_idx, "dismissed", now - timedelta(days=45 - i * 15)))
    # No open quest: Home generates a real one for today on first load.

    player.level = math.floor(player.total_xp / 1000) + 1
    player.xp_in_level = player.total_xp % 1000
    player.achievements_unlocked = len(unlocked)
    db.commit()
    db.refresh(player)
    return player
