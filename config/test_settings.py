from config.settings import *  # noqa: F401,F403

# Speed up isolated tests. The application uses Django's default PBKDF2 hasher.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
CELERY_BROKER_URL = "memory://"
