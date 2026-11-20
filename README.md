# NPC Backend 🎮🗺️

An AI-powered real-world adventure app that turns everyday life into a game. Players receive personalised **Side Quests** (explore unfamiliar streets, try new flavours, observe their city mindfully), earn XP, level up, unlock achievements, and build a reflective journal of their journey.

Built for the **Best Use of SerpApi** track, with SerpApi acting as the core discovery engine powering authentic local places, events, and activities.

---

## Tech Stack
- **Framework:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn
- **Database:** SQLite via SQLAlchemy 2.0 (stored at `./npc.db`, auto-created on startup)
- **External Discovery:** SerpApi (Google Maps, Google Events, Google Search) via `httpx`
- **LLM Integration:** Google Gemini via `google-genai` SDK (model configured by `GEMINI_MODEL`), isolated cleanly in `app/services/llm.py`
- **Frontend Sync:** Auto-generated OpenAPI specification written to `openapi.json` on startup

---

## Getting Started

### 1. Environment Setup
Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configuration & API Keys
Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Default `.env` values:
```env
SERPAPI_API_KEY=dummy_serpapi_key_replace_me
GEMINI_API_KEY=dummy_gemini_key_replace_me
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///./npc.db
PUBLIC_BASE_URL=http://localhost:8000
SERP_CACHE_TTL_HOURS=12
```

#### Mock Mode vs Live Mode
- **Zero-config Demo / Mock Mode:** If an API key is missing or starts with `dummy`, that service automatically runs in **Mock Mode** (no external network calls, zero crash risk).
  - Mock mode uses 17 curated, realistic Andheri / Mumbai fixtures matching the exact SerpApi schema (`fixtures/serp_maps.json`, `serp_events.json`, `serp_search.json`).
  - Mock LLM generates playful, structured quests from candidate experiences via a template engine.
- **Live Mode:** Replace `SERPAPI_API_KEY` with your SerpApi key and `GEMINI_API_KEY` with your Google Gemini key. The backend will immediately start making live calls with zero code changes.
- Check `GET /api/v1/health` at any time to verify live vs mock status.

### 3. Run the Backend
From the `backend` directory:
```bash
uvicorn app.main:app --reload --port 8000
```
Or from the project root:
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Base API URL: `http://localhost:8000/api/v1`

### 4. Seed Demo Data
To immediately explore the app with an active player who has 4 completed quests, unlocked achievements, and a lively Autopilot meter:

```bash
python backend/scripts/seed_demo.py
```
This prints the generated `PLAYER_ID` (e.g. `p_demo_1e186efd`).

### 5. Running Smoke Tests
Run the automated pytest smoke test (validates: create player -> home -> start quest -> complete quest -> journey):

```bash
pytest backend/tests/test_smoke.py -v
```

---

## Frontend Contract & `openapi.json`
Every time the server starts up or tests run, an updated `openapi.json` is exported to the repository root. You can compare this file against frontend TypeScript types to verify that the frontend and backend remain 100% in sync without drift.

---

## cURL Examples for Every Endpoint

Set helper environment variables:
```bash
API_BASE="http://localhost:8000/api/v1"
PLAYER_ID="p_demo_1e186efd" # replace with your player id
```

### 1. Health Check (No Auth Required)
```bash
curl -X GET "http://localhost:8000/api/v1/health"
```
*Response:*
```json
{
  "status": "ok",
  "mock_mode": true,
  "serpapi_live": false,
  "llm_live": false
}
```

---

### 2. Create Player (Onboarding)
```bash
curl -X POST "$API_BASE/players" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Rohan",
    "interests": ["food", "art", "outdoors"],
    "novelty_frequency": "weekly",
    "social_style": "solo",
    "comfort_level": 4,
    "city": "Andheri, Mumbai",
    "lat": 19.1136,
    "lng": 72.8697,
    "free_time_minutes": 60,
    "max_distance_km": 5.0,
    "budget_inr": 200,
    "accessibility_notes": null,
    "last_first_time": "this_week"
  }'
```

---

