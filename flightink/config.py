from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    home_lat: float
    home_lon: float
    radius_nm: float = 10.0
    refresh_seconds: int = 45
    output_path: str = "output/flightink.png"
    display_width: int = 800
    display_height: int = 480
    airplanes_api_base: str = "https://api.airplanes.live/v2"
    weather_api_base: str = "https://api.open-meteo.com/v1/forecast"

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            lat = float(os.environ["HOME_LAT"])
            lon = float(os.environ["HOME_LON"])
        except KeyError as exc:
            raise RuntimeError("HOME_LAT en HOME_LON ontbreken in de omgeving") from exc
        except ValueError as exc:
            raise RuntimeError("HOME_LAT en HOME_LON moeten geldige getallen zijn") from exc

        return cls(
            home_lat=lat,
            home_lon=lon,
            radius_nm=float(os.getenv("RADIUS_NM", "10")),
            refresh_seconds=int(os.getenv("REFRESH_SECONDS", "45")),
            output_path=os.getenv("OUTPUT_PATH", "output/flightink.png"),
        )
