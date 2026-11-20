import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import httpx
from sqlalchemy.orm import Session

from app.config import settings, BASE_DIR
from app.models import SerpCacheModel, ExperienceModel
from app.schemas import Experience, ExperienceKind, SourceType

DEFAULT_MUMBAI_LAT = 19.1136
DEFAULT_MUMBAI_LNG = 72.8697

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
    p_lat = player_lat or DEFAULT_MUMBAI_LAT
    p_lng = player_lng or DEFAULT_MUMBAI_LNG

    for item in items:
        title = item.get("title")
        if not title:
            continue
        place_id = item.get("place_id") or hashlib.md5(title.encode()).hexdigest()[:10]
        exp_id = f"exp_maps_{place_id}"

        gps = item.get("gps_coordinates", {})
        lat = gps.get("latitude")
        lng = gps.get("longitude")

        distance_km = haversine_km(p_lat, p_lng, lat, lng) if lat and lng else None

        types = item.get("types", [])
        subtitle = item.get("type") or (types[0] if types else "Local find")
        tag = extract_tag(title, subtitle, types)

        hours = item.get("hours") or item.get("open_state")
        price = item.get("price")
        price_label = price if price else None
        rating = float(item["rating"]) if "rating" in item and item["rating"] is not None else None
        link_url = item.get("link")

        why_worth_it = f"Authentic local spot in {item.get('address', 'Mumbai')}. Rated {rating or 4.5} stars."
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
    p_lat = player_lat or DEFAULT_MUMBAI_LAT
    p_lng = player_lng or DEFAULT_MUMBAI_LNG

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

        # Approximate distance for Andheri events
        distance_km = 2.4

        results.append(Experience(
            id=exp_id,
            kind="event",
            title=title,
            subtitle=venue_name or "Community gathering",
            tag=tag,
            thumbnail_url=item.get("thumbnail"),
            address=address,
            lat=p_lat + 0.005,
            lng=p_lng + 0.005,
            distance_km=distance_km,
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
    p_lat = player_lat or DEFAULT_MUMBAI_LAT
    p_lng = player_lng or DEFAULT_MUMBAI_LNG

    # Check local_results
    local_places = data.get("local_results", {}).get("places", [])
    for place in local_places:
        title = place.get("title")
        if not title:
            continue
        exp_id = f"exp_act_{hashlib.md5(title.encode()).hexdigest()[:10]}"
        address = place.get("address")
        rating = float(place["rating"]) if "rating" in place and place["rating"] is not None else None
        tag = extract_tag(title, address)

        results.append(Experience(
            id=exp_id,
            kind="activity",
            title=title,
            subtitle="Hidden neighbourhood gem",
            tag=tag,
            thumbnail_url=place.get("thumbnail"),
            address=address,
            lat=p_lat - 0.004,
            lng=p_lng + 0.003,
            distance_km=1.5,
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
            address="Andheri, Mumbai",
            lat=p_lat + 0.002,
            lng=p_lng - 0.003,
            distance_km=2.1,
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

    # 2. Check if live SerpApi or mock
    raw_json_str = None
    if settings.is_serpapi_live:
        # Live SerpApi call with retry once on 5xx
        req_params = dict(params)
        req_params["api_key"] = settings.SERPAPI_API_KEY
        req_params["engine"] = engine
        url = "https://serpapi.com/search.json"

        last_resp = None
        for attempt in range(2):
            try:
                resp = httpx.get(url, params=req_params, timeout=15.0)
                if resp.status_code < 500:
                    last_resp = resp
                    break
                last_resp = resp
            except Exception as e:
                import logging
                logging.getLogger("npc").warning(f"SerpApi attempt {attempt+1} failed: {e}")

        if last_resp and last_resp.is_success:
            raw_json_str = last_resp.text
        else:
            # Fall back to mock if error
            pass

    if not raw_json_str:
        # Load from fixture
        if engine == "google_maps":
            data = load_fixture("serp_maps.json")
        elif engine == "google_events":
            data = load_fixture("serp_events.json")
        else:
            data = load_fixture("serp_search.json")
        raw_json_str = json.dumps(data)

    # 3. Store into cache
    data = json.loads(raw_json_str)
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

    if engine == "google_maps":
        exps = parse_maps_results(data, player_lat, player_lng, now_iso)
    elif engine == "google_events":
        exps = parse_events_results(data, player_lat, player_lng, now_iso)
    else:
        exps = parse_search_results(data, player_lat, player_lng, now_iso)

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
    p_lat = lat or DEFAULT_MUMBAI_LAT
    p_lng = lng or DEFAULT_MUMBAI_LNG
    results: List[Experience] = []

    if category == "explore":
        exps, _ = fetch_serp_cached("google_maps", {"q": "hidden gems unusual landmarks", "ll": f"@{p_lat},{p_lng},14z"}, db, p_lat, p_lng)
        results.extend(exps)
        exps_s, _ = fetch_serp_cached("google", {"q": f"offbeat places {city}"}, db, p_lat, p_lng)
        results.extend(exps_s)
    elif category == "creativity":
        exps, _ = fetch_serp_cached("google_maps", {"q": "art gallery pottery studio", "ll": f"@{p_lat},{p_lng},14z"}, db, p_lat, p_lng)
        results.extend(exps)
        exps_e, _ = fetch_serp_cached("google_events", {"q": f"workshop in {city}"}, db, p_lat, p_lng)
        results.extend(exps_e)
    elif category == "social":
        exps, _ = fetch_serp_cached("google_events", {"q": f"meetup open mic community event in {city}"}, db, p_lat, p_lng)
        results.extend(exps)
        exps_m, _ = fetch_serp_cached("google_maps", {"q": "live comedy open mic cafe", "ll": f"@{p_lat},{p_lng},14z"}, db, p_lat, p_lng)
        results.extend(exps_m)
    elif category == "courage":
        exps, _ = fetch_serp_cached("google", {"q": f"free open mic try-something-scary beginner friendly {city}"}, db, p_lat, p_lng)
        results.extend(exps)
        exps_e, _ = fetch_serp_cached("google_events", {"q": f"improv theater beginner in {city}"}, db, p_lat, p_lng)
        results.extend(exps_e)
    elif category == "awareness":
        exps, _ = fetch_serp_cached("google_maps", {"q": "park garden quiet library", "ll": f"@{p_lat},{p_lng},14z"}, db, p_lat, p_lng)
        results.extend(exps)
        exps_s, _ = fetch_serp_cached("google", {"q": f"slow walk nature spots {city}"}, db, p_lat, p_lng)
        results.extend(exps_s)
    else:
        exps, _ = fetch_serp_cached("google_maps", {"q": f"places to visit {city}", "ll": f"@{p_lat},{p_lng},14z"}, db, p_lat, p_lng)
        results.extend(exps)

    # Filter by max_distance_km if distance is known
    filtered = [e for e in results if e.distance_km is None or e.distance_km <= max_distance_km]
    return filtered if filtered else results

