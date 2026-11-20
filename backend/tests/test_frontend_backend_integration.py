import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_frontend_backend_full_contract_wiring():
    """
    Simulates every method of NpcClient in frontend/src/lib/api.ts
    to verify complete end-to-end integration between frontend and backend.
    """
    # 1. health()
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["status"] == "ok"
    assert health["serpapi_live"] is True
    assert health["llm_live"] is True
    assert health["mock_mode"] is False

    # 2. createPlayer(p)
    player_data = {
        "display_name": "EndToEnd Player",
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
    create_resp = client.post("/api/v1/players", json=player_data)
    assert create_resp.status_code == 201
    create_data = create_resp.json()
    player_id = create_data["player"]["id"]
    assert player_id.startswith("p_")
    assert create_data["autopilot"]["score"] >= 0

    headers = {"X-Player-Id": player_id}

    # 3. getMe()
    me_resp = client.get("/api/v1/players/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["player"]["id"] == player_id
    assert me_data["preferences"]["city"] == "Andheri, Mumbai"

    # 4. updateMe(p)
    update_resp = client.patch("/api/v1/players/me", json={"budget_inr": 400}, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["preferences"]["budget_inr"] == 400

    # 5. home()
    home_resp = client.get("/api/v1/home", headers=headers)
    assert home_resp.status_code == 200
    home_data = home_resp.json()
    assert "todays_quest" in home_data
    todays_q = home_data["todays_quest"]
    assert todays_q is not None
    today_q_id = todays_q["id"]

    # 6. generateQuest({ category, replace_today })
    gen_resp = client.post("/api/v1/quests/generate", json={"category": "creativity", "replace_today": False}, headers=headers)
    assert gen_resp.status_code == 200
    gen_quest = gen_resp.json()["quest"]
    assert gen_quest["category"] == "creativity"
    gen_q_id = gen_quest["id"]

    # 7. listQuests(q)
    list_q_resp = client.get("/api/v1/quests?limit=10", headers=headers)
    assert list_q_resp.status_code == 200
    quests_list = list_q_resp.json()["quests"]
    assert len(quests_list) >= 2

    # 8. getQuest(id)
    get_q_resp = client.get(f"/api/v1/quests/{gen_q_id}", headers=headers)
    assert get_q_resp.status_code == 200
    assert get_q_resp.json()["quest"]["id"] == gen_q_id

    # 9. startQuest(id)
    start_resp = client.post(f"/api/v1/quests/{gen_q_id}/start", headers=headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["quest"]["status"] == "active"
    assert start_resp.json()["quest"]["started_at"] is not None

    # 10. completeQuest(id, body)
    complete_resp = client.post(
        f"/api/v1/quests/{gen_q_id}/complete",
        json={"reflection": "A stunning creative detour in the afternoon."},
        headers=headers
    )
    assert complete_resp.status_code == 200
    comp_data = complete_resp.json()
    assert comp_data["quest"]["status"] == "completed"
    assert comp_data["xp_awarded"] in [50, 100, 150]
    assert comp_data["player"]["quests_completed"] == 1
    assert "first_step" in [a["id"] for a in comp_data["achievements_unlocked"]]

    # 11. dismissQuest(id)
    dismiss_resp = client.post(f"/api/v1/quests/{today_q_id}/dismiss", headers=headers)
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["quest"]["status"] == "dismissed"

    # 12. listExperiences(q)
    exp_list_resp = client.get("/api/v1/explore/experiences?limit=5", headers=headers)
    assert exp_list_resp.status_code == 200
    exps = exp_list_resp.json()["experiences"]
    assert len(exps) > 0
    first_exp = exps[0]
    exp_id = first_exp["id"]

    # 13. getExperience(id)
    get_exp_resp = client.get(f"/api/v1/explore/experiences/{exp_id}", headers=headers)
    assert get_exp_resp.status_code == 200
    assert get_exp_resp.json()["experience"]["id"] == exp_id

    # 14. questFromExperience(id)
    from_exp_resp = client.post(f"/api/v1/explore/experiences/{exp_id}/quest", headers=headers)
    assert from_exp_resp.status_code == 200
    from_exp_q = from_exp_resp.json()["quest"]
    assert from_exp_q["status"] == "suggested"
    assert from_exp_q["source"]["title"] == first_exp["title"]

    # 15. journey()
    journey_resp = client.get("/api/v1/journey", headers=headers)
    assert journey_resp.status_code == 200
    j_data = journey_resp.json()
    assert j_data["player"]["quests_completed"] == 1
    assert len(j_data["journal"]) == 1
    assert j_data["category_counts"]["creativity"] == 1
    assert len(j_data["achievements"]) == 8

    # 16. weeklyRecap()
    recap_resp = client.get("/api/v1/journey/weekly-recap", headers=headers)
    assert recap_resp.status_code == 200
    recap = recap_resp.json()
    assert recap["stats"]["quests_completed"] == 1
    assert recap["generated_by"] in ["llm", "template"]
    assert len(recap["summary"]) > 10

