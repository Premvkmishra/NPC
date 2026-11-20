from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class PlayerModel(Base):
    __tablename__ = "players"

    id = Column(String, primary_key=True, index=True)
    display_name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    total_xp = Column(Integer, default=0, nullable=False)
    xp_in_level = Column(Integer, default=0, nullable=False)
    xp_for_next_level = Column(Integer, default=1000, nullable=False)
    quests_completed = Column(Integer, default=0, nullable=False)
    achievements_unlocked = Column(Integer, default=0, nullable=False)
    created_at = Column(String, nullable=False)

    preferences = relationship("PreferencesModel", back_populates="player", uselist=False, cascade="all, delete-orphan")
    quests = relationship("QuestModel", back_populates="player", cascade="all, delete-orphan")
    completions = relationship("CompletionModel", back_populates="player", cascade="all, delete-orphan")
    achievements = relationship("PlayerAchievementModel", back_populates="player", cascade="all, delete-orphan")

class PreferencesModel(Base):
    __tablename__ = "preferences"

    player_id = Column(String, ForeignKey("players.id"), primary_key=True)
    display_name = Column(String, nullable=False)
    interests = Column(Text, nullable=False) # JSON list
    novelty_frequency = Column(String, nullable=False)
    social_style = Column(String, nullable=False)
    comfort_level = Column(Integer, nullable=False)
    city = Column(String, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    free_time_minutes = Column(Integer, nullable=False)
    max_distance_km = Column(Float, nullable=False)
    budget_inr = Column(Integer, nullable=False)
    accessibility_notes = Column(Text, nullable=True)
    last_first_time = Column(String, nullable=False)

    player = relationship("PlayerModel", back_populates="preferences")

class QuestModel(Base):
    __tablename__ = "quests"

    id = Column(String, primary_key=True, index=True)
    player_id = Column(String, ForeignKey("players.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    why_selected = Column(Text, nullable=False)
    category = Column(String, nullable=False, index=True)
    difficulty = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    estimated_cost_inr = Column(Integer, nullable=True)
    cost_label = Column(String, nullable=False)
    xp_reward = Column(Integer, nullable=False)
    status = Column(String, nullable=False, index=True) # suggested, active, completed, dismissed
    location = Column(Text, nullable=True) # JSON
    source = Column(Text, nullable=True) # JSON
    reflection_prompt = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)
    started_at = Column(String, nullable=True)
    completed_at = Column(String, nullable=True)

    player = relationship("PlayerModel", back_populates="quests")
    completion = relationship("CompletionModel", back_populates="quest", uselist=False, cascade="all, delete-orphan")

class ExperienceModel(Base):
    __tablename__ = "experiences"

    id = Column(String, primary_key=True, index=True)
    kind = Column(String, nullable=False) # place, event, activity
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    tag = Column(String, nullable=False, index=True)
    thumbnail_url = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    price_label = Column(String, nullable=True)
    hours_label = Column(String, nullable=True)
    event_time_label = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    link_url = Column(Text, nullable=True)
    source = Column(String, nullable=False) # google_maps, google_events, google_search
    why_worth_it = Column(Text, nullable=False)
    fetched_at = Column(String, nullable=False)

class SerpCacheModel(Base):
    __tablename__ = "serp_cache"

    query_hash = Column(String, primary_key=True, index=True)
    engine = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    raw_json = Column(Text, nullable=False)
    fetched_at = Column(String, nullable=False)

class CompletionModel(Base):
    __tablename__ = "completions"

    id = Column(String, primary_key=True, index=True)
    quest_id = Column(String, ForeignKey("quests.id"), nullable=False, unique=True)
    player_id = Column(String, ForeignKey("players.id"), nullable=False, index=True)
    reflection = Column(Text, nullable=True)
    photo_path = Column(Text, nullable=True)
    xp_awarded = Column(Integer, nullable=False)
    completed_at = Column(String, nullable=False)

    quest = relationship("QuestModel", back_populates="completion")
    player = relationship("PlayerModel", back_populates="completions")

class PlayerAchievementModel(Base):
    __tablename__ = "player_achievements"

    player_id = Column(String, ForeignKey("players.id"), primary_key=True)
    achievement_id = Column(String, primary_key=True)
    unlocked_at = Column(String, nullable=False)

    player = relationship("PlayerModel", back_populates="achievements")

