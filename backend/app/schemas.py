from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

Category = Literal["explore", "social", "creativity", "courage", "awareness"]
Difficulty = Literal["easy", "medium", "hard"]
QuestStatus = Literal["suggested", "active", "completed", "dismissed"]
Interest = Literal["food", "art", "people", "learning", "outdoors", "culture"]
NoveltyFrequency = Literal["rarely", "monthly", "weekly", "daily"]
SocialStyle = Literal["solo", "friends", "either"]
LastFirstTime = Literal["this_week", "this_month", "this_year", "cant_remember"]
AutopilotLabel = Literal["Wide awake", "Mostly exploring", "Needs a little adventure", "Deep autopilot"]
SourceType = Literal["google_maps", "google_events", "google_search"]
ExperienceKind = Literal["place", "event", "activity"]

class Player(BaseModel):
    id: str
    display_name: str
    city: str
    level: int
    total_xp: int
    xp_in_level: int
    xp_for_next_level: int
    quests_completed: int
    achievements_unlocked: int
    created_at: str

class Preferences(BaseModel):
    display_name: str
    interests: List[Interest] = Field(..., min_length=1)
    novelty_frequency: NoveltyFrequency
    social_style: SocialStyle
    comfort_level: int = Field(..., ge=1, le=5)
    city: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    free_time_minutes: int = Field(..., ge=15, le=480)
    max_distance_km: float
    budget_inr: int
    accessibility_notes: Optional[str] = None
    last_first_time: LastFirstTime

class PreferencesUpdate(BaseModel):
    display_name: Optional[str] = None
    interests: Optional[List[Interest]] = None
    novelty_frequency: Optional[NoveltyFrequency] = None
    social_style: Optional[SocialStyle] = None
    comfort_level: Optional[int] = Field(None, ge=1, le=5)
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    free_time_minutes: Optional[int] = Field(None, ge=15, le=480)
    max_distance_km: Optional[float] = None
    budget_inr: Optional[int] = None
    accessibility_notes: Optional[str] = None
    last_first_time: Optional[LastFirstTime] = None

class Autopilot(BaseModel):
    score: int = Field(..., ge=0, le=100)
    label: AutopilotLabel
    explanation: str
    disclaimer: str = "A playful reflection of your reported habits. Not a psychological score."

class QuestSource(BaseModel):
    type: SourceType
    title: str
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    fetched_at: str

class QuestLocation(BaseModel):
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    distance_km: Optional[float] = None
    maps_url: Optional[str] = None

class Quest(BaseModel):
    id: str
    title: str
    description: str
    why_selected: str
    category: Category
    difficulty: Difficulty
    duration_minutes: int
    estimated_cost_inr: Optional[int] = None
    cost_label: str
    xp_reward: int
    status: QuestStatus
    location: Optional[QuestLocation] = None
    source: Optional[QuestSource] = None
    reflection_prompt: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class Experience(BaseModel):
    id: str
    kind: ExperienceKind
    title: str
    subtitle: Optional[str] = None
    tag: str
    thumbnail_url: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    distance_km: Optional[float] = None
    price_label: Optional[str] = None
    hours_label: Optional[str] = None
    event_time_label: Optional[str] = None
    rating: Optional[float] = None
    link_url: Optional[str] = None
    source: SourceType
    why_worth_it: str
    fetched_at: str

class ActivityItem(BaseModel):
    quest_id: str
    title: str
    xp_earned: int
    completed_at: str

class Achievement(BaseModel):
    id: str
    name: str
    description: str
    icon_key: str
    unlocked: bool
    unlocked_at: Optional[str] = None

class JournalEntry(BaseModel):
    quest_id: str
    title: str
    category: Category
    completed_at: str
    xp_earned: int
    reflection: Optional[str] = None
    photo_url: Optional[str] = None
    location_name: Optional[str] = None

class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mock_mode: bool
    serpapi_live: bool
    llm_live: bool

class CreatePlayerResponse(BaseModel):
    player: Player
    autopilot: Autopilot

class PlayerMeResponse(BaseModel):
    player: Player
    preferences: Preferences
    autopilot: Autopilot

class HomeResponse(BaseModel):
    player: Player
    autopilot: Autopilot
    todays_quest: Optional[Quest] = None
    recent_activity: List[ActivityItem] = Field(default_factory=list)

class GenerateQuestRequest(BaseModel):
    category: Optional[Category] = None
    replace_today: Optional[bool] = False

class QuestResponse(BaseModel):
    quest: Quest

class QuestsListResponse(BaseModel):
    quests: List[Quest]

class CompleteQuestRequest(BaseModel):
    reflection: str = Field(..., max_length=500)
    photo_data_url: Optional[str] = None

class CompleteQuestResponse(BaseModel):
    quest: Quest
    xp_awarded: int
    player: Player
    leveled_up: bool
    new_level: Optional[int] = None
    achievements_unlocked: List[Achievement]
    autopilot: Autopilot
    message: str = "You broke your routine today."

class ExperiencesListResponse(BaseModel):
    experiences: List[Experience]
    cached: bool

class ExperienceResponse(BaseModel):
    experience: Experience

class JourneyResponse(BaseModel):
    player: Player
    achievements: List[Achievement]
    journal: List[JournalEntry]
    category_counts: Dict[str, int]

class AnalyticsEntry(BaseModel):
    """One completed quest, with the details the analytics tab aggregates."""
    quest_id: str
    title: str
    category: Category
    difficulty: Difficulty
    duration_minutes: int
    estimated_cost_inr: Optional[int] = None
    xp_earned: int
    completed_at: str
    location: Optional[QuestLocation] = None
    has_reflection: bool
    has_photo: bool

class AnalyticsResponse(BaseModel):
    player: Player
    entries: List[AnalyticsEntry]  # completed quests, newest first
    quests_dismissed: int
    quests_open: int  # suggested or active
    autopilot_start: Autopilot  # reading from onboarding answers alone
    autopilot_now: Autopilot

class WeeklyRecapStats(BaseModel):
    quests_completed: int
    new_places: int
    categories_tried: List[Category]
    xp_earned: int

class WeeklyRecapResponse(BaseModel):
    week_start: str
    week_end: str
    summary: str
    stats: WeeklyRecapStats
    generated_by: Literal["llm", "template"]

class ErrorDetail(BaseModel):
    code: Literal["validation_error", "not_found", "player_required", "upstream_error", "no_suitable_quest"]
    message: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

