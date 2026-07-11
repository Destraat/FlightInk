from __future__ import annotations

import logging
import time

from flightink.api import fetch_aircraft, fetch_weather
from flightink.config import Settings
from flightink.renderer import render_dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("flightink")


def run_once(settings: Settings) -> None:
    aircraft = []
    weather = None

    try:
        aircraft = fetch_aircraft(settings)
        LOGGER.info("%s vliegtuigen gevonden binnen %.1f NM", len(aircraft), settings.radius_nm)
    except Exception:
        LOGGER.exception("Vliegtuigdata ophalen mislukt")

    try:
        weather = fetch_weather(settings)
    except Exception:
        LOGGER.exception("Weerdata ophalen mislukt")

    selected = aircraft[0] if aircraft else None
    output = render_dashboard(
        selected,
        weather,
        settings.output_path,
        (settings.display_width, settings.display_height),
    )
    LOGGER.info("Schermbeeld geschreven naar %s", output)


def main() -> None:
    settings = Settings.from_env()
    while True:
        started = time.monotonic()
        run_once(settings)
        elapsed = time.monotonic() - started
        time.sleep(max(1, settings.refresh_seconds - elapsed))


if __name__ == "__main__":
    main()
