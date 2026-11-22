import base64
import json
import logging
import math
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import settings, BASE_DIR
from app.database import Base, engine, get_db
from app.models import (
    PlayerModel, PreferencesModel, QuestModel, ExperienceModel,
    CompletionModel, PlayerAchievementModel, SerpCacheModel,
    RewardModel, RewardRedemptionModel
)
from app.schemas import (
    Player, Preferences, PreferencesUpdate, Autopilot, Quest, Experience,
    ActivityItem, Achievement, JournalEntry, HealthResponse,
    CreatePlayerResponse, PlayerMeResponse, HomeResponse,
    GenerateQuestRequest, QuestResponse, QuestsListResponse,
    CompleteQuestRequest, CompleteQuestResponse, ExperiencesListResponse,
    ExperienceResponse, JourneyResponse, WeeklyRecapResponse, WeeklyRecapStats,
    Category, Difficulty, QuestStatus, QuestLocation, QuestSource,
    Reward, RewardRedemption, RewardsListResponse, RedeemRewardResponse
)
from app.services.autopilot import calculate_autopilot
from app.services.achievements import evaluate_achievements, ALL_ACHIEVEMENTS
from app.services.serp import (
    fetch_serp_cached, get_experiences_for_category, load_fixture,
    parse_maps_results, parse_events_results, parse_search_results,
    geocode_city, haversine_km,
    DEFAULT_MUMBAI_LAT, DEFAULT_MUMBAI_LNG
)
from app.services.quest_engine import generate_quest, XP_MAP
from app.services.llm import generate_weekly_recap_text

logger = logging.getLogger("npc")

# Custom Application Exception for contract compliance
class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def init_app_state(app_instance: Optional[FastAPI] = None):
    # 1. Create tables
    Base.metadata.create_all(bind=engine)

    # 2. Pre-seed experiences from the Andheri fixtures if the table is empty.
    #    Mock mode only: in live mode Explore fills from real searches for the player's area.
    db = next(get_db())
    try:
        count = db.query(ExperienceModel).count()
        if count == 0 and not settings.is_serpapi_live:
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            maps_data = load_fixture("serp_maps.json")
            events_data = load_fixture("serp_events.json")
            search_data = load_fixture("serp_search.json")

            exps = []
            if maps_data:
                exps.extend(parse_maps_results(maps_data, DEFAULT_MUMBAI_LAT, DEFAULT_MUMBAI_LNG, now_iso))
            if events_data:
                exps.extend(parse_events_results(events_data, DEFAULT_MUMBAI_LAT, DEFAULT_MUMBAI_LNG, now_iso))
            if search_data:
                exps.extend(parse_search_results(search_data, DEFAULT_MUMBAI_LAT, DEFAULT_MUMBAI_LNG, now_iso))

            for e in exps:
                db.add(ExperienceModel(
                    id=e.id,
                    kind=e.kind,
                    title=e.title,
                    subtitle=e.subtitle,
                    tag=e.tag,
                    thumbnail_url=e.thumbnail_url,
                    address=e.address,
                    lat=e.lat,
                    lng=e.lng,
                    distance_km=e.distance_km,
                    price_label=e.price_label,
                    hours_label=e.hours_label,
                    event_time_label=e.event_time_label,
                    rating=e.rating,
                    link_url=e.link_url,
                    source=e.source,
                    why_worth_it=e.why_worth_it,
                    fetched_at=e.fetched_at
                ))
            db.commit()

        # Seed default rewards if rewards table is empty
        reward_count = db.query(RewardModel).count()
        if reward_count == 0:
            default_rewards = [
                {
                    "id": "rew_raju_20",
                    "title": "₹20 OFF at Raju Idli Stall",
                    "description": "Crispy medu vada, piping hot idlis & filter coffee right outside Andheri Station.",
                    "brand": "Raju Idli Stall",
                    "category": "food",
                    "discount_amount_inr": 20,
                    "cost_xp": 50,
                    "location": "Platform 1 Exit, Andheri Station West",
                    "terms": "Valid on any billing above ₹40. Flash voucher code at the counter.",
                    "icon_key": "star",
                    "is_active": 1
                },
                {
                    "id": "rew_andheri_idli_50",
                    "title": "₹50 OFF on Any Idli / Dosa Corner",
                    "description": "Redeem ₹50 discount on any South Indian breakfast stall or eatery across Andheri Station market.",
                    "brand": "Andheri Station Food Network",
                    "category": "food",
                    "discount_amount_inr": 50,
                    "cost_xp": 100,
                    "location": "Station Road Market, Andheri West",
                    "terms": "Valid on bill of ₹100 or more at participating street stalls & counters.",
                    "icon_key": "heart",
                    "is_active": 1
                },
                {
                    "id": "rew_macd_75",
                    "title": "₹75 OFF or Free McFlurry at McDonald's",
                    "description": "Flat ₹75 off on your favourite burgers and meals, or get a free McFlurry with any combo.",
                    "brand": "McDonald's",
                    "category": "food",
                    "discount_amount_inr": 75,
                    "cost_xp": 150,
                    "location": "All McDonald's Outlets & McDelivery",
                    "terms": "Enter code at McDonald's Self-Ordering Kiosk or McDelivery app.",
                    "icon_key": "sword",
                    "is_active": 1
                },
                {
                    "id": "rew_starbucks_100",
                    "title": "₹100 OFF Starbucks Beverage Voucher",
                    "description": "Treat yourself to handcrafted Frappuccinos, artisanal cold brews, or warm bakery bites.",
                    "brand": "Starbucks Coffee",
                    "category": "lifestyle",
                    "discount_amount_inr": 100,
                    "cost_xp": 200,
                    "location": "All Starbucks Outlets / In-app",
                    "terms": "Show barcode or enter code on Starbucks India app at payment.",
                    "icon_key": "crown",
                    "is_active": 1
                },
                {
                    "id": "rew_amazon_50",
                    "title": "₹50 Amazon Pay Gift Voucher",
                    "description": "Instant ₹50 voucher balance for shopping, food orders, or recharge on Amazon.",
                    "brand": "Amazon",
                    "category": "shopping",
                    "discount_amount_inr": 50,
                    "cost_xp": 100,
                    "location": "Online / Amazon India App",
                    "terms": "Redeem voucher code instantly in Amazon Pay -> Add Gift Card.",
                    "icon_key": "gift",
                    "is_active": 1
                },
                {
                    "id": "rew_amazon_100",
                    "title": "₹100 Amazon Pay Gift Voucher",
                    "description": "Instant ₹100 voucher balance for shopping, movies, or bill payments on Amazon.",
                    "brand": "Amazon",
                    "category": "shopping",
                    "discount_amount_inr": 100,
                    "cost_xp": 200,
                    "location": "Online / Amazon India App",
                    "terms": "Redeem voucher code instantly in Amazon Pay -> Add Gift Card.",
                    "icon_key": "gift",
                    "is_active": 1
                }
            ]
            for r in default_rewards:
                db.add(RewardModel(**r))
            db.commit()
    finally:
        db.close()

    # 3. Export openapi.json to repo root and base dir
    if app_instance is not None:
        try:
            openapi_schema = app_instance.openapi()
            targets = [
                BASE_DIR / "openapi.json",
                BASE_DIR.parent / "openapi.json",
                Path("openapi.json")
            ]
            for t in targets:
                try:
                    t.parent.mkdir(parents=True, exist_ok=True)
                    with open(t, "w", encoding="utf-8") as f:
                        json.dump(openapi_schema, f, indent=2)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Could not write openapi.json: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app_state(app)
    yield

