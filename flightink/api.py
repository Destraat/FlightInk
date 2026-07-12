from __future__ import annotations

import math
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Settings
from .models import Aircraft, Weather


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
    client = session or create_session()
    url = f"{settings.airplanes_api_base}/point/{settings.home_lat}/{settings.home_lon}/{settings.radius_nm}"
    response = client.get(url, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()

    result: list[Aircraft] = []
    for raw in payload.get("ac", []):
        lat = _to_float(raw.get("lat"))
        lon = _to_float(raw.get("lon"))
        if lat is None or lon is None:
            continue
        distance = haversine_km(settings.home_lat, settings.home_lon, lat, lon)
        altitude = _to_float(raw.get("alt_baro"))
        if altitude is not None and altitude < settings.minimum_altitude_ft:
            continue
        if distance > settings.maximum_distance_km:
            continue
        result.append(
            Aircraft(
                hex=str(raw.get("hex", "")).strip().lower(),
                callsign=str(raw.get("flight", "")).strip().upper(),
                registration=str(raw.get("r", "")).strip().upper(),
                type_code=str(raw.get("t", "")).strip().upper(),
                latitude=lat,
                longitude=lon,
                altitude_ft=altitude,
                speed_knots=_to_float(raw.get("gs")),
                track=_to_float(raw.get("track")),
                distance_km=distance,
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


def _selection_score(aircraft: Aircraft) -> tuple[float, float]:
    # Distance dominates; aircraft with a callsign and type are preferred on ties.
    completeness_penalty = 0.0 if aircraft.callsign and aircraft.type_code else 0.75
    return aircraft.distance_km + completeness_penalty, -(aircraft.altitude_ft or 0.0)


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