### 3. Get Player Profile (`GET /players/me`)
```bash
curl -X GET "$API_BASE/players/me" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 4. Update Preferences (`PATCH /players/me`)
```bash
curl -X PATCH "$API_BASE/players/me" \
  -H "X-Player-Id: $PLAYER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "free_time_minutes": 90,
    "budget_inr": 500
  }'
```

---

### 5. Home Dashboard (`GET /home`)
*Lazily generates today's quest if none exists yet today.*
```bash
curl -X GET "$API_BASE/home" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 6. Generate a New Quest (`POST /quests/generate`)
*Optionally specify a category or `replace_today: true`.*
```bash
curl -X POST "$API_BASE/quests/generate" \
  -H "X-Player-Id: $PLAYER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "creativity",
    "replace_today": true
  }'
```

---

### 7. List Quests (`GET /quests`)
```bash
curl -X GET "$API_BASE/quests?category=explore&status=suggested&limit=10" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 8. Get Quest by ID (`GET /quests/{quest_id}`)
```bash
curl -X GET "$API_BASE/quests/q_seed_today_1" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 9. Start a Quest (`POST /quests/{quest_id}/start`)
```bash
curl -X POST "$API_BASE/quests/q_seed_today_1/start" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 10. Dismiss a Quest (`POST /quests/{quest_id}/dismiss`)
```bash
curl -X POST "$API_BASE/quests/q_seed_today_1/dismiss" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 11. Complete a Quest (`POST /quests/{quest_id}/complete`)
```bash
curl -X POST "$API_BASE/quests/q_seed_today_1/complete" \
  -H "X-Player-Id: $PLAYER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "reflection": "Found a 1982 illustrated copy of Malgudi Days. The smell of the paper made my day.",
    "photo_data_url": null
  }'
```

---

### 12. Browse Real-World Discoveries (`GET /explore/experiences`)
```bash
curl -X GET "$API_BASE/explore/experiences?tag=bookstore&limit=5" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 13. Get Experience by ID (`GET /explore/experiences/{experience_id}`)
```bash
curl -X GET "$API_BASE/explore/experiences/exp_maps_ChIJN1t_tDeu5zsRgranth001" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 14. Turn Discovery into Personalised Quest (`POST /explore/experiences/{id}/quest`)
```bash
curl -X POST "$API_BASE/explore/experiences/exp_maps_ChIJN1t_tDeu5zsRgranth001/quest" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 15. Player Journey (`GET /journey`)
*Returns full journal, all locked/unlocked achievements, and category statistics.*
```bash
curl -X GET "$API_BASE/journey" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

### 16. Weekly Recap (`GET /journey/weekly-recap`)
```bash
curl -X GET "$API_BASE/journey/weekly-recap" \
  -H "X-Player-Id: $PLAYER_ID"
```

---

## Core Mechanics

### Autopilot Meter
A playful, deterministic score from `0` to `100` where **higher = more routine/repetition**:
- Base: 50
- `novelty_frequency`: rarely (+25), monthly (+10), weekly (-10), daily (-25)
- `last_first_time`: this_week (-15), this_month (-5), this_year (+10), cant_remember (+20)
- `comfort_level`: -4 per point above 3, +4 per point below 3
- Completions (last 14 days): -4 per completed quest (cap -30), -3 per distinct category (cap -15)
- Labels: `Wide awake` (0-24), `Mostly exploring` (25-49), `Needs a little adventure` (50-74), `Deep autopilot` (75-100)

### Level & XP Math
- Easy Quest: 50 XP
- Medium Quest: 100 XP
- Hard Quest: 150 XP
- `level = floor(total_xp / 1000) + 1`
- `xp_in_level = total_xp % 1000`
- `xp_for_next_level = 1000` (always 1000)

### Achievements
- `first_step`: Complete your first side quest (`footprint`)
- `explorer`: Complete 3 explore quests (`compass`)
- `social_spark`: Complete 2 social quests (`spark`)
- `maker`: Complete 2 creativity quests (`brush`)
- `brave_heart`: Complete 1 courage quest (`heart`)
- `present`: Complete 2 awareness quests (`eye`)
- `variety_pack`: Complete a quest in every category (`dice`)
- `local_legend`: Complete 10 quests (`crown`)

