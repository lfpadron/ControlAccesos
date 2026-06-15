from __future__ import annotations

import logging
import signal
import time

from redis import Redis

from app.core.config import get_settings
from app.core.logging import configure_logging

running = True


def stop_worker(_signum: int, _frame: object) -> None:
    global running
    running = False


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    redis_client = Redis.from_url(settings.redis_url, socket_timeout=5)

    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)

    logger.info("worker_started")
    while running:
        redis_client.ping()
        logger.info("worker_heartbeat")
        time.sleep(30)
    logger.info("worker_stopped")


if __name__ == "__main__":
    main()
