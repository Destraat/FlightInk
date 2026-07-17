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
    display_transition: str = "direct"
    transition_steps: int = 2
    transition_delay_seconds: float = 0.5
    database_path: str = "data/flightink.db"
    cache_path: str = "data/cache.json"
    minimum_altitude_ft: float = 500.0
    maximum_distance_km: float = 20.0
    selection_hold_seconds: int = 90
    request_timeout_seconds: int = 15
    stale_aircraft_seconds: int = 900
    stale_weather_seconds: int = 3600
    prediction_horizon_seconds: int = 900
    aircraft_source: str = "hybrid"
    local_adsb_url: str = "http://127.0.0.1:8080/data/aircraft.json"
    local_adsb_timeout_seconds: int = 3
    airplanes_api_base: str = "https://api.airplanes.live/v2"
    weather_api_base: str = "https://api.open-meteo.com/v1/forecast"
    opensky_routes_enabled: bool = True
    opensky_api_base: str = "https://opensky-network.org/api"
    opensky_token_url: str = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    opensky_route_lookback_hours: int = 36
    opensky_route_cache_seconds: int = 1800
    photo_provider: str = "none"
    planespotters_user_agent: str = ""
    planespotters_image_cache_enabled: bool = False
    planespotters_image_cache_dir: str = "data/aircraft_photos"
    planespotters_image_width: int = 492
    planespotters_image_height: int = 234

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        try:
            lat = float(os.environ["HOME_LAT"])
            lon = float(os.environ["HOME_LON"])
        except KeyError as exc:
            raise RuntimeError("HOME_LAT and HOME_LON are required") from exc
        except ValueError as exc:
            raise RuntimeError("HOME_LAT and HOME_LON must be valid numbers") from exc

        settings = cls(
            home_lat=lat,
            home_lon=lon,
            radius_nm=float(os.getenv("RADIUS_NM", "10")),
            refresh_seconds=int(os.getenv("REFRESH_SECONDS", "60")),
            output_path=os.getenv("OUTPUT_PATH", "output/flightink.png"),
            display_backend=os.getenv("DISPLAY_BACKEND", "preview"),
            waveshare_module=os.getenv("WAVESHARE_MODULE", "waveshare_epd.epd7in5_V2"),
            display_transition=os.getenv("DISPLAY_TRANSITION", "direct").strip().lower(),
            transition_steps=int(os.getenv("TRANSITION_STEPS", "2")),
            transition_delay_seconds=float(os.getenv("TRANSITION_DELAY_SECONDS", "0.5")),
            database_path=os.getenv("DATABASE_PATH", "data/flightink.db"),
            cache_path=os.getenv("CACHE_PATH", "data/cache.json"),
            minimum_altitude_ft=float(os.getenv("MINIMUM_ALTITUDE_FT", "500")),
            maximum_distance_km=float(os.getenv("MAXIMUM_DISTANCE_KM", "20")),
            selection_hold_seconds=int(os.getenv("SELECTION_HOLD_SECONDS", "90")),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
            stale_aircraft_seconds=int(os.getenv("STALE_AIRCRAFT_SECONDS", "900")),
            stale_weather_seconds=int(os.getenv("STALE_WEATHER_SECONDS", "3600")),
            prediction_horizon_seconds=int(os.getenv("PREDICTION_HORIZON_SECONDS", "900")),
            aircraft_source=os.getenv("AIRCRAFT_SOURCE", "hybrid").strip().lower(),
            local_adsb_url=os.getenv("LOCAL_ADSB_URL", "http://127.0.0.1:8080/data/aircraft.json").strip(),
            local_adsb_timeout_seconds=int(os.getenv("LOCAL_ADSB_TIMEOUT_SECONDS", "3")),
            opensky_routes_enabled=os.getenv("OPENSKY_ROUTES_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
            opensky_api_base=os.getenv("OPENSKY_API_BASE", "https://opensky-network.org/api").rstrip("/"),
            opensky_token_url=os.getenv("OPENSKY_TOKEN_URL", "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token").strip(),
            opensky_client_id=os.getenv("OPENSKY_CLIENT_ID", "").strip(),
            opensky_client_secret=os.getenv("OPENSKY_CLIENT_SECRET", "").strip(),
            opensky_route_lookback_hours=int(os.getenv("OPENSKY_ROUTE_LOOKBACK_HOURS", "36")),
            opensky_route_cache_seconds=int(os.getenv("OPENSKY_ROUTE_CACHE_SECONDS", "1800")),
            photo_provider=os.getenv("PHOTO_PROVIDER", "none").strip().lower(),
            planespotters_user_agent=os.getenv("PLANESPOTTERS_USER_AGENT", "").strip(),
            planespotters_image_cache_enabled=os.getenv("PLANESPOTTERS_IMAGE_CACHE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
            planespotters_image_cache_dir=os.getenv("PLANESPOTTERS_IMAGE_CACHE_DIR", "data/aircraft_photos").strip(),
            planespotters_image_width=int(os.getenv("PLANESPOTTERS_IMAGE_WIDTH", "492")),
            planespotters_image_height=int(os.getenv("PLANESPOTTERS_IMAGE_HEIGHT", "234")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not -90 <= self.home_lat <= 90:
            raise ValueError("HOME_LAT must be between -90 and 90")
        if not -180 <= self.home_lon <= 180:
            raise ValueError("HOME_LON must be between -180 and 180")
        if self.radius_nm <= 0 or self.radius_nm > 250:
            raise ValueError("RADIUS_NM must be greater than 0 and at most 250")
        if self.refresh_seconds < 20:
            raise ValueError("REFRESH_SECONDS must be at least 20 for e-paper")
        if self.maximum_distance_km <= 0:
            raise ValueError("MAXIMUM_DISTANCE_KM must be greater than 0")
        if self.stale_aircraft_seconds < self.refresh_seconds:
            raise ValueError("STALE_AIRCRAFT_SECONDS must be at least one refresh interval")
        if self.display_backend not in {"preview", "waveshare"}:
            raise ValueError("DISPLAY_BACKEND must be preview or waveshare")
        if self.display_transition not in {"direct", "white", "erase"}:
            raise ValueError("DISPLAY_TRANSITION must be direct, white, or erase")
        if not 1 <= self.transition_steps <= 4:
            raise ValueError("TRANSITION_STEPS must be between 1 and 4")
        if not 0 <= self.transition_delay_seconds <= 10:
            raise ValueError("TRANSITION_DELAY_SECONDS must be between 0 and 10")
        if self.aircraft_source not in {"local", "remote", "hybrid"}:
            raise ValueError("AIRCRAFT_SOURCE must be local, remote, or hybrid")
        if self.local_adsb_timeout_seconds < 1:
            raise ValueError("LOCAL_ADSB_TIMEOUT_SECONDS must be at least 1")
        if not 1 <= self.opensky_route_lookback_hours <= 720:
            raise ValueError("OPENSKY_ROUTE_LOOKBACK_HOURS must be between 1 and 720")
        if self.opensky_route_cache_seconds < 60:
            raise ValueError("OPENSKY_ROUTE_CACHE_SECONDS must be at least 60")
        if bool(self.opensky_client_id) != bool(self.opensky_client_secret):
            raise ValueError("OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET must be configured together")
        if self.photo_provider not in {"none", "planespotters"}:
            raise ValueError("PHOTO_PROVIDER must be none or planespotters")
        if self.photo_provider == "planespotters" and not self.planespotters_user_agent:
            raise ValueError("PLANESPOTTERS_USER_AGENT is required when Planespotters photos are enabled")
        if self.planespotters_image_cache_enabled and self.photo_provider != "planespotters":
            raise ValueError("PLANESPOTTERS_IMAGE_CACHE_ENABLED requires PHOTO_PROVIDER=planespotters")
        if not 100 <= self.planespotters_image_width <= 800:
            raise ValueError("PLANESPOTTERS_IMAGE_WIDTH must be between 100 and 800")
        if not 80 <= self.planespotters_image_height <= 400:
            raise ValueError("PLANESPOTTERS_IMAGE_HEIGHT must be between 80 and 400")
