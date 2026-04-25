from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

SUPABASE_TABLE = "parking_data"
URL = "https://parkingavailability.charlotte.edu/decks/stream"

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
BUFFER_FILE = LOGS_DIR / "pending_snapshots.jsonl"
MAX_BUFFER_FLUSH = int(os.environ.get("MAX_BUFFER_FLUSH", "500"))
