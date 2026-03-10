# SITPULSE // WEST ASIA THEATER

**Military-style OSINT command dashboard for West Asia conflict monitoring.**
Zero infrastructure. GitHub Actions for data. GitHub Pages for the dashboard.

![status](https://img.shields.io/badge/status-live-brightgreen) ![license](https://img.shields.io/badge/license-MIT-blue)

## What This Does

GitHub Actions run on a cron schedule, pulling data from free public OSINT feeds, normalizing it to JSON, and committing it to the `data/` directory. GitHub Pages serves a static dashboard that reads those JSON files and renders an interactive map + event feed.

## Data Sources

| Source | What It Covers | Update Frequency | API |
|--------|---------------|-----------------|-----|
| **ACLED** | Conflict events (battles, explosions, protests, violence against civilians) | Daily | Free (requires key) |
| **GDELT** | Global events extracted from news, geocoded | Every 15 min | Free, no key |
| **NASA FIRMS** | Satellite-detected fire/thermal hotspots (airstrike proxy) | Hourly | Free (requires key) |
| **USGS** | Earthquakes M2.5+ | Real-time | Free, no key |
| **ReliefWeb** | UN humanitarian updates | Hourly | Free, no key |

## Region Coverage

Bounding box: `24°N to 42°N, 32°E to 63°E`

Covers: Iraq, Syria, Lebanon, Israel/Palestine, Yemen, Iran, Jordan, Saudi Arabia (northern), Turkey (southeastern), Kuwait, Bahrain, Qatar, UAE, Oman.

## Setup

### 1. Fork this repo

### 2. Set GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

- `ACLED_API_KEY` — Get free at https://acleddata.com/
- `ACLED_EMAIL` — Your ACLED account email
- `FIRMS_MAP_KEY` — Get free at https://firms.modaps.eosdis.nasa.gov/api/area/

### 3. Enable GitHub Pages

Go to **Settings → Pages** → Source: **GitHub Actions** (not "Deploy from a branch")

### 4. Enable Actions

The workflows will start running on schedule. You can also trigger them manually from the Actions tab.

## Repo Structure

```
.github/workflows/     # Cron-triggered data fetchers
  fetch-acled.yml
  fetch-gdelt.yml
  fetch-firms.yml
  fetch-usgs.yml
  fetch-reliefweb.yml
scripts/               # Data normalization scripts
  normalize-acled.py
  normalize-gdelt.py
  normalize-firms.py
  normalize-usgs.py
  normalize-reliefweb.py
data/                  # Committed JSON (auto-updated by Actions)
  acled.json
  gdelt.json
  firms.json
  usgs.json
  reliefweb.json
  combined.json
docs/                  # Static dashboard (GitHub Pages)
  index.html
```

## Cost

- GitHub Actions free tier: 2,000 min/month (free) or 3,000 min/month (Pro, $4/mo)
- All data sources: Free
- Hosting: Free (GitHub Pages)
- **Total: $0–$4/month**

## Monetization (Planned)

- **Free**: Dashboard + last 24h of data (this repo)
- **Paid ($10-20/mo)**: Daily AI briefing email, custom alerts, 30-day history, API access
- **Org ($50-100/mo)**: Weekly sitreps, Slack integration, raw data export

## License

MIT — do whatever you want with it.
