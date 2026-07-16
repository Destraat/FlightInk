from __future__ import annotations

import io
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from PIL import Image, ImageEnhance, ImageOps

from .storage import Storage

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AircraftPhoto:
    thumbnail_url: str
    link_url: str
    photographer: str
    image_path: str | None = None


class PlanespottersClient:
    """Retrieve Planespotters metadata and optionally prepare a local e-ink image.

    The public Planespotters terms normally prohibit downloading and storing image
    binaries. ``image_cache_enabled`` must therefore only be enabled when the
    project owner has received explicit permission for this physical e-ink use.
    API JSON responses remain cached for no more than 24 hours.
    """

    API_BASE = "https://api.planespotters.net/pub/photos"
    CACHE_SECONDS = 24 * 60 * 60

    def __init__(
        self,
        storage: Storage,
        user_agent: str,
        timeout_seconds: int = 10,
        *,
        image_cache_enabled: bool = False,
        image_cache_dir: str | Path = "data/aircraft_photos",
        image_size: tuple[int, int] = (470, 190),
        session: requests.Session | None = None,
    ) -> None:
        if not user_agent or "FlightInk" not in user_agent:
            raise ValueError("PLANESPOTTERS_USER_AGENT must identify FlightInk and include contact details")
        if image_size[0] < 100 or image_size[1] < 80:
            raise ValueError("Planespotters e-ink image size is too small")

        self.storage = storage
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.image_cache_enabled = image_cache_enabled
        self.image_cache_dir = Path(image_cache_dir)
        self.image_size = image_size
        self.session = session or requests.Session()

        if self.image_cache_enabled:
            self.image_cache_dir.mkdir(parents=True, exist_ok=True)

    def latest(self, registration: str | None, hex_code: str | None) -> AircraftPhoto | None:
        identifiers = self._identifiers(registration, hex_code)
        for identifier_type, identifier in identifiers:
            photo = self._latest_for(identifier_type, identifier)
            if photo is not None:
                return photo
        return None

    def _latest_for(self, identifier_type: str, identifier: str) -> AircraftPhoto | None:
        image_path = self._cached_image_path(identifier_type, identifier)
        manifest_path = image_path.with_suffix(".json")
        cache_key = f"planespotters:{identifier_type}:{identifier.upper()}"
        cached = self.storage.get_cache(cache_key, self.CACHE_SECONDS)

        try:
            if isinstance(cached, dict):
                photo = self._parse_cached(cached)
            else:
                url = f"{self.API_BASE}/{identifier_type}/{quote(identifier, safe='')}"
                response = self.session.get(
                    url,
                    headers=self._headers(),
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                if payload.get("error"):
                    raise requests.HTTPError(str(payload["error"]), response=response)
                photos = payload.get("photos")
                raw_photo = photos[0] if isinstance(photos, list) and photos else None
                photo = self._parse_photo(raw_photo)
                self.storage.set_cache(cache_key, self._serialize(photo))
        except requests.RequestException:
            local = self._load_local_photo(image_path, manifest_path)
            if local is not None:
                LOGGER.info("Using offline Planespotters cache for %s", identifier)
                return local
            raise

        if photo is None or not self.image_cache_enabled:
            return photo

        if not image_path.exists():
            try:
                self._download_and_prepare(photo.thumbnail_url, image_path)
            except (OSError, ValueError, requests.RequestException):
                LOGGER.warning("Could not prepare Planespotters photo for %s", identifier, exc_info=True)
                return photo

        self._write_manifest(manifest_path, photo)
        return AircraftPhoto(
            thumbnail_url=photo.thumbnail_url,
            link_url=photo.link_url,
            photographer=photo.photographer,
            image_path=str(image_path),
        )

    def _download_and_prepare(self, image_url: str, output_path: Path) -> None:
        response = self.session.get(
            image_url,
            headers=self._headers(accept="image/avif,image/webp,image/*,*/*;q=0.8"),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if content_type and not content_type.lower().startswith("image/"):
            raise ValueError(f"Unexpected Planespotters content type: {content_type}")

        prepared = self.prepare_eink_image(response.content, self.image_size)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(".tmp.png")
        prepared.save(temporary, format="PNG", optimize=True)
        temporary.replace(output_path)

    @staticmethod
    def prepare_eink_image(image_data: bytes, size: tuple[int, int]) -> Image.Image:
        with Image.open(io.BytesIO(image_data)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)

            canvas = Image.new("RGB", size, "white")
            offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
            canvas.paste(image, offset)

        grayscale = ImageOps.autocontrast(canvas.convert("L"), cutoff=1)
        grayscale = ImageEnhance.Contrast(grayscale).enhance(1.35)
        grayscale = ImageEnhance.Sharpness(grayscale).enhance(1.15)
        return grayscale

    @staticmethod
    def _write_manifest(path: Path, photo: AircraftPhoto) -> None:
        payload = {
            "thumbnail_url": photo.thumbnail_url,
            "link_url": photo.link_url,
            "photographer": photo.photographer,
        }
        temporary = path.with_suffix(".tmp.json")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _load_local_photo(image_path: Path, manifest_path: Path) -> AircraftPhoto | None:
        if not image_path.is_file() or not manifest_path.is_file():
            return None
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        thumbnail_url = str(payload.get("thumbnail_url") or "").strip()
        link_url = str(payload.get("link_url") or "").strip()
        photographer = str(payload.get("photographer") or "Unknown photographer").strip()
        if not thumbnail_url or not link_url:
            return None
        return AircraftPhoto(thumbnail_url, link_url, photographer, str(image_path))

    def _cached_image_path(self, identifier_type: str, identifier: str) -> Path:
        safe_identifier = re.sub(r"[^A-Z0-9-]", "", identifier.upper()) or "UNKNOWN"
        return self.image_cache_dir / f"{identifier_type}-{safe_identifier}.png"

    def _headers(self, accept: str = "application/json") -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": accept}

    @staticmethod
    def _identifiers(registration: str | None, hex_code: str | None) -> list[tuple[str, str]]:
        identifiers: list[tuple[str, str]] = []
        registration = re.sub(r"[^A-Z0-9-]", "", (registration or "").strip().upper())
        if registration:
            identifiers.append(("reg", registration))

        hex_code = re.sub(r"[^0-9a-f]", "", (hex_code or "").strip().lower())
        if hex_code and not any(value.lower() == hex_code for _, value in identifiers):
            identifiers.append(("hex", hex_code))
        return identifiers

    @classmethod
    def _identifier(cls, registration: str | None, hex_code: str | None) -> tuple[str, str | None]:
        """Compatibility helper retained for existing integrations and tests."""
        identifiers = cls._identifiers(registration, hex_code)
        return identifiers[0] if identifiers else ("hex", None)

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
