import requests
import json
from src.supabase_client import supabase
from src.config import SUPABASE_TABLE, URL
from src.notifier import send_discord

def scrape_and_store():
    try:
        response = requests.get(URL, stream=True, timeout=15)
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            if line.startswith("data:"):
                json_data = line.removeprefix("data:").strip()
                parking_data = json.loads(json_data)

                # Convert to {lotCode: percentAvailable}
                snapshot = {
                    lot["lotCode"]: lot["percentAvailable"]
                    for lot in parking_data
                    if "lotCode" in lot and "percentAvailable" in lot
                }

                if not snapshot:
                    print("No data found in snapshot")
                    return

                supabase.table(SUPABASE_TABLE).insert({
                    "data": snapshot
                }).execute()

                print("Inserted parking snapshot")
                return

    except requests.RequestException as e:
        msg = f"Scraper error: network error — {e}"
        print(msg)
        send_discord(f"⚠️ {msg}")

    except json.JSONDecodeError as e:
        msg = f"Scraper error: JSON decode failed — {e}"
        print(msg)
        send_discord(f"⚠️ {msg}")

    except Exception as e:
        msg = f"Scraper error: unexpected error — {e}"
        print(msg)
        send_discord(f"⚠️ {msg}")

#comment to test ci/cd