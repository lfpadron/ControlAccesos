"""Register the HTTPS webhook after configuring the bot in the server environment."""
import argparse
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.qr_delivery import DeliveryError, telegram_bot_url, telegram_request


def main() -> None:
    parser = argparse.ArgumentParser(description="Configurar webhook de Telegram para CMC")
    parser.add_argument("--url", required=True, help="https://tu-dominio/api/telegram/webhook")
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/api/telegram/webhook":
        parser.error("Usa https://tu-dominio/api/telegram/webhook sin credenciales ni parámetros.")
    settings = get_settings()
    if not telegram_bot_url():
        parser.error("Configura TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME y TELEGRAM_WEBHOOK_SECRET.")
    configure_logging(settings.log_level)
    try:
        telegram_request("setWebhook", json={
            "url": args.url, "secret_token": settings.telegram_webhook_secret,
            "allowed_updates": ["message"],
        })
    except DeliveryError as exc:
        parser.exit(1, f"{exc}\n")
    print("Webhook de Telegram configurado.")


if __name__ == "__main__":
    main()
