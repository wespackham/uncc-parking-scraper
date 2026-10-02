# UNCC Parking Scraper

Scrapes the UNC Charlotte parking availability feed, stores snapshots in Supabase, and sends Discord alerts on failures.

## Run Locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Buffering And Retry

The scraper now writes each snapshot to local JSONL before attempting any Supabase insert.

- buffered snapshots live at `logs/pending_snapshots.jsonl`
- inserts are replayed in order on every run
- replay stops on the first failed insert so ordering is preserved
- unflushed rows remain on disk for the next run
- Discord alerts fire if buffered replay fails

This prevents transient Supabase auth or network failures from dropping live parking snapshots.

## Manual Replay

Replay buffered snapshots without scraping a new one:

```bash
python main.py --flush-only
```

`MAX_BUFFER_FLUSH` controls the maximum number of buffered records replayed in one run. It defaults to `500`.
