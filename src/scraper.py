import json
from datetime import datetime, timezone

import requests

from src.config import BUFFER_FILE, MAX_BUFFER_FLUSH, SUPABASE_TABLE, URL
from src.notifier import send_discord
from src.supabase_client import supabase


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snapshot_record(snapshot: dict, created_at: str | None = None) -> dict:
    return {
        "created_at": created_at or _utc_now_iso(),
        "data": snapshot,
    }


def _load_buffered_records() -> list[dict]:
    if not BUFFER_FILE.exists():
        return []

    records = []
    for raw_line in BUFFER_FILE.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            print("Skipping malformed buffered snapshot line")
            continue
        if isinstance(record, dict) and "created_at" in record and "data" in record:
            records.append(record)
    return records


def _write_buffered_records(records: list[dict]) -> None:
    BUFFER_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        if BUFFER_FILE.exists():
            BUFFER_FILE.unlink()
        return

    tmp_path = BUFFER_FILE.with_suffix(".tmp")
    with tmp_path.open("w", encoding="ascii") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    tmp_path.replace(BUFFER_FILE)


def _buffer_snapshot(snapshot: dict, created_at: str | None = None) -> dict:
    record = _snapshot_record(snapshot, created_at)
    records = _load_buffered_records()
    records.append(record)
    _write_buffered_records(records)
    return record


def _insert_record(record: dict) -> None:
    supabase.table(SUPABASE_TABLE).insert(record).execute()


def flush_buffered_snapshots(max_records: int = MAX_BUFFER_FLUSH) -> tuple[int, int]:
    """Replay locally buffered snapshots in order.

    Returns (inserted_count, remaining_count).
    Stops at the first failed insert to preserve ordering and avoid duplicates.
    """
    records = _load_buffered_records()
    if not records:
        return 0, 0

    inserted = 0
    failed_message = None
    replay_window = records[:max_records]
    untouched_tail = records[max_records:]

    for idx, record in enumerate(replay_window):
        try:
            _insert_record(record)
            inserted += 1
        except Exception as exc:
            failed_message = exc
            remaining = replay_window[idx:] + untouched_tail
            _write_buffered_records(remaining)
            break
    else:
        _write_buffered_records(untouched_tail)
        remaining = untouched_tail

    if inserted:
        print(f"Flushed {inserted} buffered snapshot(s)")

    if failed_message is not None:
        msg = f"Scraper error: buffered retry failed — {failed_message}"
        print(msg)
        send_discord(f"⚠️ {msg}")

    return inserted, len(remaining)


def _extract_snapshot(response) -> dict | None:
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue

        json_data = line.removeprefix("data:").strip()
        parking_data = json.loads(json_data)

        snapshot = {
            lot["lotCode"]: lot["percentAvailable"]
            for lot in parking_data
            if "lotCode" in lot and "percentAvailable" in lot
        }

        if not snapshot:
            print("No data found in snapshot")
            return None

        return snapshot

    return None


def scrape_and_store():
    try:
        response = requests.get(URL, stream=True, timeout=15)
        response.raise_for_status()

        snapshot = _extract_snapshot(response)
        if not snapshot:
            return

        record = _buffer_snapshot(snapshot)
        print(f"Buffered parking snapshot locally at {record['created_at']}")

        inserted, remaining = flush_buffered_snapshots()
        if inserted:
            print(f"Inserted parking snapshot(s); {remaining} buffered snapshot(s) remaining")
        return

    except requests.RequestException as exc:
        msg = f"Scraper error: network error — {exc}"
        print(msg)
        send_discord(f"⚠️ {msg}")

    except json.JSONDecodeError as exc:
        msg = f"Scraper error: JSON decode failed — {exc}"
        print(msg)
        send_discord(f"⚠️ {msg}")

    except Exception as exc:
        msg = f"Scraper error: unexpected error — {exc}"
        print(msg)
        send_discord(f"⚠️ {msg}")
