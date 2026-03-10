#!/usr/bin/env python3
"""
Fetch USGS earthquake data for West Asia.
Free, no API key required.
"""
import requests
import json
import os
from datetime import datetime, timedelta

# USGS Earthquake API
USGS_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# West Asia bounding box
BBOX = {
    "minlatitude": 12,
    "maxlatitude": 42,
    "minlongitude": 32,
    "maxlongitude": 63
}


def fetch_usgs_events():
    events = []

    try:
        params = {
            "format": "geojson",
            "starttime": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "minmagnitude": 2.5,
            **BBOX,
            "limit": 200,
            "orderby": "time"
        }

        resp = requests.get(USGS_API, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])

            for f in features:
                props = f.get("properties", {})
                coords = f.get("geometry", {}).get("coordinates", [0, 0, 0])

                mag = props.get("mag", 0)
                if mag >= 5.0:
                    severity = "major"
                elif mag >= 4.0:
                    severity = "moderate"
                else:
                    severity = "minor"

                # Convert epoch ms to ISO
                time_ms = props.get("time", 0)
                timestamp = datetime.utcfromtimestamp(time_ms / 1000).isoformat() + "Z" if time_ms else ""

                event = {
                    "id": f"usgs-{f.get('id', '')}",
                    "source": "usgs",
                    "category": "earthquake",
                    "title": props.get("title", f"M{mag} Earthquake"),
                    "place": props.get("place", ""),
                    "magnitude": mag,
                    "depth_km": coords[2] if len(coords) > 2 else None,
                    "severity": severity,
                    "lat": coords[1],
                    "lng": coords[0],
                    "timestamp": timestamp,
                    "url": props.get("url", ""),
                    "felt": props.get("felt"),
                    "tsunami": props.get("tsunami", 0),
                    "alert": props.get("alert")
                }
                events.append(event)

        else:
            print(f"USGS API returned {resp.status_code}")

    except Exception as e:
        print(f"Error fetching USGS: {e}")

    return events


def main():
    print("Fetching USGS earthquakes for West Asia...")
    events = fetch_usgs_events()
    print(f"Found {len(events)} earthquakes")

    output = {
        "source": "usgs",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "region": "west_asia",
        "count": len(events),
        "events": events
    }

    os.makedirs("data", exist_ok=True)
    with open("data/usgs.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(events)} earthquakes to data/usgs.json")


if __name__ == "__main__":
    main()
