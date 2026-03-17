from datetime import datetime, timezone, timedelta
from src.supabase_client import supabase
from src.config import SUPABASE_TABLE
from src.notifier import send_discord

EXPECTED_SNAPSHOTS = 96  # 24 hours × 4 per hour (every 15 min)


def send_daily_report():
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    result = (
        supabase.table(SUPABASE_TABLE)
        .select("id", count="exact")
        .gte("created_at", since)
        .execute()
    )

    count = result.count if result.count is not None else 0

    if count == 0:
        send_discord(f"🚨 Daily report: 0/{EXPECTED_SNAPSHOTS} snapshots collected in the last 24 hours — scraper may be down")
    elif count < EXPECTED_SNAPSHOTS:
        send_discord(f"⚠️ Daily report: {count}/{EXPECTED_SNAPSHOTS} snapshots collected in the last 24 hours")
    else:
        send_discord(f"✅ Daily report: {count}/{EXPECTED_SNAPSHOTS} snapshots collected in the last 24 hours")


if __name__ == "__main__":
    send_daily_report()