app = FastAPI(
    title="NPC - Real-World Adventure App Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS: allow all origins in dev (Lovable preview + localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup uploads directory
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# --- Custom Exception Handlers (Exact API Contract Error Shape) ---
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = "; ".join([f"{'.'.join(str(l) for l in e.get('loc', []))}: {e.get('msg')}" for e in errors])
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": msg}}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "not_found" if exc.status_code == 404 else ("player_required" if exc.status_code == 401 else "upstream_error")
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": detail}}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "upstream_error", "message": "An unexpected server error occurred."}}
    )


# --- Helper Functions ---
def get_current_player(
    x_player_id: Optional[str] = Header(None, alias="X-Player-Id"),
    db: Session = Depends(get_db)
) -> PlayerModel:
    if not x_player_id or not x_player_id.strip():
        raise AppException(
            status_code=401,
            code="player_required",
            message="X-Player-Id header is required"
        )
    player = db.query(PlayerModel).filter(PlayerModel.id == x_player_id.strip()).first()
    if not player:
        raise AppException(
            status_code=401,
            code="player_required",
            message=f"Player with id '{x_player_id}' not found"
        )
    return player

def model_to_player(p: PlayerModel) -> Player:
    return Player(
        id=p.id,
        display_name=p.display_name,
        city=p.city,
        level=p.level,
        total_xp=p.total_xp,
        xp_in_level=p.xp_in_level,
        xp_for_next_level=p.xp_for_next_level,
        quests_completed=p.quests_completed,
        achievements_unlocked=p.achievements_unlocked,
        created_at=p.created_at
    )

def model_to_preferences(p: PreferencesModel) -> Preferences:
    interests = json.loads(p.interests) if isinstance(p.interests, str) else p.interests
    return Preferences(
        display_name=p.display_name,
        interests=interests,
        novelty_frequency=p.novelty_frequency, # type: ignore
        social_style=p.social_style, # type: ignore
        comfort_level=p.comfort_level,
        city=p.city,
        lat=p.lat,
        lng=p.lng,
        free_time_minutes=p.free_time_minutes,
        max_distance_km=p.max_distance_km,
        budget_inr=p.budget_inr,
        accessibility_notes=p.accessibility_notes,
        last_first_time=p.last_first_time # type: ignore
    )

