#!/usr/bin/env python3
"""
Fetch ACLED conflict events for West Asia.
Requires ACLED_API_KEY and ACLED_EMAIL env vars.
Free API key at https://acleddata.com/
"""
import requests
import json
import os
from datetime import datetime, timedelta

ACLED_API = "https://api.acleddata.com/acled/read"

# West Asia region codes in ACLED
REGION = 11  # Middle East

# Also fetch by specific countries to ensure coverage
COUNTRIES = [
    "Iraq", "Syria", "Lebanon", "Israel", "Palestine", "Yemen", "Iran",
    "Jordan", "Saudi Arabia", "Turkey", "Kuwait", "Bahrain", "Qatar",
    "United Arab Emirates", "Oman"
]


def fetch_acled_events():
    api_key = os.environ.get("ACLED_API_KEY")
    email = os.environ.get("ACLED_EMAIL")

    if not api_key or not email:
        print("WARNING: ACLED_API_KEY or ACLED_EMAIL not set. Writing empty dataset.")
        return []

    # Fetch last 7 days
    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    events = []
    try:
        params = {
            "key": api_key,
            "email": email,
            "event_date": f"{since}|",
            "event_date_where": "BETWEEN",
            "region": REGION,
            "limit": 500,
            "fields": "event_id_cnty|event_date|event_type|sub_event_type|actor1|actor2|country|admin1|admin2|location|latitude|longitude|fatalities|notes|source|source_scale"
        }

        resp = requests.get(ACLED_API, params=params, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            raw_events = data.get("data", [])

            for raw in raw_events:
                # Map ACLED event types to our categories
                etype = raw.get("event_type", "")
                if etype in ("Battles", "Explosions/Remote violence"):
                    category = "conflict"
                elif etype in ("Protests", "Riots"):
                    category = "protest"
                elif etype == "Violence against civilians":
                    category = "civilian_harm"
                elif etype == "Strategic developments":
                    category = "military"
                else:
                    category = "other"

                event = {
                    "id": f"acled-{raw.get('event_id_cnty', '')}",
                    "source": "acled",
                    "category": category,
                    "event_type": etype,
                    "sub_type": raw.get("sub_event_type", ""),
                    "title": f"{raw.get('sub_event_type', etype)} in {raw.get('location', 'Unknown')}, {raw.get('country', '')}",
                    "description": raw.get("notes", ""),
                    "country": raw.get("country", ""),
                    "admin1": raw.get("admin1", ""),
                    "location": raw.get("location", ""),
                    "lat": float(raw["latitude"]) if raw.get("latitude") else None,
                    "lng": float(raw["longitude"]) if raw.get("longitude") else None,
                    "fatalities": int(raw.get("fatalities", 0)),
                    "actor1": raw.get("actor1", ""),
                    "actor2": raw.get("actor2", ""),
                    "timestamp": raw.get("event_date", ""),
                    "source_name": raw.get("source", ""),
                    "source_scale": raw.get("source_scale", "")
                }
                events.append(event)

        else:
            print(f"ACLED API returned {resp.status_code}: {resp.text[:200]}")

    except Exception as e:
        print(f"Error fetching ACLED: {e}")

    return events


def main():
    print("Fetching ACLED conflict events for West Asia...")
    events = fetch_acled_events()
    print(f"Found {len(events)} events")

    output = {
        "source": "acled",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "region": "west_asia",
        "count": len(events),
        "events": events
    }

    os.makedirs("data", exist_ok=True)
    with open("data/acled.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(events)} events to data/acled.json")


if __name__ == "__main__":
    main()
