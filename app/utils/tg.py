import requests
from decouple import config

TG_BOT_TOKEN = config("TG_BOT_TOKEN")
CHAT_ID = config("TG_CHATID")


def notify_telegram(number=None, total_rows=None, duration=None, purged=0):
    if not TG_BOT_TOKEN or not CHAT_ID:
        return

    message = f"""
        <b>Gazzette Stale results updated!</b>
        <i>Total time taken: <strong>{f"{duration:.2f}"} seconds</strong></i>
        <i>Total rows in database: <strong>{total_rows}</strong></i>
        <i>Total results updated: <strong>{number}</strong></i>
        <i>Unused results purged: <strong>{purged}</strong></i>
        """
    response = requests.post(
        url=f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message, "parse_mode": "html"},
        timeout=10,
    ).json()

    print(response)
