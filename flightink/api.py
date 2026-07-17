from __future__ import annotations

import logging
import math
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Settings
from .models import Aircraft, Weather

LOGGER = logging.getLogger(__name__)


def create_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": "FlightInk/1.0 (+https://github.com/Destraat/FlightInk)"})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=Retry(total=0)))
    return session


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def fetch_aircraft(settings: Settings, session: requests.Session | None = None) -> list[Aircraft]:
    """Fetch aircraft from a local USB ADS-B receiver, the internet, or both.

    `local` reads dump1090/readsb JSON generated from an RTL-SDR USB dongle.
    `remote` uses Airplanes.live.
    `hybrid` prefers the local receiver and falls back to Airplanes.live when
    the local feed is unavailable or contains no usable aircraft.
    """
    client = session or create_session()
    if settings.aircraft_source in {"local", "hybrid"}:
        try:
            local = fetch_local_aircraft(settings, client)
            if local or settings.aircraft_source == "local":
                LOGGER.info("Using local ADS-B receiver: %s aircraft", len(local))
                return local
            LOGGER.info("Local ADS-B receiver returned no usable aircraft; using remote fallback")
        except (requests.RequestException, ValueError, TypeError):
            if settings.aircraft_source == "local":
                raise
            LOGGER.warning("Local ADS-B receiver unavailable; using remote fallback", exc_info=True)

    return fetch_remote_aircraft(settings, client)


def fetch_local_aircraft(settings: Settings, session: requests.Session | None = None) -> list[Aircraft]:
    client = session or create_session()
    response = client.get(settings.local_adsb_url, timeout=settings.local_adsb_timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    raw_aircraft = payload.get("aircraft", payload.get("ac", []))
    if not isinstance(raw_aircraft, list):
        raise ValueError("Local ADS-B response does not contain an aircraft list")
    return _parse_aircraft(raw_aircraft, settings)


def fetch_remote_aircraft(settings: Settings, session: requests.Session | None = None) -> list[Aircraft]:
    client = session or create_session()
    url = f"{settings.airplanes_api_base}/point/{settings.home_lat}/{settings.home_lon}/{settings.radius_nm}"
    response = client.get(url, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    raw_aircraft = payload.get("ac", [])
    if not isinstance(raw_aircraft, list):
        raise ValueError("Remote ADS-B response does not contain an aircraft list")
    return _parse_aircraft(raw_aircraft, settings)


def _parse_aircraft(raw_aircraft: list[dict[str, Any]], settings: Settings) -> list[Aircraft]:
    result: list[Aircraft] = []
    for raw in raw_aircraft:
        if not isinstance(raw, dict):
            continue
        lat = _to_float(raw.get("lat"))
        lon = _to_float(raw.get("lon"))
        if lat is None or lon is None:
            continue
        distance = haversine_km(settings.home_lat, settings.home_lon, lat, lon)
        altitude = _altitude(raw)
        if altitude is not None and altitude < settings.minimum_altitude_ft:
            continue
        if distance > settings.maximum_distance_km:
            continue
        origin_airport, destination_airport = _route_hints(raw)
        result.append(
            Aircraft(
                hex=str(raw.get("hex", raw.get("icao", ""))).strip().lower(),
                callsign=str(raw.get("flight", raw.get("callsign", ""))).strip().upper(),
                registration=str(raw.get("r", raw.get("registration", ""))).strip().upper(),
                type_code=str(raw.get("t", raw.get("type", ""))).strip().upper(),
                latitude=lat,
                longitude=lon,
                altitude_ft=altitude,
                speed_knots=_to_float(raw.get("gs", raw.get("speed"))),
                track=_to_float(raw.get("track", raw.get("heading"))),
                distance_km=distance,
                origin_airport=origin_airport,
                destination_airport=destination_airport,
            )
        )
    return sorted(result, key=_selection_score)


def fetch_weather(settings: Settings, session: requests.Session | None = None) -> Weather:
    client = session or create_session()
    params = {
        "latitude": settings.home_lat,
        "longitude": settings.home_lon,
        "current": "temperature_2m,cloud_cover,weather_code,wind_speed_10m,wind_direction_10m",
        "timezone": "auto",
    }
    response = client.get(settings.weather_api_base, params=params, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    current = response.json().get("current", {})
    return Weather(
        temperature_c=_to_float(current.get("temperature_2m")),
        cloud_cover=_to_int(current.get("cloud_cover")),
        weather_code=_to_int(current.get("weather_code")),
        wind_speed_kmh=_to_float(current.get("wind_speed_10m")),
        wind_direction=_to_float(current.get("wind_direction_10m")),
    )


def _altitude(raw: dict[str, Any]) -> float | None:
    value = raw.get("alt_baro", raw.get("alt_geom", raw.get("altitude")))
    if isinstance(value, str) and value.lower() == "ground":
        return 0.0
    return _to_float(value)


def _selection_score(aircraft: Aircraft) -> tuple[float, float]:
    completeness_penalty = 0.0 if aircraft.callsign and aircraft.type_code else 0.75
    return aircraft.distance_km + completeness_penalty, -(aircraft.altitude_ft or 0.0)


def _route_hints(raw: dict[str, Any]) -> tuple[str, str]:
    origin = _normalize_airport_code(
        raw.get("origin")
        or raw.get("from")
        or raw.get("dep")
        or raw.get("estDepartureAirport")
        or raw.get("origin_airport")
    )
    destination = _normalize_airport_code(
        raw.get("destination")
        or raw.get("to")
        or raw.get("arr")
        or raw.get("estArrivalAirport")
        or raw.get("destination_airport")
    )

    if origin and destination:
        return origin, destination

    route_value = str(raw.get("route") or raw.get("route_hint") or "").strip().upper()
    if route_value:
        parsed_origin, parsed_destination = _split_route(route_value)
        origin = origin or parsed_origin
        destination = destination or parsed_destination
    return origin, destination


def _split_route(value: str) -> tuple[str, str]:
    normalized = value.replace(">", "-").replace("/", "-").replace(" ", "")
    for separator in ("-",):
        if separator in normalized:
            left, right = normalized.split(separator, 1)
            return _normalize_airport_code(left), _normalize_airport_code(right)
    return "", ""


def _normalize_airport_code(value: Any) -> str:
    code = str(value or "").strip().upper()
    if not code:
        return ""
    code = "".join(ch for ch in code if ch.isalnum())
    return code if len(code) in {3, 4} else ""


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
