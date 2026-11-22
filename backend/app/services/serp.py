import hashlib
import json
import logging
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import httpx
from sqlalchemy.orm import Session

from app.config import settings, BASE_DIR
from app.models import SerpCacheModel, ExperienceModel
from app.schemas import Experience, ExperienceKind, SourceType

logger = logging.getLogger("npc")

DEFAULT_MUMBAI_LAT = 19.1136
DEFAULT_MUMBAI_LNG = 72.8697
SERPAPI_URL = "https://serpapi.com/search.json"


def _gps(item: dict) -> Tuple[Optional[float], Optional[float]]:
    gps = item.get("gps_coordinates") or {}
    return gps.get("latitude"), gps.get("longitude")


def _distance(player_lat: Optional[float], player_lng: Optional[float],
              lat: Optional[float], lng: Optional[float]) -> Optional[float]:
    if None in (player_lat, player_lng, lat, lng):
        return None
    return haversine_km(player_lat, player_lng, lat, lng)

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

def query_hash(engine: str, params: Dict[str, Any]) -> str:
    serialized = json.dumps({"engine": engine, "params": params}, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def is_cache_valid(fetched_at_iso: str, ttl_hours: int) -> bool:
    try:
        dt = datetime.fromisoformat(fetched_at_iso.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - dt < timedelta(hours=ttl_hours)
    except Exception:
        return False

def load_fixture(fixture_filename: str) -> dict:
    for search_dir in [BASE_DIR / "fixtures", BASE_DIR.parent / "fixtures", Path("fixtures")]:
        p = search_dir / fixture_filename
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

def extract_tag(title: str, subtitle: Optional[str] = None, types: Optional[List[str]] = None) -> str:
    combined = f"{title} {subtitle or ''} {' '.join(types or [])}".lower()
    if any(w in combined for w in ["book", "bookstore", "read"]):
        return "bookstore"
    if any(w in combined for w in ["art", "gallery", "exhibition", "museum"]):
        return "gallery"
    if any(w in combined for w in ["workshop", "pottery", "craft", "class", "session"]):
        return "workshop"
    if any(w in combined for w in ["chai", "tea", "vada", "bun", "cafe", "food", "tapri", "restaurant"]):
        return "food"
    if any(w in combined for w in ["mural", "street art", "graffiti", "wall"]):
        return "street art"
    if any(w in combined for w in ["open mic", "comedy", "poetry", "live music", "meetup", "cleanup"]):
        return "free events"
    if any(w in combined for w in ["park", "garden", "nature", "hill", "cave"]):
        return "outdoors"
    return "discovery"

def parse_maps_results(
    data: dict,
    player_lat: Optional[float],
    player_lng: Optional[float],
    fetched_at: str
) -> List[Experience]:
    results: List[Experience] = []
    items = data.get("local_results", [])
    if not isinstance(items, list):
        items = []

    for item in items:
        title = item.get("title")
        if not title:
            continue
        place_id = item.get("place_id") or hashlib.md5(title.encode()).hexdigest()[:10]
        exp_id = f"exp_maps_{place_id}"

        lat, lng = _gps(item)
        distance_km = _distance(player_lat, player_lng, lat, lng)

        types = item.get("types", [])
        subtitle = item.get("type") or (types[0] if types else "Local find")
        tag = extract_tag(title, subtitle, types)

        hours = item.get("hours") or item.get("open_state")
        price = item.get("price")
        price_label = price if price else None
        rating = float(item["rating"]) if "rating" in item and item["rating"] is not None else None
        link_url = item.get("link")

        why_worth_it = f"Authentic local spot in {item.get('address') or 'the neighbourhood'}."
        if rating:
            why_worth_it += f" Rated {rating} stars."
        if "gallery" in tag:
            why_worth_it = "Ten minutes surrounded by original contemporary art resets your mindset."
        elif "bookstore" in tag:
            why_worth_it = "Shelves curated by human hands, full of titles you won't stumble upon online."
        elif "food" in tag:
            why_worth_it = "The quintessential local flavour made fresh in front of your eyes."

        results.append(Experience(
            id=exp_id,
            kind="place",
            title=title,
            subtitle=subtitle,
            tag=tag,
            thumbnail_url=item.get("thumbnail"),
            address=item.get("address"),
            lat=lat,
            lng=lng,
            distance_km=distance_km,
            price_label=price_label,
            hours_label=hours,
            event_time_label=None,
            rating=rating,
            link_url=link_url,
            source="google_maps",
            why_worth_it=why_worth_it,
            fetched_at=fetched_at
        ))
    return results

def parse_events_results(
    data: dict,
    player_lat: Optional[float],
    player_lng: Optional[float],
    fetched_at: str
) -> List[Experience]:
    results: List[Experience] = []
    items = data.get("events_results", [])
    if not isinstance(items, list):
        items = []

    for item in items:
        title = item.get("title")
        if not title:
            continue
        exp_id = f"exp_event_{hashlib.md5(title.encode()).hexdigest()[:10]}"

        addr_raw = item.get("address", [])
        address = ", ".join(addr_raw) if isinstance(addr_raw, list) else addr_raw

        date_info = item.get("date", {})
        when = date_info.get("when") or date_info.get("start_date")

        venue_info = item.get("venue", {})
        venue_name = venue_info.get("name") if isinstance(venue_info, dict) else None
        rating = float(venue_info.get("rating")) if isinstance(venue_info, dict) and venue_info.get("rating") else None

        tag = extract_tag(title, venue_name)

        ticket_info = item.get("ticket_info", [])
        price_label = "Free" if any(t.get("link_type") == "free" for t in ticket_info) else None

        why_worth_it = "Stepping into a shared room of strangers exploring a new skill or story."
        if "workshop" in tag or "pottery" in title.lower():
            why_worth_it = "Hands-on creative work where you leave with something made by you."
        elif "open mic" in title.lower():
            why_worth_it = "Witnessing strangers share raw, unvarnished words in an intimate space."

        # Google Events results carry no coordinates, so distance is unknown.
        results.append(Experience(
            id=exp_id,
            kind="event",
            title=title,
            subtitle=venue_name or "Community gathering",
            tag=tag,
            thumbnail_url=item.get("thumbnail"),
            address=address,
            lat=None,
            lng=None,
            distance_km=None,
            price_label=price_label,
            hours_label=None,
            event_time_label=when,
            rating=rating,
            link_url=item.get("link"),
            source="google_events",
            why_worth_it=why_worth_it,
            fetched_at=fetched_at
        ))
    return results

def parse_search_results(
    data: dict,
    player_lat: Optional[float],
    player_lng: Optional[float],
    fetched_at: str
) -> List[Experience]:
    results: List[Experience] = []

    # Check local_results
    local_raw = data.get("local_results", {})
    local_places = local_raw.get("places", []) if isinstance(local_raw, dict) else []
    for place in local_places:
        title = place.get("title")
        if not title:
            continue
        exp_id = f"exp_act_{hashlib.md5(title.encode()).hexdigest()[:10]}"
        address = place.get("address")
        rating = float(place["rating"]) if "rating" in place and place["rating"] is not None else None
        tag = extract_tag(title, address)
        lat, lng = _gps(place)

        results.append(Experience(
            id=exp_id,
            kind="activity",
            title=title,
            subtitle="Hidden neighbourhood gem",
            tag=tag,
            thumbnail_url=place.get("thumbnail"),
            address=address,
            lat=lat,
            lng=lng,
            distance_km=_distance(player_lat, player_lng, lat, lng),
            price_label=place.get("price") or "Under ₹100",
            hours_label=None,
            event_time_label=None,
            rating=rating,
            link_url=place.get("links", {}).get("directions"),
            source="google_search",
            why_worth_it="A genuine local classic recommended by neighbourhood insiders.",
            fetched_at=fetched_at
        ))

    # Check organic_results
    organic = data.get("organic_results", [])
    for item in organic:
        title = item.get("title")
        if not title:
            continue
        exp_id = f"exp_act_{hashlib.md5(title.encode()).hexdigest()[:10]}"
        snippet = item.get("snippet", "")
        tag = extract_tag(title, snippet)

        why_worth_it = snippet if snippet else "An offbeat city experience that breaks standard routines."

        results.append(Experience(
            id=exp_id,
            kind="activity",
            title=title.split(" - ")[0].split(" | ")[0],
            subtitle="Offbeat exploration",
            tag=tag,
            thumbnail_url=item.get("thumbnail"),
            address=None,
            lat=None,
            lng=None,
            distance_km=None,
            price_label="Free",
            hours_label=None,
            event_time_label=None,
            rating=None,
            link_url=item.get("link"),
            source="google_search",
            why_worth_it=why_worth_it[:160],
            fetched_at=fetched_at
        ))

    return results

def _serpapi_request(engine: str, params: Dict[str, Any]) -> Optional[str]:
    """One live SerpApi call, retried once on a 5xx or network error. Returns the raw JSON text or None."""
    req_params = dict(params)
    req_params["api_key"] = settings.SERPAPI_API_KEY
    req_params["engine"] = engine

    for attempt in range(2):
        try:
            resp = httpx.get(SERPAPI_URL, params=req_params, timeout=15.0)
        except Exception as e:
            logger.warning(f"SerpApi attempt {attempt + 1} failed: {e}")
            continue
        if resp.status_code < 500:
            if resp.is_success:
                return resp.text
            logger.warning(f"SerpApi returned {resp.status_code}: {resp.text[:200]}")
            return None
    return None


def _store_cache(db: Session, cached: Optional[SerpCacheModel], q_hash: str, engine: str,
                 params: Dict[str, Any], raw_json_str: str, now_iso: str) -> None:
    if cached:
        cached.raw_json = raw_json_str
        cached.fetched_at = now_iso
    else:
        db.add(SerpCacheModel(
            query_hash=q_hash,
            engine=engine,
            query=json.dumps(params),
            raw_json=raw_json_str,
            fetched_at=now_iso
        ))
    db.commit()


def geocode_city(city: str, db: Session) -> Optional[Tuple[float, float]]:
    """Resolve a typed city or area name to coordinates with one cached SerpApi Maps lookup.
    Returns None in mock mode or when the place can't be found."""
    city = (city or "").strip()
    if not city or not settings.is_serpapi_live:
        return None

    params = {"q": city, "type": "search"}
    q_hash = query_hash("google_maps", params)
    cached = db.query(SerpCacheModel).filter(SerpCacheModel.query_hash == q_hash).first()

    if cached:
        raw = cached.raw_json
    else:
        raw = _serpapi_request("google_maps", params)
        if raw is None:
            return None
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        _store_cache(db, None, q_hash, "google_maps", params, raw, now_iso)

    try:
        data = json.loads(raw)
    except Exception:
        return None

    # A city or area name usually resolves to a single place; otherwise use the top result.
    candidates = [data.get("place_results") or {}]
    local = data.get("local_results")
    if isinstance(local, list) and local:
        candidates.append(local[0])
    for c in candidates:
        lat, lng = _gps(c)
        if lat is not None and lng is not None:
            return float(lat), float(lng)

    logger.warning(f"Could not geocode city '{city}'.")
    return None


def fetch_serp_cached(
    engine: str,
    params: Dict[str, Any],
    db: Session,
    player_lat: Optional[float] = None,
    player_lng: Optional[float] = None
) -> Tuple[List[Experience], bool]:
    """
    Returns (experiences, is_cached)
    """
    q_hash = query_hash(engine, params)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. Check database cache
    cached = db.query(SerpCacheModel).filter(SerpCacheModel.query_hash == q_hash).first()
    if cached and is_cache_valid(cached.fetched_at, settings.SERP_CACHE_TTL_HOURS):
        try:
            data = json.loads(cached.raw_json)
            if engine == "google_maps":
                return parse_maps_results(data, player_lat, player_lng, cached.fetched_at), True
            elif engine == "google_events":
                return parse_events_results(data, player_lat, player_lng, cached.fetched_at), True
            else:
                return parse_search_results(data, player_lat, player_lng, cached.fetched_at), True
        except Exception:
            pass

    # 2. Live SerpApi, falling back to fixtures
    raw_json_str = _serpapi_request(engine, params) if settings.is_serpapi_live else None

    from_fixture = raw_json_str is None
    if from_fixture:
        if settings.is_serpapi_live:
            logger.warning(f"SerpApi failed for {engine} {params}; using fixture data instead.")
        if engine == "google_maps":
            data = load_fixture("serp_maps.json")
        elif engine == "google_events":
            data = load_fixture("serp_events.json")
        else:
            data = load_fixture("serp_search.json")
        raw_json_str = json.dumps(data)

    data = json.loads(raw_json_str)

    # 3. Cache live responses only, so fixture data never masks live results later
    if not from_fixture:
        _store_cache(db, cached, q_hash, engine, params, raw_json_str, now_iso)

    if engine == "google_maps":
        exps = parse_maps_results(data, player_lat, player_lng, now_iso)
    elif engine == "google_events":
        exps = parse_events_results(data, player_lat, player_lng, now_iso)
    else:
        exps = parse_search_results(data, player_lat, player_lng, now_iso)

    # Fixture data stands in for a failed live call; keep it out of the shared table in live mode
    if from_fixture and settings.is_serpapi_live:
        return exps, False

    # Also save or update experiences in DB
    for exp in exps:
        existing = db.query(ExperienceModel).filter(ExperienceModel.id == exp.id).first()
        if not existing:
            db.add(ExperienceModel(
                id=exp.id,
                kind=exp.kind,
                title=exp.title,
                subtitle=exp.subtitle,
                tag=exp.tag,
                thumbnail_url=exp.thumbnail_url,
                address=exp.address,
                lat=exp.lat,
                lng=exp.lng,
                distance_km=exp.distance_km,
                price_label=exp.price_label,
                hours_label=exp.hours_label,
                event_time_label=exp.event_time_label,
                rating=exp.rating,
                link_url=exp.link_url,
                source=exp.source,
                why_worth_it=exp.why_worth_it,
                fetched_at=exp.fetched_at
            ))
    db.commit()

    return exps, False

def get_experiences_for_category(
    category: str,
    city: str,
    lat: Optional[float],
    lng: Optional[float],
    max_distance_km: float,
    db: Session
) -> List[Experience]:
    """
    Mapped per pipeline specifications:
    explore -> Maps "hidden gems / public art / unusual landmarks", "offbeat places"
    creativity -> Maps "art gallery / pottery studio" + Events "workshop"
    social -> Events "meetup / open mic / community event"
    courage -> Search "free open mic / try-something-scary beginner friendly"
    awareness -> Maps "park / garden / quiet library" + Search "slow walk / nature spots"
    """
    # Mock fixtures are Andheri data, so mock mode keeps Andheri as the origin.
    # In live mode an unknown location stays unknown instead of silently becoming Andheri.
    if (lat is None or lng is None) and not settings.is_serpapi_live:
        lat, lng = DEFAULT_MUMBAI_LAT, DEFAULT_MUMBAI_LNG

    def maps(q: str) -> Tuple[str, Dict[str, Any]]:
        # Name the city in the query too, so results stay local even without coordinates.
        params: Dict[str, Any] = {"q": f"{q} in {city}", "type": "search"}
        if lat is not None and lng is not None:
            params["ll"] = f"@{lat},{lng},14z"
        return "google_maps", params

    queries: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {
        "explore": [maps("hidden gems unusual landmarks"), ("google", {"q": f"offbeat places {city}"})],
        "creativity": [maps("art gallery pottery studio"), ("google_events", {"q": f"workshop in {city}"})],
        "social": [("google_events", {"q": f"meetup open mic community event in {city}"}), maps("live comedy open mic cafe")],
        "courage": [("google", {"q": f"free open mic try-something-scary beginner friendly {city}"}),
                    ("google_events", {"q": f"improv theater beginner in {city}"})],
        "awareness": [maps("park garden quiet library"), ("google", {"q": f"slow walk nature spots {city}"})],
    }

    results: List[Experience] = []
    for engine, params in queries.get(category, [maps("places to visit")]):
        exps, _ = fetch_serp_cached(engine, params, db, lat, lng)
        results.extend(exps)

    # Filter by max_distance_km if distance is known
    filtered = [e for e in results if e.distance_km is None or e.distance_km <= max_distance_km]
    return filtered if filtered else results

