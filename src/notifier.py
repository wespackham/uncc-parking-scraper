import requests
from src.config import DISCORD_WEBHOOK_URL


def send_discord(message: str) -> None:
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    except Exception:
        pass
