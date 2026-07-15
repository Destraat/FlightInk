from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

from .storage import Storage


@dataclass(frozen=True)
class AircraftPhoto:
    thumbnail_url: str
    link_url: str
    photographer: str


class PlanespottersClient:
    """Fetch photo metadata only.

    Image binaries are never downloaded, cached, proxied, rewritten, or stored.
    The returned thumbnail URL must be used directly by the end user's browser.
    """

    API_BASE = "https://api.planespotters.net/pub/photos"
    CACHE_SECONDS = 24 * 60 * 60

    def __init__(self, storage: Storage, user_agent: str, timeout_seconds: int = 10) -> None:
        if not user_agent or "FlightInk" not in user_agent:
            raise ValueError("PLANESPOTTERS_USER_AGENT must identify FlightInk and include contact details")
        self.storage = storage
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def latest(self, registration: str | None, hex_code: str | None) -> AircraftPhoto | None:
        identifier_type, identifier = self._identifier(registration, hex_code)
        if identifier is None:
            return None

        cache_key = f"planespotters:{identifier_type}:{identifier.upper()}"
        cached = self.storage.get_cache(cache_key, self.CACHE_SECONDS)
        if isinstance(cached, dict):
            return self._parse_cached(cached)

        url = f"{self.API_BASE}/{identifier_type}/{quote(identifier, safe='')}"
        response = requests.get(
            url,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        photos = payload.get("photos")
        photo = photos[0] if isinstance(photos, list) and photos else None
        parsed = self._parse_photo(photo)
        self.storage.set_cache(cache_key, self._serialize(parsed))
        return parsed

    @staticmethod
    def _identifier(registration: str | None, hex_code: str | None) -> tuple[str, str | None]:
        registration = (registration or "").strip().upper()
        if registration:
            return "reg", registration
        hex_code = (hex_code or "").strip().lower()
        return "hex", hex_code or None

    @staticmethod
    def _parse_photo(value: Any) -> AircraftPhoto | None:
        if not isinstance(value, dict):
            return None
        thumbnail = value.get("thumbnail_large") or value.get("thumbnail")
        if isinstance(thumbnail, dict):
            thumbnail_url = str(thumbnail.get("src") or "").strip()
        else:
            thumbnail_url = str(thumbnail or "").strip()
        link_url = str(value.get("link") or "").strip()
        photographer = str(value.get("photographer") or "Unknown photographer").strip()
        if not thumbnail_url or not link_url:
            return None
        return AircraftPhoto(thumbnail_url=thumbnail_url, link_url=link_url, photographer=photographer)

    @classmethod
    def _parse_cached(cls, value: dict[str, Any]) -> AircraftPhoto | None:
        if value.get("missing") is True:
            return None
        return cls._parse_photo(value)

    @staticmethod
    def _serialize(photo: AircraftPhoto | None) -> dict[str, Any]:
        if photo is None:
            return {"missing": True}
        return {
            "thumbnail_large": {"src": photo.thumbnail_url},
            "link": photo.link_url,
            "photographer": photo.photographer,
        }