def model_to_quest(q: QuestModel) -> Quest:
    loc = None
    if q.location:
        try:
            loc_data = json.loads(q.location) if isinstance(q.location, str) else q.location
            loc = QuestLocation(**loc_data)
        except Exception:
            pass

    src = None
    if q.source:
        try:
            src_data = json.loads(q.source) if isinstance(q.source, str) else q.source
            src = QuestSource(**src_data)
        except Exception:
            pass

    return Quest(
        id=q.id,
        title=q.title,
        description=q.description,
        why_selected=q.why_selected,
        category=q.category, # type: ignore
        difficulty=q.difficulty, # type: ignore
        duration_minutes=q.duration_minutes,
        estimated_cost_inr=q.estimated_cost_inr,
        cost_label=q.cost_label,
        xp_reward=q.xp_reward,
        status=q.status, # type: ignore
        location=loc,
        source=src,
        reflection_prompt=q.reflection_prompt,
        created_at=q.created_at,
        started_at=q.started_at,
        completed_at=q.completed_at
    )

def model_to_experience(e: ExperienceModel) -> Experience:
    return Experience(
        id=e.id,
        kind=e.kind, # type: ignore
        title=e.title,
        subtitle=e.subtitle,
        tag=e.tag,
        thumbnail_url=e.thumbnail_url,
        address=e.address,
        lat=e.lat,
        lng=e.lng,
        distance_km=e.distance_km,
        price_label=e.price_label,
        hours_label=e.hours_label,
        event_time_label=e.event_time_label,
        rating=e.rating,
        link_url=e.link_url,
        source=e.source, # type: ignore
        why_worth_it=e.why_worth_it,
        fetched_at=e.fetched_at
    )

def ensure_player_coords(player: PlayerModel, db: Session) -> None:
    """Fill in missing coordinates from the player's typed city, so searches and distances
    centre on where they actually are. Lookups are cached, so this is cheap after the first call."""
    prefs_model = player.preferences
    if not prefs_model or (prefs_model.lat is not None and prefs_model.lng is not None):
        return
    coords = geocode_city(prefs_model.city, db)
    if coords:
        prefs_model.lat, prefs_model.lng = coords
        db.commit()
        db.refresh(player)


def distance_from_player(prefs: Preferences, lat: Optional[float], lng: Optional[float]) -> Optional[float]:
    if None in (prefs.lat, prefs.lng, lat, lng):
        return None
    return haversine_km(prefs.lat, prefs.lng, lat, lng)


def nearby_for_player(exps: List[Experience], prefs: Preferences) -> List[Experience]:
    """Keep experiences within the player's max distance, with distance measured from the player.
    Items without coordinates (most events) are kept only if their address names the player's city.
    If the player's own location is unknown, nothing can be filtered and everything is returned."""
    if prefs.lat is None or prefs.lng is None:
        return exps

    city_key = (prefs.city or "").split(",")[0].strip().lower()
    out: List[Experience] = []
    for e in exps:
        d = distance_from_player(prefs, e.lat, e.lng)
        if d is not None:
            if d <= prefs.max_distance_km:
                out.append(e.model_copy(update={"distance_km": d}))
        elif city_key and city_key in (e.address or "").lower():
            out.append(e.model_copy(update={"distance_km": None}))
    out.sort(key=lambda e: (e.distance_km is None, e.distance_km or 0.0))
    return out


def model_to_reward(r: RewardModel) -> Reward:
    return Reward(
        id=r.id,
        title=r.title,
        description=r.description,
        brand=r.brand,
        category=r.category,
        discount_amount_inr=r.discount_amount_inr,
        cost_xp=r.cost_xp,
        location=r.location,
        terms=r.terms,
        icon_key=r.icon_key,
        is_active=bool(r.is_active)
    )

def model_to_redemption(red: RewardRedemptionModel) -> RewardRedemption:
    reward_title = red.reward.title if red.reward else "Perk Voucher"
    brand = red.reward.brand if red.reward else "NPC Partner"
    return RewardRedemption(
        id=red.id,
        reward_id=red.reward_id,
        reward_title=reward_title,
        brand=brand,
        voucher_code=red.voucher_code,
        cost_xp=red.cost_xp,
        redeemed_at=red.redeemed_at,
        expires_at=red.expires_at,
        status=red.status
    )


def get_player_autopilot(player: PlayerModel, db: Session) -> Autopilot:
    prefs_model = player.preferences
    if not prefs_model:
        prefs_model = db.query(PreferencesModel).filter(PreferencesModel.player_id == player.id).first()
    prefs = model_to_preferences(prefs_model)

    # Get completions in last 14 days
    completions = db.query(CompletionModel).filter(CompletionModel.player_id == player.id).all()
    comp_list = []
    for c in completions:
        q = db.query(QuestModel).filter(QuestModel.id == c.quest_id).first()
        cat = q.category if q else "explore"
        comp_list.append((c.completed_at, cat))

    return calculate_autopilot(prefs, comp_list)

