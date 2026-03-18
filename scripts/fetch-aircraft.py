#!/usr/bin/env python3
"""
Fetch live ADS-B aircraft positions from OpenSky Network for SITPULSE dashboard.
West Asia bounding box: lat 12-42°N, lon 32-63°E
Free, no API key required (anonymous access).
"""
import requests
import json
import os
from datetime import datetime, timezone

BBOX = {"lamin": 12, "lomin": 32, "lamax": 42, "lomax": 63}

OPENSKY_URL = "https://opensky-network.org/api/states/all"

# Optional credentials from env (higher rate limits)
USERNAME = os.environ.get("OPENSKY_USER", "")
PASSWORD = os.environ.get("OPENSKY_PASS", "")


def fetch_aircraft():
    auth = (USERNAME, PASSWORD) if USERNAME else None
    resp = requests.get(OPENSKY_URL, params=BBOX, auth=auth, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    states = data.get("states") or []
    # Filter to aircraft with valid position
    aircraft = []
    for s in states:
        if s[5] is None or s[6] is None:
            continue
        aircraft.append({
            "icao24": s[0],
            "callsign": (s[1] or "").strip(),
            "origin_country": s[2] or "",
            "time_position": s[3],
            "last_contact": s[4],
            "lng": s[5],
            "lat": s[6],
            "geo_altitude": s[13],
            "baro_altitude": s[7],
            "on_ground": s[8],
            "velocity": s[9],
            "heading": s[10],
            "vertical_rate": s[11],
            "squawk": s[14],
        })
    print(f"Fetched {len(aircraft)} aircraft in West Asia bounding box")
    return aircraft


def main():
    aircraft = fetch_aircraft()
    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(aircraft),
        "aircraft": aircraft,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/aircraft.json", "w") as f:
        json.dump(output, f)
    print(f"Wrote data/aircraft.json with {len(aircraft)} aircraft")


if __name__ == "__main__":
    main()
