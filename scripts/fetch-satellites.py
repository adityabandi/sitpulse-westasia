#!/usr/bin/env python3
"""
Fetch satellite TLE data from CelesTrak for SITPULSE dashboard.
Downloads orbital elements for militarily/intelligence-relevant constellations.
Outputs JSON with TLE line pairs for satellite.js SGP4 propagation.
Free, no API key required.
"""
import requests
import json
import os
from datetime import datetime, timezone

# Groups to fetch — curated for OSINT relevance
GROUPS = [
    ("military", "https://celestrak.org/NORAD/elements/gp.php?GROUP=military&FORMAT=3le"),
    ("radar", "https://celestrak.org/NORAD/elements/gp.php?GROUP=radar&FORMAT=3le"),
    ("resource", "https://celestrak.org/NORAD/elements/gp.php?GROUP=resource&FORMAT=3le"),
    ("stations", "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=3le"),
    ("starlink", "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=3le"),
]

# Highlight patterns for intelligence-relevant satellites
HIGHLIGHT_PATTERNS = [
    "ISS", "KEYHOLE", "KH-11", "LACROSSE", "ONYX", "MISTY",
    "USA ", "NROL", "CAPELLA", "ICEYE", "MAXAR", "WORLDVIEW",
    "FLOCK", "DOVE", "COSMOS", "BARS",
    "GAOFEN", "YAOGAN", "JILIN", "RADARSAT", "SENTINEL",
    "LANDSAT", "TERRA", "AQUA",
]

MAX_STARLINK = 150


def parse_3le(text):
    """Parse 3-line TLE format into list of {name, tle1, tle2} dicts."""
    lines = [l.rstrip() for l in text.strip().split("\n") if l.strip()]
    sats = []
    i = 0
    while i + 2 < len(lines):
        if lines[i + 1].startswith("1 ") and lines[i + 2].startswith("2 "):
            name = lines[i].strip()
            tle1 = lines[i + 1]
            tle2 = lines[i + 2]
            try:
                norad_id = int(tle1[2:7].strip())
            except ValueError:
                norad_id = 0
            sats.append({"name": name, "tle1": tle1, "tle2": tle2, "norad_id": norad_id})
            i += 3
        else:
            i += 1
    return sats


def fetch_group(name, url):
    """Fetch a constellation group from CelesTrak in 3LE format."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            sats = parse_3le(resp.text)
            print(f"  {name}: {len(sats)} satellites")
            return sats
        else:
            print(f"  {name}: HTTP {resp.status_code}")
            return []
    except Exception as e:
        print(f"  {name}: Error — {e}")
        return []


def main():
    print("Fetching satellite TLE data from CelesTrak...")
    all_sats = []
    seen_ids = set()

    for group_name, url in GROUPS:
        sats = fetch_group(group_name, url)

        if group_name == "starlink":
            sats = sats[:MAX_STARLINK]

        for sat in sats:
            nid = sat["norad_id"]
            if nid and nid not in seen_ids:
                seen_ids.add(nid)
                obj_name_upper = sat["name"].upper()
                all_sats.append({
                    "name": sat["name"],
                    "tle1": sat["tle1"],
                    "tle2": sat["tle2"],
                    "norad_id": nid,
                    "group": group_name,
                    "highlight": any(p in obj_name_upper for p in HIGHLIGHT_PATTERNS),
                })

    print(f"\nTotal unique satellites: {len(all_sats)}")
    highlighted = sum(1 for s in all_sats if s.get("highlight"))
    print(f"Highlighted (intelligence-relevant): {highlighted}")

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(all_sats),
        "satellites": all_sats
    }

    os.makedirs("data", exist_ok=True)
    with open("data/satellites.json", "w") as f:
        json.dump(output, f, ensure_ascii=False)
    print(f"Wrote {len(all_sats)} satellites to data/satellites.json")


if __name__ == "__main__":
    main()
