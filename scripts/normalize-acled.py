#!/usr/bin/env python3
"""
Fetch ACLED conflict events for West Asia.
Uses ACLED's new OAuth2 token authentication (as of Sep 2025).
Requires ACLED_EMAIL and ACLED_PASSWORD env vars.
Register at https://acleddata.com/register/
"""
import requests
import json
import os
from datetime import datetime, timedelta

ACLED_TOKEN_URL = "https://acleddata.com/oauth/token"
ACLED_API       = "https://acleddata.com/api/acled/read"
REGION          = 11  # Middle East


def get_oauth_token(email, password):
    """Exchange credentials for a short-lived Bearer token."""
    resp = requests.post(ACLED_TOKEN_URL, data={
        "username":   email,
        "password":   password,
        "grant_type": "password",
        "client_id":  "acled",
    }, timeout=30)
    if resp.status_code != 200:
        print(f"OAuth error {resp.status_code}: {resp.text[:300]}")
        return None
    return resp.json().get("access_token")


def fetch_acled_events(token):
    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    events = []
    try:
        params = {
            "event_date":       f"{since}|",
            "event_date_where": "BETWEEN",
            "region":           REGION,
            "limit":            500,
            "fields": (
                "event_id_cnty|event_date|event_type|sub_event_type|"
                "actor1|actor2|country|admin1|location|latitude|longitude|"
                "fatalities|notes|source|source_scale"
            ),
        }
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(ACLED_API, params=params, headers=headers, timeout=60)
        if resp.status_code == 200:
            for raw in resp.json().get("data", []):
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

                events.append({
                    "id":          f"acled-{raw.get('event_id_cnty', '')}",
                    "source":      "acled",
                    "category":    category,
                    "event_type":  etype,
                    "sub_type":    raw.get("sub_event_type", ""),
                    "title":       f"{raw.get('sub_event_type', etype)} in {raw.get('location', 'Unknown')}, {raw.get('country', '')}",
                    "description": raw.get("notes", ""),
                    "country":     raw.get("country", ""),
                    "admin1":      raw.get("admin1", ""),
                    "location":    raw.get("location", ""),
                    "lat":         float(raw["latitude"])  if raw.get("latitude")  else None,
                    "lng":         float(raw["longitude"]) if raw.get("longitude") else None,
                    "fatalities":  int(raw.get("fatalities", 0)),
                    "actor1":      raw.get("actor1", ""),
                    "actor2":      raw.get("actor2", ""),
                    "timestamp":   raw.get("event_date", ""),
                    "source_name": raw.get("source", ""),
                    "source_scale":raw.get("source_scale", ""),
                })
        else:
            print(f"ACLED API {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"Error fetching ACLED: {e}")
    return events


def main():
    email    = os.environ.get("ACLED_EMAIL")
    password = os.environ.get("ACLED_PASSWORD")

    if not email or not password:
        print("WARNING: ACLED_EMAIL or ACLED_PASSWORD not set. Writing empty dataset.")
        events = []
    else:
        print("Authenticating with ACLED OAuth...")
        token = get_oauth_token(email, password)
        if not token:
            print("Failed to get token. Writing empty dataset.")
            events = []
        else:
            print("Token obtained. Fetching events...")
            events = fetch_acled_events(token)

    print(f"Found {len(events)} events")
    os.makedirs("data", exist_ok=True)
    with open("data/acled.json", "w") as f:
        json.dump({
            "source":     "acled",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "region":     "west_asia",
            "count":      len(events),
            "events":     events,
        }, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(events)} events to data/acled.json")


if __name__ == "__main__":
    main()
