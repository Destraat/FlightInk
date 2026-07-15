from __future__ import annotations

import argparse
import logging
import signal
import time
from dataclasses import asdict

import requests

from flightink import renderer as renderer_module
from flightink.api import create_session, fetch_aircraft, fetch_local_aircraft, fetch_weather
from flightink.config import Settings
from flightink.display import Display, create_display
from flightink.landmarks import draw_landmark
from flightink.models import Aircraft, Weather
from flightink.prediction import PassagePrediction, predict_passage, selection_score
from flightink.routes import RouteResolver
from flightink.storage import Storage

# Install the richer monochrome landmark renderer without coupling the generic
# dashboard module to a specific landmark catalogue.
renderer_module._draw_landmark = draw_landmark
render_dashboard = renderer_module.render_dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger("flightink")
_STOP = False


def _stop(*_: object) -> None:
    global _STOP
    _STOP = True


def _select_aircraft(aircraft: list[Aircraft], settings: Settings) -> tuple[Aircraft | None, PassagePrediction | None]:
    if not aircraft:
        return None, None
    ranked = [(item, predict_passage(item, settings.home_lat, settings.home_lon)) for item in aircraft]
    ranked.sort(key=lambda pair: selection_score(pair[0], pair[1]))
    return ranked[0]


def _cache_live_state(storage: Storage, aircraft: Aircraft | None, weather: Weather | None) -> None:
    now = int(time.time())
    if aircraft:
        storage.set_cache("last_aircraft", {"stored_at_epoch": now, "aircraft": asdict(aircraft)})
    if weather:
        storage.set_cache("last_weather", {"stored_at_epoch": now, "weather": asdict(weather)})


def _cached_aircraft(storage: Storage, max_age_seconds: int) -> tuple[Aircraft | None, int | None]:
    value = storage.get_cache("last_aircraft", max_age_seconds)
    if not isinstance(value, dict) or not isinstance(value.get("aircraft"), dict):
        return None, None
    try:
        age = max(0, int((time.time() - int(value.get("stored_at_epoch", 0))) / 60))
        return Aircraft(**value["aircraft"]), age
    except (TypeError, ValueError):
        return None, None


def _cached_weather(storage: Storage, max_age_seconds: int) -> Weather | None:
    value = storage.get_cache("last_weather", max_age_seconds)
    if not isinstance(value, dict) or not isinstance(value.get("weather"), dict):
        return None
    try:
        return Weather(**value["weather"])
    except TypeError:
        return None


def run_once(settings: Settings, storage: Storage, resolver: RouteResolver, display: Display, session: requests.Session) -> None:
    aircraft_list: list[Aircraft] = []
    weather: Weather | None = None
    aircraft_error = False
    offline = False

    try:
        aircraft_list = fetch_aircraft(settings, session)
        LOGGER.info("Found %s suitable aircraft", len(aircraft_list))
    except requests.ConnectionError:
        offline = True
        LOGGER.exception("No network connection for aircraft data")
    except Exception:
        aircraft_error = True
        LOGGER.exception("Aircraft data retrieval failed")

    try:
        weather = fetch_weather(settings, session)
    except Exception:
        LOGGER.exception("Weather data retrieval failed")
        weather = _cached_weather(storage, settings.stale_weather_seconds)

    selected, prediction = _select_aircraft(aircraft_list, settings)
    stale_minutes: int | None = None
    status = "live"

    if selected:
        _cache_live_state(storage, selected, weather)
    elif offline or aircraft_error:
        selected, stale_minutes = _cached_aircraft(storage, settings.stale_aircraft_seconds)
        if selected:
            prediction = predict_passage(selected, settings.home_lat, settings.home_lon)
            status = "stale"
        else:
            status = "offline" if offline else "aircraft_error"
    else:
        status = "no_aircraft"

    route = resolver.resolve(selected.callsign) if selected else None
    if selected and status == "live":
        storage.record_sighting(selected, route, prediction)

    output = render_dashboard(
        selected,
        weather,
        settings.output_path,
        (settings.display_width, settings.display_height),
        route=route,
        stats=storage.stats_today(),
        prediction=prediction,
        status=status,
        stale_minutes=stale_minutes,
    )
    changed = display.show(output)
    LOGGER.info("Display %s: %s", "updated" if changed else "unchanged", output)


def _run_adsb_test(settings: Settings, session: requests.Session) -> None:
    LOGGER.info("Testing local ADS-B endpoint: %s", settings.local_adsb_url)
    aircraft = fetch_local_aircraft(settings, session)
    LOGGER.info("Local receiver returned %s usable aircraft", len(aircraft))
    for item in aircraft[:10]:
        LOGGER.info(
            "%s %s %s · %.1f km · %s ft",
            item.callsign or item.hex,
            item.registration or "registration unknown",
            item.type_code or "type unknown",
            item.distance_km,
            f"{item.altitude_ft:.0f}" if item.altitude_ft is not None else "unknown",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="FlightInk e-ink flight display")
    parser.add_argument("--once", action="store_true", help="Render once and stop")
    parser.add_argument("--preview", action="store_true", help="Force PNG preview without hardware")
    parser.add_argument("--display-test", action="store_true", help="Show a diagnostic display image")
    parser.add_argument("--adsb-test", action="store_true", help="Test the local RTL-SDR/dump1090/readsb feed")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.preview:
        settings = Settings(**{**settings.__dict__, "display_backend": "preview"})
    storage = Storage(settings.database_path, settings.cache_path)
    resolver = RouteResolver(storage)
    display = create_display(
        settings.display_backend,
        settings.waveshare_module,
        transition_mode=settings.display_transition,
        transition_steps=settings.transition_steps,
        transition_delay_seconds=settings.transition_delay_seconds,
    )
    session = create_session()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    try:
        if args.display_test:
            output = display.test()
            LOGGER.info("Display test written/shown: %s", output)
            return
        if args.adsb_test:
            _run_adsb_test(settings, session)
            return
        while not _STOP:
            started = time.monotonic()
            run_once(settings, storage, resolver, display, session)
            if args.once:
                break
            time.sleep(max(1, settings.refresh_seconds - (time.monotonic() - started)))
    finally:
        display.sleep()
        session.close()


if __name__ == "__main__":
    main()
