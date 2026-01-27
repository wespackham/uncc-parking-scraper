import requests
import json
from src.supabase_client import supabase
from src.config import SUPABASE_TABLE, URL

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
        print(f"Network error while scraping: {e}")

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")
