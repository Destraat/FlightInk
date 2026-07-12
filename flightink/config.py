from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    home_lat: float
    home_lon: float
    radius_nm: float = 10.0
    refresh_seconds: int = 60
    output_path: str = "output/flightink.png"
    display_width: int = 800
    display_height: int = 480
    display_backend: str = "preview"
    waveshare_module: str = "waveshare_epd.epd7in5_V2"
    database_path: str = "data/flightink.db"
    cache_path: str = "data/cache.json"
    minimum_altitude_ft: float = 500.0
    maximum_distance_km: float = 20.0
    selection_hold_seconds: int = 90
    request_timeout_seconds: int = 15
    stale_aircraft_seconds: int = 900
    stale_weather_seconds: int = 3600
    prediction_horizon_seconds: int = 900
    airplanes_api_base: str = "https://api.airplanes.live/v2"
    weather_api_base: str = "https://api.open-meteo.com/v1/forecast"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        try:
            lat = float(os.environ["HOME_LAT"])
            lon = float(os.environ["HOME_LON"])
        except KeyError as exc:
            raise RuntimeError("HOME_LAT en HOME_LON ontbreken in .env of de omgeving") from exc
        except ValueError as exc:
            raise RuntimeError("HOME_LAT en HOME_LON moeten geldige getallen zijn") from exc

        settings = cls(
            home_lat=lat,
            home_lon=lon,
            radius_nm=float(os.getenv("RADIUS_NM", "10")),
            refresh_seconds=int(os.getenv("REFRESH_SECONDS", "60")),
            output_path=os.getenv("OUTPUT_PATH", "output/flightink.png"),
            display_backend=os.getenv("DISPLAY_BACKEND", "preview"),
            waveshare_module=os.getenv("WAVESHARE_MODULE", "waveshare_epd.epd7in5_V2"),
            database_path=os.getenv("DATABASE_PATH", "data/flightink.db"),
            cache_path=os.getenv("CACHE_PATH", "data/cache.json"),
            minimum_altitude_ft=float(os.getenv("MINIMUM_ALTITUDE_FT", "500")),
            maximum_distance_km=float(os.getenv("MAXIMUM_DISTANCE_KM", "20")),
            selection_hold_seconds=int(os.getenv("SELECTION_HOLD_SECONDS", "90")),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
            stale_aircraft_seconds=int(os.getenv("STALE_AIRCRAFT_SECONDS", "900")),
            stale_weather_seconds=int(os.getenv("STALE_WEATHER_SECONDS", "3600")),
            prediction_horizon_seconds=int(os.getenv("PREDICTION_HORIZON_SECONDS", "900")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not -90 <= self.home_lat <= 90:
            raise ValueError("HOME_LAT moet tussen -90 en 90 liggen")
        if not -180 <= self.home_lon <= 180:
            raise ValueError("HOME_LON moet tussen -180 en 180 liggen")
        if self.radius_nm <= 0 or self.radius_nm > 250:
            raise ValueError("RADIUS_NM moet groter dan 0 en maximaal 250 zijn")
        if self.refresh_seconds < 20:
            raise ValueError("REFRESH_SECONDS moet minimaal 20 zijn voor e-ink")
        if self.maximum_distance_km <= 0:
            raise ValueError("MAXIMUM_DISTANCE_KM moet groter dan 0 zijn")
        if self.stale_aircraft_seconds < self.refresh_seconds:
            raise ValueError("STALE_AIRCRAFT_SECONDS moet minimaal één refreshinterval zijn")
        if self.display_backend not in {"preview", "waveshare"}:
            raise ValueError("DISPLAY_BACKEND moet preview of waveshare zijn")