# --- Routes (API CONTRACT v1) ---

# Health endpoints (both root and api/v1)
@app.get("/health", response_model=HealthResponse)
@app.get("/api/v1/health", response_model=HealthResponse)
def get_health():
    return HealthResponse(
        status="ok",
        mock_mode=settings.mock_mode,
        serpapi_live=settings.is_serpapi_live,
        llm_live=settings.is_llm_live
    )

# Player Onboarding
@app.post("/api/v1/players", response_model=CreatePlayerResponse, status_code=status.HTTP_201_CREATED)
def create_player(prefs_in: Preferences, db: Session = Depends(get_db)):
    if not prefs_in.display_name.strip():
        raise AppException(422, "validation_error", "Display name cannot be empty.")
    if not prefs_in.interests:
        raise AppException(422, "validation_error", "At least one interest is required.")

    player_id = f"p_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    new_player = PlayerModel(
        id=player_id,
        display_name=prefs_in.display_name.strip(),
        city=prefs_in.city.strip() if prefs_in.city else "Mumbai",
        level=1,
        total_xp=0,
        xp_in_level=0,
        xp_for_next_level=1000,
        quests_completed=0,
        achievements_unlocked=0,
        created_at=now_iso
    )
    db.add(new_player)

    new_prefs = PreferencesModel(
        player_id=player_id,
        display_name=prefs_in.display_name.strip(),
        interests=json.dumps(prefs_in.interests),
        novelty_frequency=prefs_in.novelty_frequency,
        social_style=prefs_in.social_style,
        comfort_level=prefs_in.comfort_level,
        city=prefs_in.city.strip() if prefs_in.city else "Mumbai",
        lat=prefs_in.lat,
        lng=prefs_in.lng,
        free_time_minutes=prefs_in.free_time_minutes,
        max_distance_km=prefs_in.max_distance_km,
        budget_inr=prefs_in.budget_inr,
        accessibility_notes=prefs_in.accessibility_notes,
        last_first_time=prefs_in.last_first_time
    )
    db.add(new_prefs)
    db.commit()
    db.refresh(new_player)
    ensure_player_coords(new_player, db)

    # Initial Autopilot
    autopilot = calculate_autopilot(prefs_in, [])

    # Pre-generate today's quest on onboarding so when player navigates to Home, it loads instantly (0ms)
    try:
        generate_quest(new_player, prefs_in, db)
    except Exception as e:
        logger.warning(f"Could not pre-warm quest on player creation: {e}")

    return CreatePlayerResponse(
        player=model_to_player(new_player),
        autopilot=autopilot
    )

