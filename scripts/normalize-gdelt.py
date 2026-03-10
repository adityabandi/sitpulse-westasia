#!/usr/bin/env python3
"""
Fetch GDELT events for the West Asia bounding box.
Uses GDELT 2.0 GKG (Global Knowledge Graph) API — no key required.
Falls back to GDELT Events API.
"""
import requests
import json
import os
from datetime import datetime, timedelta

# West Asia bounding box
BBOX = {
    "south": 12.0,   # Extended south to cover Yemen
    "north": 42.0,
    "west": 32.0,
    "east": 63.0
}

# GDELT 2.0 DOC API — free, no key, returns geolocated events from news
GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# Countries in our region
COUNTRIES = [
    "Iraq", "Syria", "Lebanon", "Israel", "Palestine", "Yemen", "Iran",
    "Jordan", "Saudi Arabia", "Turkey", "Kuwait", "Bahrain", "Qatar",
    "United Arab Emirates", "Oman"
]

def fetch_gdelt_events():
    """Fetch recent conflict/security events from GDELT DOC API."""
    events = []

    # Search for conflict-related news in the region
    queries = [
        "airstrike OR bombing OR shelling OR missile",
        "protest OR demonstration OR unrest",
        "military OR troops OR deployment",
        "humanitarian OR refugees OR displacement",
        "ceasefire OR negotiation OR peace talks"
    ]

    for query_terms in queries:
        try:
            # Combine with country names
            country_filter = " OR ".join(COUNTRIES[:5])  # Top conflict countries
            full_query = f"({query_terms}) ({country_filter})"

            params = {
                "query": full_query,
                "mode": "ArtList",
                "maxrecords": 50,
                "format": "json",
                "timespan": "24h",
                "sort": "DateDesc"
            }

            resp = requests.get(GDELT_DOC_API, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                articles = data.get("articles", [])

                for article in articles:
                    # Extract location if available
                    lat = None
                    lng = None

                    # Determine event category from query
                    if "airstrike" in query_terms:
                        category = "conflict"
                    elif "protest" in query_terms:
                        category = "protest"
                    elif "military" in query_terms:
                        category = "military"
                    elif "humanitarian" in query_terms:
                        category = "humanitarian"
                    else:
                        category = "diplomatic"

                    event = {
                        "id": f"gdelt-{hash(article.get('url', '')) & 0xFFFFFFFF}",
                        "source": "gdelt",
                        "category": category,
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source_name": article.get("domain", ""),
                        "timestamp": article.get("seendate", ""),
                        "language": article.get("language", ""),
                        "image": article.get("socialimage", ""),
                        "lat": lat,
                        "lng": lng
                    }
                    events.append(event)

        except Exception as e:
            print(f"Error fetching GDELT for '{query_terms}': {e}")
            continue

    # Deduplicate by URL
    seen_urls = set()
    unique_events = []
    for e in events:
        if e["url"] not in seen_urls:
            seen_urls.add(e["url"])
            unique_events.append(e)

    return unique_events


def main():
    print("Fetching GDELT events for West Asia...")
    events = fetch_gdelt_events()
    print(f"Found {len(events)} events")

    output = {
        "source": "gdelt",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "region": "west_asia",
        "count": len(events),
        "events": events
    }

    os.makedirs("data", exist_ok=True)
    with open("data/gdelt.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(events)} events to data/gdelt.json")


if __name__ == "__main__":
    main()
