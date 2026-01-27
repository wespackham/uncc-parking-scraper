from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

SUPABASE_TABLE = "parking data"
URL = "https://parkingavailability.charlotte.edu/decks/stream"
