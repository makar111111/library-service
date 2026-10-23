import requests
from django.conf import settings


class TelegramDeliveryError(Exception):
    """A retryable delivery failure with no token, URL or response body."""


def is_configured():
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)


def send_message(text):
    if not is_configured():
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise TelegramDeliveryError("Telegram rejected the notification.")
    except (requests.RequestException, ValueError):
        # Requests exceptions include the bot token in their URL. Never expose
        # their messages in a Celery traceback, log entry or API response.
        raise TelegramDeliveryError("Telegram delivery failed; retry later.") from None
    return True
