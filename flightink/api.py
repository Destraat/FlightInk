from __future__ import annotations

import math
from typing import Any

import requests

from .config import Settings
from .models import Aircraft, Weather


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def fetch_aircraft(settings: Settings) -> list[Aircraft]:
    url = f"{settings.airplanes_api_base}/point/{settings.home_lat}/{settings.home_lon}/{settings.radius_nm}"
    response = requests.get(url, timeout=15, headers={"User-Agent": "FlightInk/0.1"})
    response.raise_for_status()
    payload: dict[str, Any] = response.json()

    result: list[Aircraft] = []
    for raw in payload.get("ac", []):
        lat = raw.get("lat")
        lon = raw.get("lon")
        if lat is None or lon is None:
            continue

        result.append(
            Aircraft(
                hex=str(raw.get("hex", "")).strip(),
                callsign=str(raw.get("flight", "")).strip(),
                registration=str(raw.get("r", "")).strip(),
                type_code=str(raw.get("t", "")).strip().upper(),
                latitude=float(lat),
                longitude=float(lon),
                altitude_ft=_to_float(raw.get("alt_baro")),
                speed_knots=_to_float(raw.get("gs")),
                track=_to_float(raw.get("track")),
                distance_km=haversine_km(settings.home_lat, settings.home_lon, float(lat), float(lon)),
            )
        )

    return sorted(result, key=lambda aircraft: aircraft.distance_km)


def fetch_weather(settings: Settings) -> Weather:
    params = {
        "latitude": settings.home_lat,
        "longitude": settings.home_lon,
        "current": "temperature_2m,cloud_cover,weather_code",
        "timezone": "auto",
    }
    response = requests.get(settings.weather_api_base, params=params, timeout=15)
    response.raise_for_status()
    current = response.json().get("current", {})
    return Weather(
        temperature_c=_to_float(current.get("temperature_2m")),
        cloud_cover=int(current["cloud_cover"]) if current.get("cloud_cover") is not None else None,
        weather_code=int(current["weather_code"]) if current.get("weather_code") is not None else None,
    )


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
