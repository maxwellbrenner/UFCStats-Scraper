# UFC Stats Advanced Scraper

## Overview
A Python 3.10+ command‑line tool that harvests comprehensive UFC event, fight, fighter and per‑round statistics directly from **[UFCStats.com](http://ufcstats.com/)**.  
Captured data are exported simultaneously to:

1. **`UFCStats.csv`** – an analysis‑ready flat file.:contentReference[oaicite:0]{index=0}  
2. **MySQL database `UFCStats`** – a fully‑normalised schema created from `create_database.sql`.:contentReference[oaicite:1]{index=1}

The scraper only processes events that are not yet present in the database, allowing incremental updates.:contentReference[oaicite:2]{index=2}

---

## Key Features
- **Multi‑threaded fetching** of web pages with retry/back‑off logic for robustness.:contentReference[oaicite:3]{index=3}  
- **In‑memory fighter cache** to avoid duplicate HTTP requests.  
- **Automatic DB bootstrap** – if the database is missing, the schema script is executed on first run.:contentReference[oaicite:4]{index=4}  
- **Granular per‑round metrics** (20+ stats) for both fighters.:contentReference[oaicite:5]{index=5}  
- Works headlessly; only standard console input for DB credentials is required.:contentReference[oaicite:6]{index=6}

---

## Workflow

| Step | Action | Output |
|------|--------|--------|
| 1 | Scrape completed‑events index; skip the “upcoming” placeholder row.:contentReference[oaicite:7]{index=7} | List of event URLs |
| 2 | For each event, discover fight links and fetch fight pages in parallel.:contentReference[oaicite:8]{index=8} | Fight HTML |
| 3 | From each fight page:<br>&nbsp;&nbsp;• create `Fighter` objects (with caching)<br>&nbsp;&nbsp;• detect winner, weight‑class, title fight, etc.<br>&nbsp;&nbsp;• parse round tables into `RoundStats`. | Python objects |
| 4 | Assemble a row per fight → **`UFCStats.csv`**.:contentReference[oaicite:9]{index=9} | CSV |
| 5 | Insert events, fighters, fights, rounds and stats into MySQL with safe upserts.:contentReference[oaicite:10]{index=10} | MySQL |

---

## Data Model

### CSV Columns (excerpt)
*Event‐level* – `event_name`, `event_date`, `event_location`, `event_link`  
*Fight* – `winner`, `weight_class`, `gender`, `title_fight`, `method_of_victory`, `round_of_victory`, `time_of_victory_sec`, `referee`  
*Fighter A / B* – `*_name`, `*_height_in`, `*_reach_in`, `*_dob`, `*_link`  
*Per‑round* – prefixed `round_<n>_fighter_<a|b>_…` plus the 20 fields shown in `round_stat_fields`.:contentReference[oaicite:11]{index=11}

### MySQL Schema (simplified)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `event` | One row per UFC event | `event_id`, `name`, `date`, `location`:contentReference[oaicite:12]{index=12} |
| `fighter` | Unique fighter bios | `fighter_id`, `name`, `height_in`, `reach_in`, `dob`:contentReference[oaicite:13]{index=13} |
| `fight` | Join between event & fighters + outcome | `winner`, `weight_class`, `gender`, `title_fight`, `method_of_victory`, `round_of_victory`, `time_of_victory`:contentReference[oaicite:14]{index=14} |
| `round` | One row per round per fight | `round_id`, `fight_id`, `round_number`:contentReference[oaicite:15]{index=15} |
| `roundstats` | Per‑fighter round metrics (20+) | `knockdowns`, `takedowns_landed`, `control_time_seconds`, etc.:contentReference[oaicite:16]{index=16} |

---

## Installation

```bash
git clone https://github.com/<your‑org>/<repo>.git
cd <repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
