#!/usr/bin/env python3
"""
Fetch satellite TLE data from CelesTrak for SITPULSE dashboard.
Downloads orbital elements for militarily/intelligence-relevant constellations.
Enriches with country-of-origin from SATCAT catalog.
Outputs JSON with TLE line pairs for satellite.js SGP4 propagation.
Free, no API key required.
"""
import requests
import json
import os
import time
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

# CelesTrak SATCAT owner codes → (ISO2, country name, flag emoji)
OWNER_MAP = {
    "US": ("US", "United States", "\U0001F1FA\U0001F1F8"),
    "CIS": ("RU", "Russia (CIS)", "\U0001F1F7\U0001F1FA"),
    "PRC": ("CN", "China", "\U0001F1E8\U0001F1F3"),
    "UK": ("GB", "United Kingdom", "\U0001F1EC\U0001F1E7"),
    "FR": ("FR", "France", "\U0001F1EB\U0001F1F7"),
    "IN": ("IN", "India", "\U0001F1EE\U0001F1F3"),
    "ISRA": ("IL", "Israel", "\U0001F1EE\U0001F1F1"),
    "JPN": ("JP", "Japan", "\U0001F1EF\U0001F1F5"),
    "ESA": ("EU", "ESA (Europe)", "\U0001F1EA\U0001F1FA"),
    "GER": ("DE", "Germany", "\U0001F1E9\U0001F1EA"),
    "IT": ("IT", "Italy", "\U0001F1EE\U0001F1F9"),
    "CA": ("CA", "Canada", "\U0001F1E8\U0001F1E6"),
    "SKOR": ("KR", "South Korea", "\U0001F1F0\U0001F1F7"),
    "NKOR": ("KP", "North Korea", "\U0001F1F0\U0001F1F5"),
    "IRAN": ("IR", "Iran", "\U0001F1EE\U0001F1F7"),
    "UAE": ("AE", "UAE", "\U0001F1E6\U0001F1EA"),
    "SAU": ("SA", "Saudi Arabia", "\U0001F1F8\U0001F1E6"),
    "TUR": ("TR", "Turkey", "\U0001F1F9\U0001F1F7"),
    "EGYP": ("EG", "Egypt", "\U0001F1EA\U0001F1EC"),
    "BRAZ": ("BR", "Brazil", "\U0001F1E7\U0001F1F7"),
    "AUS": ("AU", "Australia", "\U0001F1E6\U0001F1FA"),
    "INDO": ("ID", "Indonesia", "\U0001F1EE\U0001F1E9"),
    "SPN": ("ES", "Spain", "\U0001F1EA\U0001F1F8"),
    "ARGN": ("AR", "Argentina", "\U0001F1E6\U0001F1F7"),
    "LUXE": ("LU", "Luxembourg", "\U0001F1F1\U0001F1FA"),
    "SWED": ("SE", "Sweden", "\U0001F1F8\U0001F1EA"),
    "NOR": ("NO", "Norway", "\U0001F1F3\U0001F1F4"),
    "TAIW": ("TW", "Taiwan", "\U0001F1F9\U0001F1FC"),
    "PAKI": ("PK", "Pakistan", "\U0001F1F5\U0001F1F0"),
    "O/S": ("XX", "Multinational", "\U0001F310"),
    "ORB": ("XX", "Multinational", "\U0001F310"),
    "AC": ("XX", "AsiaSat", "\U0001F310"),
    "SES": ("LU", "SES (Luxembourg)", "\U0001F1F1\U0001F1FA"),
    "EUME": ("EU", "EUMETSAT", "\U0001F1EA\U0001F1FA"),
    "EUTE": ("EU", "Eutelsat", "\U0001F1EA\U0001F1FA"),
    "GLOB": ("XX", "Globalstar", "\U0001F310"),
    "IRID": ("US", "Iridium (US)", "\U0001F1FA\U0001F1F8"),
    "IM": ("XX", "Inmarsat", "\U0001F310"),
    "ITSO": ("XX", "Intelsat", "\U0001F310"),
    "NATO": ("XX", "NATO", "\U0001F310"),
    "NIG": ("NG", "Nigeria", "\U0001F1F3\U0001F1EC"),
    "SEAL": ("XX", "Sea Launch", "\U0001F310"),
    "SS": ("XX", "Spacecom", "\U0001F310"),
    "ALG": ("DZ", "Algeria", "\U0001F1E9\U0001F1FF"),
    "AZER": ("AZ", "Azerbaijan", "\U0001F1E6\U0001F1FF"),
    "CHBZ": ("XX", "China/Brazil", "\U0001F310"),
    "IND": ("IN", "India", "\U0001F1EE\U0001F1F3"),
    "ISS": ("XX", "ISS (Multinational)", "\U0001F310"),
    "KAZ": ("KZ", "Kazakhstan", "\U0001F1F0\U0001F1FF"),
    "MEX": ("MX", "Mexico", "\U0001F1F2\U0001F1FD"),
    "ROC": ("TW", "Taiwan", "\U0001F1F9\U0001F1FC"),
    "SAUD": ("SA", "Saudi Arabia", "\U0001F1F8\U0001F1E6"),
    "SING": ("SG", "Singapore", "\U0001F1F8\U0001F1EC"),
    "SVN": ("SI", "Slovenia", "\U0001F1F8\U0001F1EE"),
    "TBD": ("XX", "Unknown", "\U0001F310"),
    "THAI": ("TH", "Thailand", "\U0001F1F9\U0001F1ED"),
    "TURK": ("TR", "Turkey", "\U0001F1F9\U0001F1F7"),
    "VTNM": ("VN", "Vietnam", "\U0001F1FB\U0001F1F3"),
}


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


