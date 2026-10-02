import requests
from src.config import DISCORD_LABEL, DISCORD_WEBHOOK_URL


def send_discord(message: str) -> None:
    if DISCORD_LABEL:
        message = f"**[{DISCORD_LABEL}]** {message}"
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    except Exception:
        pass
