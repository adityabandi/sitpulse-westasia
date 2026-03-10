#!/usr/bin/env python3
"""
Combine all feed JSON files into a single combined.json and generate stats.
"""
import json
import os
from datetime import datetime

FEEDS = ["acled", "gdelt", "firms", "usgs", "reliefweb"]
DATA_DIR = "data"


def load_feed(name):
    path = os.path.join(DATA_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
            return data.get("events", []), data.get("fetched_at", "")
    return [], ""


def main():
    all_events = []
    feed_meta = {}

    for feed in FEEDS:
        events, fetched_at = load_feed(feed)
        all_events.extend(events)
        feed_meta[feed] = {
            "count": len(events),
            "fetched_at": fetched_at
        }

    # Sort by timestamp (newest first), handling missing timestamps
    all_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    # Generate stats
    stats = {
        "total_events": len(all_events),
        "by_source": {f: feed_meta[f]["count"] for f in FEEDS},
        "by_category": {},
        "by_country": {},
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "feed_freshness": feed_meta
    }

    for e in all_events:
        cat = e.get("category", "unknown")
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        country = e.get("country", "")
        if country:
            stats["by_country"][country] = stats["by_country"].get(country, 0) + 1

    # Write combined
    combined = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total": len(all_events),
        "events": all_events
    }

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(os.path.join(DATA_DIR, "combined.json"), "w") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    with open(os.path.join(DATA_DIR, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2)

    print(f"Combined {len(all_events)} events from {len(FEEDS)} feeds")
    print(f"Stats: {json.dumps(stats['by_source'])}")


if __name__ == "__main__":
    main()
