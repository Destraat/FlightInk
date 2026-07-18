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
from flightink.photo_display import active_aircraft_photo, install_photo_renderer
from flightink.planespotters import AircraftPhoto, PlanespottersClient
from flightink.prediction import PassagePrediction, predict_passage, selection_score
from flightink.routes import RouteResolver
from flightink.storage import Storage

renderer_module._draw_landmark = draw_landmark
install_photo_renderer(renderer_module)
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


def _ranked_aircraft(aircraft: list[Aircraft], settings: Settings) -> list[tuple[Aircraft, PassagePrediction]]:
    ranked = [(item, predict_passage(item, settings.home_lat, settings.home_lon)) for item in aircraft]
    ranked.sort(key=lambda pair: selection_score(pair[0], pair[1]))
    return ranked


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


def _fetch_aircraft_photo(
    aircraft: Aircraft | None,
    photo_client: PlanespottersClient | None,
) -> AircraftPhoto | None:
    if aircraft is None or photo_client is None:
        return None
    try:
        photo = photo_client.latest(aircraft.registration, aircraft.hex)
        if photo and photo.image_path:
            LOGGER.info("Using cached e-ink aircraft photo: %s", photo.image_path)
        elif photo:
            LOGGER.info("Planespotters metadata found; no local e-ink image available")
        return photo
    except (requests.RequestException, ValueError, TypeError):
        LOGGER.warning("Planespotters photo lookup failed for %s", aircraft.registration or aircraft.hex, exc_info=True)
        return None


def run_once(
    settings: Settings,
    storage: Storage,
    resolver: RouteResolver,
    display: Display,
    session: requests.Session,
    photo_client: PlanespottersClient | None = None,
) -> None:
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

    ranked_live = _ranked_aircraft(aircraft_list, settings) if aircraft_list else []
    selected, prediction = ranked_live[0] if ranked_live else (None, None)
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

    route = (
        resolver.resolve(
            callsign=selected.callsign,
            icao24=selected.hex,
            registration=selected.registration,
            origin_hint=selected.origin_airport,
            destination_hint=selected.destination_airport,
        )
        if selected
        else None
    )
    if selected and route and status == "live" and not route.destination:
        for candidate, candidate_prediction in ranked_live[1:6]:
            candidate_route = resolver.resolve(
                callsign=candidate.callsign,
                icao24=candidate.hex,
                registration=candidate.registration,
                origin_hint=candidate.origin_airport,
                destination_hint=candidate.destination_airport,
            )
            if candidate_route.destination:
                selected = candidate
                prediction = candidate_prediction
                route = candidate_route
                break
    if selected and status == "live":
        storage.record_sighting(selected, route, prediction)

    photo = _fetch_aircraft_photo(selected, photo_client)
    with active_aircraft_photo(photo):
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


def _create_photo_client(
    settings: Settings,
    storage: Storage,
    session: requests.Session,
) -> PlanespottersClient | None:
    if settings.photo_provider != "planespotters":
        return None
    return PlanespottersClient(
        storage,
        user_agent=settings.planespotters_user_agent,
        timeout_seconds=settings.request_timeout_seconds,
        image_cache_enabled=settings.planespotters_image_cache_enabled,
        image_cache_dir=settings.planespotters_image_cache_dir,
        image_size=(settings.planespotters_image_width, settings.planespotters_image_height),
        session=session,
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
    session = create_session()
    resolver = RouteResolver(storage, settings, session)
    photo_client = _create_photo_client(settings, storage, session)
    display = create_display(
        settings.display_backend,
        settings.waveshare_module,
        transition_mode=settings.display_transition,
        transition_steps=settings.transition_steps,
        transition_delay_seconds=settings.transition_delay_seconds,
    )

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
            run_once(settings, storage, resolver, display, session, photo_client)
            if args.once:
                break
            time.sleep(max(1, settings.refresh_seconds - (time.monotonic() - started)))
    finally:
        display.sleep()
        session.close()


if __name__ == "__main__":
    main()
