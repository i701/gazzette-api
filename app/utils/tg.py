from decouple import config
import requests

TG_BOT_TOKEN = config("TG_BOT_TOKEN")
CHAT_ID = config("TG_CHATID")


def notify_telegram(number=None):
    # message = (
    #     """
    #         Stale results updated
    #         Date: **{0}**
    #         Total: **{1}** Results.
    #         """.format(
    #         today,
    #         number,
    #     ),
    # )
    message = f"""
        <b>Gazzette Stale results updated!</b>
        <i>Total results updated: <strong>{number}</strong></i>
        """
    response = requests.post(
        url="https://api.telegram.org/bot{0}/sendMessage".format(TG_BOT_TOKEN),
        data={"chat_id": CHAT_ID, "text": message, "parse_mode": "html"},
    ).json()

    print(response)
