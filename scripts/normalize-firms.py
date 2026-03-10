#!/usr/bin/env python3
"""
Fetch NASA FIRMS (Fire Information for Resource Management System) hotspots.
Satellite-detected thermal anomalies — useful as airstrike/artillery proxy.
Requires FIRMS_MAP_KEY env var. Free at https://firms.modaps.eosdis.nasa.gov/api/area/
"""
import requests
import json
import os
from datetime import datetime

# West Asia bounding box
BBOX = "34,12,62,42"  # west,south,east,north — excludes Horn of Africa

# FIRMS API endpoints
FIRMS_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def fetch_firms_hotspots():
    map_key = os.environ.get("FIRMS_MAP_KEY")

    if not map_key:
        print("WARNING: FIRMS_MAP_KEY not set. Writing empty dataset.")
        return []

    events = []

    # Fetch from VIIRS SNPP (best resolution)
    sources = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT"]

    for source in sources:
        try:
            url = f"{FIRMS_API}/{map_key}/{source}/{BBOX}/1"
            resp = requests.get(url, timeout=60)

            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                if len(lines) < 2:
                    continue

                headers = lines[0].split(",")
                for line in lines[1:]:
                    cols = line.split(",")
                    if len(cols) < len(headers):
                        continue

                    row = dict(zip(headers, cols))

                    lat = float(row.get("latitude", 0))
                    lng = float(row.get("longitude", 0))
                    brightness = float(row.get("bright_ti4", 0) or row.get("brightness", 0))
                    confidence = row.get("confidence", "")
                    frp = float(row.get("frp", 0) or 0)  # Fire Radiative Power

                    # Higher brightness + FRP more likely to be explosions vs wildfires
                    if brightness > 400 or frp > 50:
                        intensity = "high"
                    elif brightness > 350 or frp > 20:
                        intensity = "medium"
                    else:
                        intensity = "low"

                    acq_date = row.get("acq_date", "")
                    acq_time = row.get("acq_time", "0000").strip()

                    # Build ISO timestamp, handling malformed acq_time
                    try:
                        t = acq_time.zfill(4)  # Pad to 4 digits
                        timestamp = f"{acq_date}T{t[:2]}:{t[2:4]}:00Z"
                    except Exception:
                        timestamp = acq_date

                    event = {
                        "id": f"firms-{source}-{lat}-{lng}-{acq_date}-{acq_time}",
                        "source": "firms",
                        "category": "thermal_anomaly",
                        "title": f"Thermal hotspot ({intensity} intensity)",
                        "lat": lat,
                        "lng": lng,
                        "brightness": brightness,
                        "frp": frp,
                        "confidence": confidence,
                        "intensity": intensity,
                        "satellite": source,
                        "timestamp": timestamp,
                        "daynight": row.get("daynight", "")
                    }
                    events.append(event)

            else:
                print(f"FIRMS {source} returned {resp.status_code}")

        except Exception as e:
            print(f"Error fetching FIRMS {source}: {e}")

    return events


def main():
    print("Fetching NASA FIRMS hotspots for West Asia...")
    events = fetch_firms_hotspots()
    print(f"Found {len(events)} hotspots")

    output = {
        "source": "firms",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "region": "west_asia",
        "count": len(events),
        "events": events
    }

    os.makedirs("data", exist_ok=True)
    with open("data/firms.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(events)} hotspots to data/firms.json")


if __name__ == "__main__":
    main()
