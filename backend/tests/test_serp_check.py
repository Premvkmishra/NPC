import os
import sys
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY", "").strip()

def test_serpapi():
    print("=" * 60)
    print("SERPAPI LIVE VERIFICATION TEST")
    print("=" * 60)
    print(f"Key configured: {'YES (starts with ' + SERPAPI_KEY[:6] + '...)' if SERPAPI_KEY and not SERPAPI_KEY.startswith('dummy') else 'NO'}")

    if not SERPAPI_KEY or SERPAPI_KEY.startswith("dummy"):
        print("ERROR: SerpApi key is not set or is dummy.")
        return False

    client = httpx.Client(timeout=25.0)

    # 1. Test Google Maps Engine (Searching places)
    print("\n--- Test 1: Google Maps Engine (Place Search) ---")
    maps_params = {
        "engine": "google_maps",
        "q": "art galleries in Bandra Mumbai",
        "ll": "@19.0596,72.8295,14z",
        "api_key": SERPAPI_KEY
    }
    try:
        resp = client.get("https://serpapi.com/search.json", params=maps_params)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            local_results = data.get("local_results", [])
            print(f"SUCCESS! Found {len(local_results)} places via Google Maps.")
            for i, place in enumerate(local_results[:3], 1):
                title = place.get("title")
                address = place.get("address")
                rating = place.get("rating")
                gps = place.get("gps_coordinates")
                print(f"  [{i}] {title} (Rating: {rating})")
                print(f"      Address: {address}")
                print(f"      GPS: {gps}")
        else:
            print(f"FAILED: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False

    # 2. Test Google Events Engine (Searching events)
    print("\n--- Test 2: Google Events Engine (Events Search) ---")
    events_params = {
        "engine": "google_events",
        "q": "workshops in Mumbai",
        "api_key": SERPAPI_KEY
    }
    try:
        resp = client.get("https://serpapi.com/search.json", params=events_params)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            events = data.get("events_results", [])
            print(f"SUCCESS! Found {len(events)} events via Google Events.")
            for i, event in enumerate(events[:3], 1):
                title = event.get("title")
                date = event.get("date", {}).get("when")
                venue = event.get("venue", {}).get("name")
                print(f"  [{i}] {title}")
                print(f"      When: {date} | Venue: {venue}")
        else:
            print(f"FAILED: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False

    # 3. Test Google Search Engine (Offbeat Activities Search)
    print("\n--- Test 3: Google Search Engine (Offbeat Activities) ---")
    search_params = {
        "engine": "google",
        "q": "offbeat places to visit in Mumbai",
        "location": "Mumbai, Maharashtra, India",
        "api_key": SERPAPI_KEY
    }
    try:
        resp = client.get("https://serpapi.com/search.json", params=search_params)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            organic = data.get("organic_results", [])
            print(f"SUCCESS! Found {len(organic)} organic results via Google Search.")
            for i, item in enumerate(organic[:3], 1):
                title = item.get("title")
                link = item.get("link")
                print(f"  [{i}] {title}")
                print(f"      Link: {link}")
        else:
            print(f"FAILED: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False

    print("\n" + "=" * 60)
    print("ALL SERPAPI ENGINES OPERATING PROPERLY & SEARCHING REAL DATA!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_serpapi()
    sys.exit(0 if success else 1)
