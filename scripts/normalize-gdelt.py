#!/usr/bin/env python3
"""
Fetch GDELT events for the West Asia bounding box.
Uses GDELT 2.0 GKG (Global Knowledge Graph) API — no key required.
Falls back to GDELT Events API.
"""
import requests
import json
import os
import re
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

# Countries in our region with centroid fallback coordinates
COUNTRIES = [
    "Iraq", "Syria", "Lebanon", "Israel", "Palestine", "Yemen", "Iran",
    "Jordan", "Saudi Arabia", "Turkey", "Kuwait", "Bahrain", "Qatar",
    "United Arab Emirates", "Oman"
]

COUNTRY_CENTROIDS = {
    "Iraq": (33.22, 43.68), "Syria": (34.80, 38.99), "Lebanon": (33.85, 35.86),
    "Israel": (31.05, 34.85), "Palestine": (31.95, 35.23), "Yemen": (15.55, 48.52),
    "Iran": (32.43, 53.69), "Jordan": (30.59, 36.24), "Saudi Arabia": (23.89, 45.08),
    "Turkey": (38.96, 35.24), "Kuwait": (29.31, 47.48), "Bahrain": (26.07, 50.55),
    "Qatar": (25.35, 51.18), "United Arab Emirates": (23.42, 53.85), "Oman": (21.47, 55.98),
    "Gaza": (31.42, 34.38), "Tehran": (35.69, 51.39), "Baghdad": (33.31, 44.37),
    "Damascus": (33.51, 36.29), "Beirut": (33.89, 35.50), "Sanaa": (15.37, 44.19),
    "Amman": (31.96, 35.95), "Riyadh": (24.71, 46.68),
}

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
                    # Geocode from title — match known country/city names
                    lat = None
                    lng = None
                    title = article.get("title", "")
                    matched_country = ""
                    for name, coords in COUNTRY_CENTROIDS.items():
                        if re.search(r'\b' + re.escape(name) + r'\b', title, re.IGNORECASE):
                            lat, lng = coords
                            matched_country = name
                            break

                    # Also try the country list for the "country" field
                    if not lat:
                        for c in COUNTRIES:
                            if c.lower() in title.lower():
                                if c in COUNTRY_CENTROIDS:
                                    lat, lng = COUNTRY_CENTROIDS[c]
                                    matched_country = c
                                break

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

                    # Convert GDELT seendate (20260310T083000Z) to ISO
                    raw_date = article.get("seendate", "")
                    try:
                        if raw_date and len(raw_date) >= 14:
                            timestamp = datetime.strptime(raw_date[:14], "%Y%m%d%H%M%S").isoformat() + "Z"
                        else:
                            timestamp = raw_date
                    except Exception:
                        timestamp = raw_date

                    event = {
                        "id": f"gdelt-{hash(article.get('url', '')) & 0xFFFFFFFF}",
                        "source": "gdelt",
                        "category": category,
                        "title": title,
                        "country": matched_country,
                        "url": article.get("url", ""),
                        "source_name": article.get("domain", ""),
                        "timestamp": timestamp,
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