@app.get("/api/v1/players/me", response_model=PlayerMeResponse)
def get_player_me(
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    prefs = model_to_preferences(player.preferences)
    autopilot = get_player_autopilot(player, db)
    return PlayerMeResponse(
        player=model_to_player(player),
        preferences=prefs,
        autopilot=autopilot
    )

@app.patch("/api/v1/players/me", response_model=PlayerMeResponse)
def update_player_me(
    updates: PreferencesUpdate,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    prefs_model = player.preferences
    up_dict = updates.model_dump(exclude_unset=True)

    if "display_name" in up_dict and up_dict["display_name"]:
        player.display_name = up_dict["display_name"]
        prefs_model.display_name = up_dict["display_name"]
    if "city" in up_dict and up_dict["city"]:
        if up_dict["city"] != prefs_model.city and "lat" not in up_dict and "lng" not in up_dict:
            # Old coordinates belong to the old city; re-resolve them below.
            prefs_model.lat = None
            prefs_model.lng = None
        player.city = up_dict["city"]
        prefs_model.city = up_dict["city"]
    if "interests" in up_dict and up_dict["interests"] is not None:
        prefs_model.interests = json.dumps(up_dict["interests"])
    if "novelty_frequency" in up_dict and up_dict["novelty_frequency"]:
        prefs_model.novelty_frequency = up_dict["novelty_frequency"]
    if "social_style" in up_dict and up_dict["social_style"]:
        prefs_model.social_style = up_dict["social_style"]
    if "comfort_level" in up_dict and up_dict["comfort_level"] is not None:
        prefs_model.comfort_level = up_dict["comfort_level"]
    if "lat" in up_dict:
        prefs_model.lat = up_dict["lat"]
    if "lng" in up_dict:
        prefs_model.lng = up_dict["lng"]
    if "free_time_minutes" in up_dict and up_dict["free_time_minutes"] is not None:
        prefs_model.free_time_minutes = up_dict["free_time_minutes"]
    if "max_distance_km" in up_dict and up_dict["max_distance_km"] is not None:
        prefs_model.max_distance_km = up_dict["max_distance_km"]
    if "budget_inr" in up_dict and up_dict["budget_inr"] is not None:
        prefs_model.budget_inr = up_dict["budget_inr"]
    if "accessibility_notes" in up_dict:
        prefs_model.accessibility_notes = up_dict["accessibility_notes"]
    if "last_first_time" in up_dict and up_dict["last_first_time"]:
        prefs_model.last_first_time = up_dict["last_first_time"]

    db.commit()
    db.refresh(player)
    ensure_player_coords(player, db)

    prefs = model_to_preferences(player.preferences)
    autopilot = get_player_autopilot(player, db)
    return PlayerMeResponse(
        player=model_to_player(player),
        preferences=prefs,
        autopilot=autopilot
    )

# Home Dashboard
@app.get("/api/v1/home", response_model=HomeResponse)
def get_home(
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    ensure_player_coords(player, db)
    prefs = model_to_preferences(player.preferences)
    autopilot = get_player_autopilot(player, db)

    # Check for today's quest (created today UTC)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Look for any quest created today
    today_quests = db.query(QuestModel).filter(
        QuestModel.player_id == player.id,
        QuestModel.created_at.startswith(today_str)
    ).order_by(QuestModel.created_at.desc()).all()

    todays_quest: Optional[Quest] = None
    if today_quests:
        active_or_suggested = next((q for q in today_quests if q.status in ["suggested", "active"]), None)
        if active_or_suggested:
            todays_quest = model_to_quest(active_or_suggested)
        else:
            # Check if one was completed today
            completed = next((q for q in today_quests if q.status == "completed"), None)
            if completed:
                todays_quest = model_to_quest(completed)
            # If all were dismissed, todays_quest is None
    else:
        # Lazily generate today's quest if none exists for today
        todays_quest = generate_quest(player, prefs, db)

    # Recent activity: max 2 completed quests
    completions = db.query(CompletionModel).filter(
        CompletionModel.player_id == player.id
    ).order_by(CompletionModel.completed_at.desc()).limit(2).all()

    recent_activity: List[ActivityItem] = []
    for c in completions:
        q = db.query(QuestModel).filter(QuestModel.id == c.quest_id).first()
        title = q.title if q else "Side Quest"
        recent_activity.append(ActivityItem(
            quest_id=c.quest_id,
            title=title,
            xp_earned=c.xp_awarded,
            completed_at=c.completed_at
        ))

    return HomeResponse(
        player=model_to_player(player),
        autopilot=autopilot,
        todays_quest=todays_quest,
        recent_activity=recent_activity
    )

# Quests
@app.post("/api/v1/quests/generate", response_model=QuestResponse)
def generate_new_quest(
    body: GenerateQuestRequest,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    ensure_player_coords(player, db)
    prefs = model_to_preferences(player.preferences)

    # replace_today=true marks the current suggested quest "dismissed" (no penalty) and returns a new one
    if body.replace_today:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_suggested = db.query(QuestModel).filter(
            QuestModel.player_id == player.id,
            QuestModel.created_at.startswith(today_str),
            QuestModel.status == "suggested"
        ).first()
        if current_suggested:
            current_suggested.status = "dismissed"
            db.commit()

    quest = generate_quest(player, prefs, db, requested_category=body.category)
    return QuestResponse(quest=quest)

@app.get("/api/v1/quests", response_model=QuestsListResponse)
def list_quests(
    category: Optional[Category] = Query(None),
    status: Optional[QuestStatus] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    query = db.query(QuestModel).filter(QuestModel.player_id == player.id)
    if category:
        query = query.filter(QuestModel.category == category)
    if status:
        query = query.filter(QuestModel.status == status)
    else:
        # Default to suggested and active quests
        query = query.filter(QuestModel.status.in_(["suggested", "active"]))

    quests = query.order_by(QuestModel.created_at.desc()).limit(limit).all()
    return QuestsListResponse(quests=[model_to_quest(q) for q in quests])

@app.get("/api/v1/quests/{quest_id}", response_model=QuestResponse)
def get_quest(
    quest_id: str,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    q = db.query(QuestModel).filter(
        QuestModel.id == quest_id,
        QuestModel.player_id == player.id
    ).first()
    if not q:
        raise AppException(404, "not_found", "Quest not found.")
    return QuestResponse(quest=model_to_quest(q))

@app.post("/api/v1/quests/{quest_id}/start", response_model=QuestResponse)
def start_quest(
    quest_id: str,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    q = db.query(QuestModel).filter(
        QuestModel.id == quest_id,
        QuestModel.player_id == player.id
    ).first()
    if not q:
        raise AppException(404, "not_found", "Quest not found.")

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if q.status == "suggested":
        q.status = "active"
        if not q.started_at:
            q.started_at = now_iso
        db.commit()
        db.refresh(q)

    return QuestResponse(quest=model_to_quest(q))

@app.post("/api/v1/quests/{quest_id}/dismiss", response_model=QuestResponse)
def dismiss_quest(
    quest_id: str,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    q = db.query(QuestModel).filter(
        QuestModel.id == quest_id,
        QuestModel.player_id == player.id
    ).first()
    if not q:
        raise AppException(404, "not_found", "Quest not found.")

    if q.status != "completed":
        q.status = "dismissed"
        db.commit()
        db.refresh(q)

    return QuestResponse(quest=model_to_quest(q))

@app.post("/api/v1/quests/{quest_id}/complete", response_model=CompleteQuestResponse)
def complete_quest(
    quest_id: str,
    body: CompleteQuestRequest,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    q = db.query(QuestModel).filter(
        QuestModel.id == quest_id,
        QuestModel.player_id == player.id
    ).first()
    if not q:
        raise AppException(404, "not_found", "Quest not found.")

    if q.status == "completed":
        raise AppException(422, "validation_error", "This quest is already in your journal.")

    if len(body.reflection) > 500:
        raise AppException(422, "validation_error", "Reflection must be 500 characters or fewer.")

    # Photo processing (optional supporting evidence)
    photo_url: Optional[str] = None
    if body.photo_data_url:
        try:
            # Format: "data:image/jpeg;base64,..."
            if "," in body.photo_data_url:
                header, b64_data = body.photo_data_url.split(",", 1)
            else:
                b64_data = body.photo_data_url

            photo_bytes = base64.b64decode(b64_data)
            if len(photo_bytes) > 2 * 1024 * 1024:
                raise AppException(422, "validation_error", "Photo size exceeds 2 MB limit.")

            file_name = f"{q.id}.jpg"
            file_path = UPLOADS_DIR / file_name
            with open(file_path, "wb") as f:
                f.write(photo_bytes)

            photo_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/uploads/{file_name}"
        except AppException:
            raise
        except Exception as e:
            raise AppException(422, "validation_error", f"Invalid photo data: {e}")

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    q.status = "completed"
    q.completed_at = now_iso
    if not q.started_at:
        q.started_at = now_iso

    xp_awarded = q.xp_reward
    old_level = player.level
    player.total_xp += xp_awarded
    # Level math: level = floor(total_xp / 1000) + 1; xp_in_level = total_xp % 1000.
    new_level = math.floor(player.total_xp / 1000) + 1
    player.level = new_level
    player.xp_in_level = player.total_xp % 1000
    player.quests_completed += 1
    leveled_up = new_level > old_level

    # Record completion
    completion = CompletionModel(
        id=f"c_{uuid.uuid4().hex[:10]}",
        quest_id=q.id,
        player_id=player.id,
        reflection=body.reflection,
        photo_path=photo_url,
        xp_awarded=xp_awarded,
        completed_at=now_iso
    )
    db.add(completion)

    # Check achievements
    existing_unlocked = {a.achievement_id for a in player.achievements}
    # Calculate category counts
    completions = db.query(CompletionModel).filter(CompletionModel.player_id == player.id).all()
    cat_counts = {c: 0 for c in ["explore", "social", "creativity", "courage", "awareness"]}
    for c in completions:
        cq = db.query(QuestModel).filter(QuestModel.id == c.quest_id).first()
        if cq and cq.category in cat_counts:
            cat_counts[cq.category] += 1
    # Add current quest's category
    if q.category in cat_counts:
        cat_counts[q.category] += 1

    all_ach, newly_unlocked = evaluate_achievements(
        quests_completed=player.quests_completed,
        category_counts=cat_counts,
        currently_unlocked_ids=existing_unlocked,
        now_iso=now_iso
    )

    for na in newly_unlocked:
        db.add(PlayerAchievementModel(
            player_id=player.id,
            achievement_id=na.id,
            unlocked_at=now_iso
        ))

    player.achievements_unlocked = len(existing_unlocked) + len(newly_unlocked)
    db.commit()
    db.refresh(q)
    db.refresh(player)

    autopilot = get_player_autopilot(player, db)

    return CompleteQuestResponse(
        quest=model_to_quest(q),
        xp_awarded=xp_awarded,
        player=model_to_player(player),
        leveled_up=leveled_up,
        new_level=new_level if leveled_up else None,
        achievements_unlocked=newly_unlocked,
        autopilot=autopilot,
        message="You broke your routine today."
    )

# Explore / Experiences
@app.get("/api/v1/explore/experiences", response_model=ExperiencesListResponse)
def list_experiences(
    tag: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    ensure_player_coords(player, db)
    prefs = model_to_preferences(player.preferences)

    query = db.query(ExperienceModel)
    if tag and tag.strip():
        query = query.filter(ExperienceModel.tag == tag.strip())
    if q and q.strip():
        search_pattern = f"%{q.strip().lower()}%"
        query = query.filter(
            (ExperienceModel.title.ilike(search_pattern)) |
            (ExperienceModel.subtitle.ilike(search_pattern)) |
            (ExperienceModel.address.ilike(search_pattern)) |
            (ExperienceModel.tag.ilike(search_pattern))
        )

    # The experiences table is shared by all players, so filter it to this player's area.
    results = nearby_for_player([model_to_experience(e) for e in query.all()], prefs)

    # Nothing nearby yet: search around the player and show what comes back
    if not results:
        city = prefs.city or "Mumbai"
        params: Dict[str, Any] = {"q": f"{q or 'interesting places to visit'} in {city}", "type": "search"}
        if prefs.lat is not None and prefs.lng is not None:
            params["ll"] = f"@{prefs.lat},{prefs.lng},14z"
        exps, cached = fetch_serp_cached("google_maps", params, db, prefs.lat, prefs.lng)
        if tag:
            exps = [e for e in exps if e.tag == tag]
        exps = nearby_for_player(exps, prefs) or exps
        return ExperiencesListResponse(experiences=exps[:limit], cached=cached)

    return ExperiencesListResponse(experiences=results[:limit], cached=True)

@app.get("/api/v1/explore/experiences/{experience_id}", response_model=ExperienceResponse)
def get_experience(
    experience_id: str,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    e = db.query(ExperienceModel).filter(ExperienceModel.id == experience_id).first()
    if not e:
        raise AppException(404, "not_found", "Experience not found.")
    return ExperienceResponse(experience=model_to_experience(e))

@app.post("/api/v1/explore/experiences/{experience_id}/quest", response_model=QuestResponse)
def quest_from_experience(
    experience_id: str,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    e = db.query(ExperienceModel).filter(ExperienceModel.id == experience_id).first()
    if not e:
        raise AppException(404, "not_found", "Experience not found.")

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # The stored distance was measured from whoever first fetched this place; measure from this player.
    ensure_player_coords(player, db)
    distance_km = distance_from_player(model_to_preferences(player.preferences), e.lat, e.lng)

    # Map experience attributes into a Quest
    category: Category = (
        "explore" if e.tag in ["food", "bookstore", "outdoors"]
        else ("social" if e.tag in ["free events"]
        else ("awareness" if e.tag in ["street art"]
        else "creativity"))
    )
    difficulty: Difficulty = "hard" if e.kind == "activity" else ("medium" if e.kind == "event" else "easy")
    xp_reward = XP_MAP[difficulty]

    maps_url = e.link_url or f"https://www.google.com/maps/search/?api=1&query={e.title}"
    location = QuestLocation(
        name=e.title,
        address=e.address,
        lat=e.lat,
        lng=e.lng,
        distance_km=distance_km,
        maps_url=maps_url
    )
    source = QuestSource(
        type=e.source, # type: ignore
        title=e.title,
        url=e.link_url,
        thumbnail_url=e.thumbnail_url,
        fetched_at=e.fetched_at
    )

    quest_id = f"q_{uuid.uuid4().hex[:10]}"
    new_quest = QuestModel(
        id=quest_id,
        player_id=player.id,
        title=f"Visit {e.title}",
        description=f"{e.subtitle or 'A local find'}. {e.why_worth_it} Go once, stay at least 20 minutes.",
        why_selected=(
            f"It's {distance_km} km away and matches the '{e.tag}' vibe you discovered."
            if distance_km is not None
            else f"It matches the '{e.tag}' vibe you discovered."
        ),
        category=category,
        difficulty=difficulty,
        duration_minutes=120 if e.kind == "activity" else 45,
        estimated_cost_inr=None,
        cost_label=e.price_label or "Cost unknown",
        xp_reward=xp_reward,
        status="suggested",
        location=location.model_dump_json(),
        source=source.model_dump_json(),
        reflection_prompt="What was the first thing you noticed when you arrived?",
        created_at=now_iso,
        started_at=None,
        completed_at=None
    )
    db.add(new_quest)
    db.commit()
    db.refresh(new_quest)

    return QuestResponse(quest=model_to_quest(new_quest))

# Journey & Weekly Recap
@app.get("/api/v1/journey", response_model=JourneyResponse)
def get_journey(
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. Achievements (all 8, with unlocked flags and unlocked_at)
    player_ach_map = {pa.achievement_id: pa.unlocked_at for pa in player.achievements}
    achievements: List[Achievement] = []
    for a in ALL_ACHIEVEMENTS:
        aid = a["id"]
        is_unlocked = aid in player_ach_map
        achievements.append(Achievement(
            id=aid,
            name=a["name"],
            description=a["description"],
            icon_key=a["icon_key"],
            unlocked=is_unlocked,
            unlocked_at=player_ach_map.get(aid)
        ))

    # 2. Journal: completions newest first
    completions = db.query(CompletionModel).filter(
        CompletionModel.player_id == player.id
    ).order_by(CompletionModel.completed_at.desc()).all()

    journal: List[JournalEntry] = []
    cat_counts: Dict[str, int] = {
        "explore": 0, "social": 0, "creativity": 0, "courage": 0, "awareness": 0
    }

    for c in completions:
        q = db.query(QuestModel).filter(QuestModel.id == c.quest_id).first()
        if q:
            if q.category in cat_counts:
                cat_counts[q.category] += 1
            loc_name = None
            if q.location:
                try:
                    ld = json.loads(q.location) if isinstance(q.location, str) else q.location
                    loc_name = ld.get("name")
                except Exception:
                    pass
            journal.append(JournalEntry(
                quest_id=q.id,
                title=q.title,
                category=q.category, # type: ignore
                completed_at=c.completed_at,
                xp_earned=c.xp_awarded,
                reflection=c.reflection,
                photo_url=c.photo_path,
                location_name=loc_name
            ))

    return JourneyResponse(
        player=model_to_player(player),
        achievements=achievements,
        journal=journal,
        category_counts=cat_counts
    )

@app.get("/api/v1/journey/weekly-recap", response_model=WeeklyRecapResponse)
def get_weekly_recap(
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)

    now_iso = now.isoformat().replace("+00:00", "Z")
    week_start_iso = week_start.isoformat().replace("+00:00", "Z")

    # Get completions in last 7 days
    completions = db.query(CompletionModel).filter(
        CompletionModel.player_id == player.id,
        CompletionModel.completed_at >= week_start_iso
    ).all()

    cats_tried = set()
    new_places = 0
    xp_earned = 0
    recent_quest_dicts = []

    for c in completions:
        q = db.query(QuestModel).filter(QuestModel.id == c.quest_id).first()
        if q:
            cats_tried.add(q.category)
            xp_earned += c.xp_awarded
            if q.location:
                new_places += 1
            recent_quest_dicts.append({"title": q.title, "category": q.category})

    stats = {
        "quests_completed": len(completions),
        "new_places": new_places,
        "categories_tried": list(cats_tried),
        "xp_earned": xp_earned
    }

    summary, gen_by = generate_weekly_recap_text(stats, recent_quest_dicts)

    return WeeklyRecapResponse(
        week_start=week_start_iso,
        week_end=now_iso,
        summary=summary,
        stats=WeeklyRecapStats(
            quests_completed=stats["quests_completed"],
            new_places=stats["new_places"],
            categories_tried=stats["categories_tried"],
            xp_earned=stats["xp_earned"]
        ),
        generated_by=gen_by # type: ignore
    )

# Rewards & Perks
@app.get("/api/v1/rewards", response_model=RewardsListResponse)
def list_rewards(
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    rewards_models = db.query(RewardModel).filter(RewardModel.is_active == 1).all()
    redemptions_models = db.query(RewardRedemptionModel).filter(
        RewardRedemptionModel.player_id == player.id
    ).order_by(RewardRedemptionModel.redeemed_at.desc()).all()

    return RewardsListResponse(
        rewards=[model_to_reward(r) for r in rewards_models],
        redemptions=[model_to_redemption(r) for r in redemptions_models],
        player_xp=player.total_xp
    )

@app.post("/api/v1/rewards/{reward_id}/redeem", response_model=RedeemRewardResponse)
def redeem_reward(
    reward_id: str,
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    reward = db.query(RewardModel).filter(RewardModel.id == reward_id).first()
    if not reward or not reward.is_active:
        raise AppException(404, "not_found", "Reward not found or no longer active.")

    if player.total_xp < reward.cost_xp:
        raise AppException(
            422,
            "validation_error",
            f"Not enough XP! You have {player.total_xp} XP, but need {reward.cost_xp} XP."
        )

    # Deduct XP
    player.total_xp -= reward.cost_xp
    player.level = math.floor(player.total_xp / 1000) + 1
    player.xp_in_level = player.total_xp % 1000

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat().replace("+00:00", "Z")
    expires_iso = (now + timedelta(days=30)).isoformat().replace("+00:00", "Z")

    brand_slug = "".join(c for c in reward.brand[:6].upper() if c.isalnum()) or "NPC"
    code_suffix = uuid.uuid4().hex[:6].upper()
    voucher_code = f"NPC-{brand_slug}-{code_suffix}"

    redemption = RewardRedemptionModel(
        id=f"red_{uuid.uuid4().hex[:10]}",
        player_id=player.id,
        reward_id=reward.id,
        voucher_code=voucher_code,
        cost_xp=reward.cost_xp,
        redeemed_at=now_iso,
        expires_at=expires_iso,
        status="active"
    )
    db.add(redemption)
    db.commit()
    db.refresh(player)
    db.refresh(redemption)

    return RedeemRewardResponse(
        success=True,
        redemption=model_to_redemption(redemption),
        player=model_to_player(player),
        reward=model_to_reward(reward),
        code=voucher_code,
        message=f"Successfully redeemed {reward.title} for {reward.cost_xp} XP!"
    )

@app.get("/api/v1/rewards/my-redemptions")
def get_my_redemptions(
    player: PlayerModel = Depends(get_current_player),
    db: Session = Depends(get_db)
):
    redemptions_models = db.query(RewardRedemptionModel).filter(
        RewardRedemptionModel.player_id == player.id
    ).order_by(RewardRedemptionModel.redeemed_at.desc()).all()
    return {"redemptions": [model_to_redemption(r) for r in redemptions_models]}

# Initialize app state (DB tables, fixtures seed, openapi.json export)
init_app_state(app)

