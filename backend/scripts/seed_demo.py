import json
import math
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import Base, engine, SessionLocal
from app.models import (
    PlayerModel, PreferencesModel, QuestModel, CompletionModel,
    PlayerAchievementModel
)
from app.services.achievements import evaluate_achievements
from app.services.autopilot import calculate_autopilot
from app.schemas import Preferences

def seed_demo_player():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat().replace("+00:00", "Z")

        player_id = f"p_demo_{uuid.uuid4().hex[:8]}"
        display_name = "Aarav Explorer"
        city = "Andheri, Mumbai"

        prefs = Preferences(
            display_name=display_name,
            interests=["food", "art", "outdoors"],
            novelty_frequency="monthly",
            social_style="either",
            comfort_level=4,
            city=city,
            lat=19.1136,
            lng=72.8697,
            free_time_minutes=90,
            max_distance_km=5.0,
            budget_inr=200,
            accessibility_notes=None,
            last_first_time="this_month"
        )

        player = PlayerModel(
            id=player_id,
            display_name=display_name,
            city=city,
            level=1,
            total_xp=0,
            xp_in_level=0,
            xp_for_next_level=1000,
            quests_completed=0,
            achievements_unlocked=0,
            created_at=(now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
        )
        db.add(player)

        prefs_model = PreferencesModel(
            player_id=player_id,
            display_name=display_name,
            interests=json.dumps(prefs.interests),
            novelty_frequency=prefs.novelty_frequency,
            social_style=prefs.social_style,
            comfort_level=prefs.comfort_level,
            city=city,
            lat=prefs.lat,
            lng=prefs.lng,
            free_time_minutes=prefs.free_time_minutes,
            max_distance_km=prefs.max_distance_km,
            budget_inr=prefs.budget_inr,
            accessibility_notes=prefs.accessibility_notes,
            last_first_time=prefs.last_first_time
        )
        db.add(prefs_model)
        db.commit()

        # 4 realistic completed quests in Andheri, Mumbai
        completed_quests_data = [
            {
                "title": "Browse Indie Shelves at Granth Book Store",
                "description": "Walk into Granth on Juhu Tara Road. Find the poetry section and read the first poem of three different books.",
                "why_selected": "Matches your interest in art & learning with a peaceful 45-minute stroll.",
                "category": "explore",
                "difficulty": "easy",
                "xp_reward": 50,
                "duration_minutes": 45,
                "cost": 0,
                "cost_label": "Free",
                "reflection": "Found an incredible translated Marathi poetry anthology. The quiet smell of paper made my whole evening peaceful.",
                "days_ago": 5,
                "location": {
                    "name": "Granth Book Store",
                    "address": "Juhu Tara Rd, near Sea Princess Hotel, Juhu, Mumbai",
                    "lat": 19.1028,
                    "lng": 72.8267,
                    "distance_km": 1.8,
                    "maps_url": "https://www.google.com/maps/place/Granth+Book+Store"
                },
                "source": {
                    "type": "google_maps",
                    "title": "Granth Book Store — Google Maps",
                    "url": "https://www.google.com/maps/place/Granth+Book+Store",
                    "thumbnail_url": None,
                    "fetched_at": (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
                }
            },
            {
                "title": "Sketch the Versova Koliwada Marine Murals",
                "description": "Walk through the fishing village lanes in Versova. Choose one fisherman mural and sketch it in 15 minutes.",
                "why_selected": "Combines your love for art and outdoors within 3 km of your location.",
                "category": "creativity",
                "difficulty": "medium",
                "xp_reward": 100,
                "duration_minutes": 45,
                "cost": 0,
                "cost_label": "Free",
                "reflection": "The fish net details were harder to sketch than I expected, but a local uncle came over and told me the mural's history!",
                "days_ago": 3,
                "location": {
                    "name": "Versova Fishing Village Murals",
                    "address": "Versova Koliwada, Andheri West, Mumbai",
                    "lat": 19.1352,
                    "lng": 72.8143,
                    "distance_km": 2.4,
                    "maps_url": "https://www.google.com/maps/search/?api=1&query=Versova+Koliwada"
                },
                "source": {
                    "type": "google_search",
                    "title": "Versova Koliwada Street Art Walk",
                    "url": "https://mumbaimirror.indiatimes.com/mumbai/culture/versova-koliwada-murals",
                    "thumbnail_url": None,
                    "fetched_at": (now - timedelta(days=3)).isoformat().replace("+00:00", "Z")
                }
            },
            {
                "title": "Order Fresh Bun Maska & Sulemani Chai at an Irani Tapri",
                "description": "Find an old tapri near Yari Road. Order a hot Sulemani chai and fresh bun maska.",
                "why_selected": "Food discovery that costs well under ₹100 and fits a quick break.",
                "category": "explore",
                "difficulty": "easy",
                "xp_reward": 50,
                "duration_minutes": 25,
                "cost": 45,
                "cost_label": "Under ₹100",
                "reflection": "Crispy edges with warm melted butter and spiced black tea. Best ₹45 spent all week.",
                "days_ago": 2,
                "location": {
                    "name": "Yari Road Irani Chai Corner",
                    "address": "Fisheries University Rd, Versova, Andheri West",
                    "lat": 19.1388,
                    "lng": 72.8125,
                    "distance_km": 2.1,
                    "maps_url": "https://www.google.com/maps/search/?api=1&query=Yari+Road+Irani+Chai"
                },
                "source": {
                    "type": "google_maps",
                    "title": "Yari Road Chai Tapris",
                    "url": None,
                    "thumbnail_url": None,
                    "fetched_at": (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
                }
            },
            {
                "title": "Ten-Minute Sound Spotting at Lokhandwala Garden",
                "description": "Sit on a bench under the banyan tree. Close your eyes and identify 8 distinct sounds without looking.",
                "why_selected": "A sensory awareness reset in a quiet green pocket of Andheri.",
                "category": "awareness",
                "difficulty": "easy",
                "xp_reward": 50,
                "duration_minutes": 20,
                "cost": 0,
                "cost_label": "Free",
                "reflection": "Counted parakeets, distant cricket bat clicks, chai glasses clinking, and dry leaves rustling. Instantly lowered my stress.",
                "days_ago": 1,
                "location": {
                    "name": "Lokhandwala Garden",
                    "address": "Lokhandwala Complex, Andheri West, Mumbai",
                    "lat": 19.1415,
                    "lng": 72.8272,
                    "distance_km": 1.5,
                    "maps_url": "https://www.google.com/maps/place/Lokhandwala+Garden"
                },
                "source": {
                    "type": "google_maps",
                    "title": "Lokhandwala Garden — Google Maps",
                    "url": "https://www.google.com/maps/place/Lokhandwala+Garden",
                    "thumbnail_url": None,
                    "fetched_at": (now - timedelta(days=1)).isoformat().replace("+00:00", "Z")
                }
            }
        ]

        total_xp = 0
        cat_counts = {"explore": 0, "social": 0, "creativity": 0, "courage": 0, "awareness": 0}

        for q_data in completed_quests_data:
            q_id = f"q_seed_{uuid.uuid4().hex[:8]}"
            c_time = (now - timedelta(days=q_data["days_ago"])).isoformat().replace("+00:00", "Z")
            s_time = (now - timedelta(days=q_data["days_ago"], minutes=q_data["duration_minutes"])).isoformat().replace("+00:00", "Z")

            quest_model = QuestModel(
                id=q_id,
                player_id=player_id,
                title=q_data["title"],
                description=q_data["description"],
                why_selected=q_data["why_selected"],
                category=q_data["category"],
                difficulty=q_data["difficulty"],
                duration_minutes=q_data["duration_minutes"],
                estimated_cost_inr=q_data["cost"],
                cost_label=q_data["cost_label"],
                xp_reward=q_data["xp_reward"],
                status="completed",
                location=json.dumps(q_data["location"]),
                source=json.dumps(q_data["source"]),
                reflection_prompt="What stood out most about this experience?",
                created_at=s_time,
                started_at=s_time,
                completed_at=c_time
            )
            db.add(quest_model)

            completion = CompletionModel(
                id=f"c_seed_{uuid.uuid4().hex[:8]}",
                quest_id=q_id,
                player_id=player_id,
                reflection=q_data["reflection"],
                photo_path=None,
                xp_awarded=q_data["xp_reward"],
                completed_at=c_time
            )
            db.add(completion)

            total_xp += q_data["xp_reward"]
            cat_counts[q_data["category"]] += 1

        player.total_xp = total_xp
        player.level = math.floor(total_xp / 1000) + 1
        player.xp_in_level = total_xp % 1000
        player.quests_completed = len(completed_quests_data)

        # Unlock First Step achievement
        all_ach, newly_unlocked = evaluate_achievements(
            quests_completed=player.quests_completed,
            category_counts=cat_counts,
            currently_unlocked_ids=set(),
            now_iso=now_iso
        )

        for na in newly_unlocked:
            db.add(PlayerAchievementModel(
                player_id=player_id,
                achievement_id=na.id,
                unlocked_at=now_iso
            ))
        player.achievements_unlocked = len(newly_unlocked)

        # Create one active/suggested quest for today
        today_quest = QuestModel(
            id=f"q_seed_today_{uuid.uuid4().hex[:8]}",
            player_id=player_id,
            title="Discover Second-Hand Vintage Books near Andheri Station",
            description="Explore the quiet book stalls under the railway canopy. Pick up one book older than 20 years and read the dedication page.",
            why_selected="An offbeat explore quest matching your interests in learning and culture.",
            category="explore",
            difficulty="easy",
            duration_minutes=35,
            estimated_cost_inr=50,
            cost_label="Under ₹100",
            xp_reward=50,
            status="suggested",
            location=json.dumps({
                "name": "Station Road Old Book Stalls",
                "address": "Opposite Railway Platform 1, Andheri West",
                "lat": 19.1198,
                "lng": 72.8465,
                "distance_km": 1.2,
                "maps_url": "https://www.google.com/maps/search/?api=1&query=Andheri+Station+Books"
            }),
            source=json.dumps({
                "type": "google_search",
                "title": "Andheri Station Old Bookstalls",
                "url": None,
                "thumbnail_url": None,
                "fetched_at": now_iso
            }),
            reflection_prompt="What was the oldest date or interesting inscription you found in a book?",
            created_at=now_iso,
            started_at=None,
            completed_at=None
        )
        db.add(today_quest)

        db.commit()

        # Compute Autopilot
        ap = calculate_autopilot(
            prefs,
            [(q_data["days_ago"], q_data["category"]) for q_data in completed_quests_data]
        )

        print("=" * 60)
        print("DEMO PLAYER SEEDED SUCCESSFULLY!")
        print(f"PLAYER ID: {player_id}")
        print(f"DISPLAY NAME: {player.display_name}")
        print(f"CITY: {player.city}")
        print(f"TOTAL XP: {player.total_xp} (Level {player.level})")
        print(f"QUESTS COMPLETED: {player.quests_completed}")
        print(f"ACHIEVEMENTS UNLOCKED: {player.achievements_unlocked}")
        print(f"AUTOPILOT SCORE: {ap.score} ('{ap.label}')")
        print(f"TODAY'S QUEST: {today_quest.title}")
        print("=" * 60)

        return player_id

    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_player()

