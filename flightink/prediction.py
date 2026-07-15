from __future__ import annotations

import math
from dataclasses import dataclass

from .models import Aircraft

EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True, slots=True)
class PassagePrediction:
    closest_distance_km: float
    seconds_until_closest: int | None
    approaching: bool

    @property
    def label(self) -> str:
        if self.seconds_until_closest is None:
            return f"Expected passage: {self.closest_distance_km:.1f} km"
        if self.approaching:
            return f"Passing in about {self.seconds_until_closest} sec - {self.closest_distance_km:.1f} km"
        return f"Already passed - {self.closest_distance_km:.1f} km"


def predict_passage(aircraft: Aircraft, home_lat: float, home_lon: float, horizon_seconds: int = 900) -> PassagePrediction:
    """Estimate closest horizontal approach using a local tangent plane.

    The calculation assumes constant ground speed and track. It is deliberately
    conservative: incomplete ADS-B motion data falls back to the current distance.
    """
    if aircraft.speed_knots is None or aircraft.track is None or aircraft.speed_knots < 5:
        return PassagePrediction(aircraft.distance_km, None, False)

    x_km, y_km = _relative_xy_km(home_lat, home_lon, aircraft.latitude, aircraft.longitude)
    speed_km_s = aircraft.speed_knots * 1.852 / 3600.0
    track_rad = math.radians(aircraft.track)
    vx = speed_km_s * math.sin(track_rad)
    vy = speed_km_s * math.cos(track_rad)
    speed_squared = vx * vx + vy * vy
    if speed_squared <= 0:
        return PassagePrediction(aircraft.distance_km, None, False)

    # Minimise |position + velocity*t|².
    raw_t = -((x_km * vx) + (y_km * vy)) / speed_squared
    approaching = raw_t > 0
    t = min(max(raw_t, 0.0), float(horizon_seconds))
    closest_x = x_km + vx * t
    closest_y = y_km + vy * t
    closest = math.hypot(closest_x, closest_y)
    return PassagePrediction(closest, int(round(t)) if approaching else 0, approaching)


def selection_score(aircraft: Aircraft, prediction: PassagePrediction) -> tuple[float, float, float]:
    """Prefer aircraft expected to pass closest, then soonest, then currently closest."""
    time_penalty = (prediction.seconds_until_closest or 9999) / 1200.0
    completeness_penalty = 0.0 if aircraft.callsign and aircraft.type_code else 0.5
    return prediction.closest_distance_km + time_penalty + completeness_penalty, aircraft.distance_km, -(aircraft.altitude_ft or 0.0)


def _relative_xy_km(home_lat: float, home_lon: float, lat: float, lon: float) -> tuple[float, float]:
    lat_scale = math.pi * EARTH_RADIUS_KM / 180.0
    x = (lon - home_lon) * lat_scale * math.cos(math.radians((lat + home_lat) / 2.0))
    y = (lat - home_lat) * lat_scale
    return x, y
