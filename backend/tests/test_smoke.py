import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_player_lifecycle_smoke():
    # 1. Health check
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "ok"
    assert "mock_mode" in health_data

    # 2. Create player (Onboarding)
    player_payload = {
        "display_name": "Smoke Explorer",
        "interests": ["food", "art", "outdoors"],
        "novelty_frequency": "weekly",
        "social_style": "solo",
        "comfort_level": 4,
        "city": "Andheri, Mumbai",
        "lat": 19.1136,
        "lng": 72.8697,
        "free_time_minutes": 60,
        "max_distance_km": 5.0,
        "budget_inr": 250,
        "accessibility_notes": None,
        "last_first_time": "this_week"
    }

    create_resp = client.post("/api/v1/players", json=player_payload)
    assert create_resp.status_code == 201, create_resp.text
    create_data = create_resp.json()
    assert "player" in create_data
    assert "autopilot" in create_data

    player = create_data["player"]
    player_id = player["id"]
    assert player["display_name"] == "Smoke Explorer"
    assert player["level"] == 1
    assert player["total_xp"] == 0
    assert player["xp_for_next_level"] == 1000

    headers = {"X-Player-Id": player_id}

    # 3. GET /home (lazily generates today's quest)
    home_resp = client.get("/api/v1/home", headers=headers)
    assert home_resp.status_code == 200, home_resp.text
    home_data = home_resp.json()
    assert home_data["player"]["id"] == player_id
    assert home_data["todays_quest"] is not None

    quest = home_data["todays_quest"]
    quest_id = quest["id"]
    assert quest["status"] in ["suggested", "active"]
    assert quest["xp_reward"] in [50, 100, 150]

    # 4. Start Quest
    start_resp = client.post(f"/api/v1/quests/{quest_id}/start", headers=headers)
    assert start_resp.status_code == 200, start_resp.text
    start_data = start_resp.json()
    assert start_data["quest"]["status"] == "active"
    assert start_data["quest"]["started_at"] is not None

    # 5. Complete Quest
    complete_payload = {
        "reflection": "Stepped off the daily commute and found a hidden lane. Absolutely loved it!",
        "photo_data_url": None
    }
    complete_resp = client.post(f"/api/v1/quests/{quest_id}/complete", json=complete_payload, headers=headers)
    assert complete_resp.status_code == 200, complete_resp.text
    comp_data = complete_resp.json()

    assert comp_data["quest"]["status"] == "completed"
    assert comp_data["xp_awarded"] > 0
    assert comp_data["player"]["total_xp"] == comp_data["xp_awarded"]
    assert comp_data["player"]["quests_completed"] == 1
    assert comp_data["message"] == "You broke your routine today."

    # Check achievements unlocked
    unlocked_names = [a["id"] for a in comp_data["achievements_unlocked"]]
    assert "first_step" in unlocked_names

    # 6. Journey verification
    journey_resp = client.get("/api/v1/journey", headers=headers)
    assert journey_resp.status_code == 200, journey_resp.text
    journey_data = journey_resp.json()
    assert journey_data["player"]["quests_completed"] == 1
    assert len(journey_data["journal"]) == 1
    assert journey_data["journal"][0]["quest_id"] == quest_id

    # Check achievements list
    achievements = journey_data["achievements"]
    assert len(achievements) == 8
    first_step_ach = next(a for a in achievements if a["id"] == "first_step")
    assert first_step_ach["unlocked"] is True

    # 7. Weekly Recap
    recap_resp = client.get("/api/v1/journey/weekly-recap", headers=headers)
    assert recap_resp.status_code == 200, recap_resp.text
    recap_data = recap_resp.json()
    assert recap_data["stats"]["quests_completed"] == 1
    assert recap_data["generated_by"] in ["llm", "template"]
    assert len(recap_data["summary"]) > 10

    # 8. Explore Experiences
    exp_resp = client.get("/api/v1/explore/experiences", headers=headers)
    assert exp_resp.status_code == 200, exp_resp.text
    exp_data = exp_resp.json()
    assert len(exp_data["experiences"]) > 0

    # 9. Quest from Experience
    exp_id = exp_data["experiences"][0]["id"]
    from_exp_resp = client.post(f"/api/v1/explore/experiences/{exp_id}/quest", headers=headers)
    assert from_exp_resp.status_code == 200, from_exp_resp.text
    assert from_exp_resp.json()["quest"]["source"] is not None

def test_missing_player_header():
    resp = client.get("/api/v1/home")
    assert resp.status_code == 401
    err = resp.json()["error"]
    assert err["code"] == "player_required"

def test_reflection_length_validation():
    # Create player
    p_resp = client.post("/api/v1/players", json={
        "display_name": "Test Valid",
        "interests": ["food"],
        "novelty_frequency": "daily",
        "social_style": "solo",
        "comfort_level": 3,
        "city": "Mumbai",
        "lat": 19.1136,
        "lng": 72.8697,
        "free_time_minutes": 45,
        "max_distance_km": 5.0,
        "budget_inr": 100,
        "accessibility_notes": None,
        "last_first_time": "this_week"
    })
    player_id = p_resp.json()["player"]["id"]
    headers = {"X-Player-Id": player_id}

    home_resp = client.get("/api/v1/home", headers=headers)
    q_id = home_resp.json()["todays_quest"]["id"]

    # Try completing with > 500 chars
    long_text = "x" * 501
    bad_resp = client.post(f"/api/v1/quests/{q_id}/complete", json={"reflection": long_text}, headers=headers)
    assert bad_resp.status_code == 422
    assert bad_resp.json()["error"]["code"] == "validation_error"

