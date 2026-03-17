from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

SUPABASE_TABLE = "parking_data"
URL = "https://parkingavailability.charlotte.edu/decks/stream"
