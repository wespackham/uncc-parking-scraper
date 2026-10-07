# UNCC Parking Scraper

Scrapes the UNC Charlotte parking availability feed every 5 minutes, stores snapshots in the `parking_data` table (PostgreSQL on the project's DigitalOcean droplet, via PostgREST at `https://parking.abrupt.app` — env vars keep the `SUPABASE_*` names), and sends Discord alerts on failures.

## Deploy

Push to `main`: `.github/workflows/deploy-scraper.yml` resets the droplet checkout to `origin/main`, installs requirements and restarts `parking-scraper.timer` (every 5 min) and `parking-scraper-report.timer` (22:00 UTC).

`.env`: `SUPABASE_URL`, `SUPABASE_KEY` (service JWT), `DISCORD_WEBHOOK_URL`, optional `DISCORD_LABEL` (prefix on Discord messages, `droplet` in production).

## Run Locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Buffering And Retry

The scraper writes each snapshot to local JSONL before attempting the database insert.

- buffered snapshots live at `logs/pending_snapshots.jsonl`
- inserts are replayed in order on every run
- replay stops on the first failed insert so ordering is preserved
- unflushed rows remain on disk for the next run
- Discord alerts fire if buffered replay fails

Inserts are idempotent upserts on `created_at` (unique index `uq_snap_created`), so a replay can never create duplicates. This prevents transient auth or network failures from dropping live parking snapshots.

## Manual Replay

Replay buffered snapshots without scraping a new one:

```bash
python main.py --flush-only
```

`MAX_BUFFER_FLUSH` controls the maximum number of buffered records replayed in one run. It defaults to `500`.
