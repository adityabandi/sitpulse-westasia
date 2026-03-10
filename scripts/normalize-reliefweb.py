#!/usr/bin/env python3
"""
Fetch ReliefWeb humanitarian updates for West Asia.
Free API, no key required.
"""
import requests
import json
import os
from datetime import datetime

RELIEFWEB_API = "https://api.reliefweb.int/v1/reports"

# ReliefWeb country ISO3 codes for our region with centroid lat/lng
COUNTRIES = {
    "IRQ": "Iraq",
    "SYR": "Syria",
    "LBN": "Lebanon",
    "PSE": "Palestine",
    "ISR": "Israel",
    "YEM": "Yemen",
    "IRN": "Iran",
    "JOR": "Jordan",
    "SAU": "Saudi Arabia",
    "TUR": "Turkey"
}

COUNTRY_CENTROIDS = {
    "Iraq": (33.22, 43.68), "Syria": (34.80, 38.99), "Lebanon": (33.85, 35.86),
    "Israel": (31.05, 34.85), "Palestine": (31.95, 35.23), "Yemen": (15.55, 48.52),
    "Iran": (32.43, 53.69), "Jordan": (30.59, 36.24), "Saudi Arabia": (23.89, 45.08),
    "Turkey": (38.96, 35.24),
}


def fetch_reliefweb():
    events = []

    try:
        payload = {
            "appname": "sitpulse-westasia",
            "filter": {
                "operator": "AND",
                "conditions": [
                    {
                        "field": "primary_country.iso3",
                        "value": list(COUNTRIES.keys()),
                        "operator": "OR"
                    }
                ]
            },
            "sort": ["date.created:desc"],
            "limit": 50,
            "fields": {
                "include": [
                    "id", "title", "date.created", "date.original",
                    "source.name", "source.shortname",
                    "primary_country.name", "primary_country.iso3",
                    "url", "format.name", "theme.name",
                    "disaster.name", "disaster_type.name"
                ]
            }
        }

        resp = requests.post(RELIEFWEB_API, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", [])

            for item in items:
                fields = item.get("fields", {})

                # Determine category from themes
                themes = [t.get("name", "") for t in fields.get("theme", [])]
                if any(t in themes for t in ["Protection and Human Rights", "Protection/Human Rights & Humanitarian Principles"]):
                    category = "protection"
                elif any(t in themes for t in ["Health", "Epidemic"]):
                    category = "health"
                elif any(t in themes for t in ["Food and Nutrition", "Food Security"]):
                    category = "food_security"
                elif any(t in themes for t in ["Shelter and Non-Food Items", "Camp Coordination/Management"]):
                    category = "displacement"
                else:
                    category = "humanitarian"

                country_data = fields.get("primary_country", [{}])
                if isinstance(country_data, list):
                    country_data = country_data[0] if country_data else {}

                sources = fields.get("source", [])
                source_name = sources[0].get("shortname", sources[0].get("name", "")) if sources else ""

                # Geocode using country centroid
                country_name = country_data.get("name", "")
                centroid = COUNTRY_CENTROIDS.get(country_name, (None, None))

                event = {
                    "id": f"reliefweb-{item.get('id', '')}",
                    "source": "reliefweb",
                    "category": category,
                    "title": fields.get("title", ""),
                    "country": country_name,
                    "country_iso3": country_data.get("iso3", ""),
                    "source_name": source_name,
                    "url": fields.get("url", ""),
                    "timestamp": fields.get("date", {}).get("created", ""),
                    "format": [f.get("name", "") for f in fields.get("format", [])],
                    "themes": themes,
                    "disasters": [d.get("name", "") for d in fields.get("disaster", [])],
                    "lat": centroid[0],
                    "lng": centroid[1]
                }
                events.append(event)

        else:
            print(f"ReliefWeb API returned {resp.status_code}: {resp.text[:200]}")

    except Exception as e:
        print(f"Error fetching ReliefWeb: {e}")

    return events


def main():
    print("Fetching ReliefWeb updates for West Asia...")
    events = fetch_reliefweb()
    print(f"Found {len(events)} reports")

    output = {
        "source": "reliefweb",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "region": "west_asia",
        "count": len(events),
        "events": events
    }

    os.makedirs("data", exist_ok=True)
    with open("data/reliefweb.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(events)} reports to data/reliefweb.json")


if __name__ == "__main__":
    main()
