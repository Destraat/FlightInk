from __future__ import annotations

import argparse
import logging
import signal
import time

from flightink.api import create_session, fetch_aircraft, fetch_weather
from flightink.config import Settings
from flightink.display import create_display
from flightink.renderer import render_dashboard
from flightink.routes import RouteResolver
from flightink.storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger("flightink")
_STOP = False


def _stop(*_: object) -> None:
    global _STOP
    _STOP = True


def run_once(settings: Settings, storage: Storage, resolver: RouteResolver, display: object) -> None:
    session = create_session()
    aircraft = []
    weather = None
    try:
        aircraft = fetch_aircraft(settings, session)
        LOGGER.info("%s vliegtuigen gevonden", len(aircraft))
    except Exception:
        LOGGER.exception("Vliegtuigdata ophalen mislukt")
    try:
        weather = fetch_weather(settings, session)
    except Exception:
        LOGGER.exception("Weerdata ophalen mislukt")

    selected = aircraft[0] if aircraft else None
    route = resolver.resolve(selected.callsign) if selected else None
    if selected:
        storage.record_sighting(selected, route)
    output = render_dashboard(
        selected,
        weather,
        settings.output_path,
        (settings.display_width, settings.display_height),
        route=route,
        stats=storage.stats_today(),
    )
    display.show(output)
    LOGGER.info("Scherm bijgewerkt: %s", output)


def main() -> None:
    parser = argparse.ArgumentParser(description="FlightInk e-ink flight display")
    parser.add_argument("--once", action="store_true", help="Render één keer en stop")
    parser.add_argument("--preview", action="store_true", help="Forceer PNG-preview zonder hardware")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.preview:
        settings = Settings(**{**settings.__dict__, "display_backend": "preview"})
    storage = Storage(settings.database_path, settings.cache_path)
    resolver = RouteResolver(storage)
    display = create_display(settings.display_backend, settings.waveshare_module)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    try:
        while not _STOP:
            started = time.monotonic()
            run_once(settings, storage, resolver, display)
            if args.once:
                break
            time.sleep(max(1, settings.refresh_seconds - (time.monotonic() - started)))
    finally:
        display.sleep()


if __name__ == "__main__":
    main()
