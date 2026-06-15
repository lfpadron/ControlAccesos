from __future__ import annotations

import logging
import time


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Access Manager Print Agent placeholder iniciado.")
    while True:
        logging.info("Print Agent heartbeat. Impresión real pendiente de implementar.")
        time.sleep(60)


if __name__ == "__main__":
    main()