def fetch_satcat_owners():
    """Fetch SATCAT catalog from CelesTrak to get satellite owner/country info."""
    print("Fetching SATCAT catalog for owner data...")
    owner_map = {}
    # Query per group since SATCAT API requires a query parameter
    satcat_groups = ["military", "radar", "resource", "stations", "starlink"]
    for grp in satcat_groups:
        try:
            url = f"https://celestrak.org/satcat/records.php?GROUP={grp}&FORMAT=json"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                records = resp.json()
                for rec in records:
                    norad = rec.get("NORAD_CAT_ID")
                    owner = rec.get("OWNER", "").strip()
                    if norad and owner:
                        owner_map[int(norad)] = owner
                print(f"  SATCAT {grp}: {len(records)} records")
            else:
                print(f"  SATCAT {grp}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  SATCAT {grp}: Error — {e}")
    print(f"  SATCAT total: {len(owner_map)} records with owner data")
    return owner_map


def main():
    print("Fetching satellite TLE data from CelesTrak...")
    all_sats = []
    seen_ids = set()

    # Fetch SATCAT owner data first
    satcat_owners = fetch_satcat_owners()

    for idx, (group_name, url) in enumerate(GROUPS):
        if idx > 0:
            time.sleep(2)  # Avoid CelesTrak rate limiting
        sats = fetch_group(group_name, url)

        if group_name == "starlink":
            sats = sats[:MAX_STARLINK]

        for sat in sats:
            nid = sat["norad_id"]
            if nid and nid not in seen_ids:
                seen_ids.add(nid)
                obj_name_upper = sat["name"].upper()

                # Look up owner from SATCAT
                owner_code = satcat_owners.get(nid, "")
                owner_info = OWNER_MAP.get(owner_code, None)

                entry = {
                    "name": sat["name"],
                    "tle1": sat["tle1"],
                    "tle2": sat["tle2"],
                    "norad_id": nid,
                    "group": group_name,
                    "highlight": any(p in obj_name_upper for p in HIGHLIGHT_PATTERNS),
                }

                if owner_info:
                    entry["owner_code"] = owner_info[0]
                    entry["owner_country"] = owner_info[1]
                    entry["owner_flag"] = owner_info[2]
                elif owner_code:
                    entry["owner_code"] = owner_code
                    entry["owner_country"] = owner_code
                    entry["owner_flag"] = ""

                all_sats.append(entry)

    print(f"\nTotal unique satellites: {len(all_sats)}")
    highlighted = sum(1 for s in all_sats if s.get("highlight"))
    with_owner = sum(1 for s in all_sats if s.get("owner_country"))
    print(f"Highlighted (intelligence-relevant): {highlighted}")
    print(f"With country-of-origin: {with_owner}")

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
