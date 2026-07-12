from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .storage import Storage

ROOT = Path(__file__).resolve().parent.parent
ROUTES_FILE = ROOT / "data" / "routes.json"
DESTINATIONS_FILE = ROOT / "data" / "destinations.json"


@dataclass(frozen=True, slots=True)
class Route:
    origin: str | None = None
    destination: str | None = None
    destination_country: str | None = None
    landmark: str | None = None
    source: str = "unknown"
    verified_at: str | None = None

    @property
    def label(self) -> str:
        if self.origin and self.destination:
            return f"{self.origin} → {self.destination}"
        return "Route onbekend"


class RouteResolver:
    """Resolve only exact callsigns from a local, user-maintained catalogue.

    Broad prefix guesses are intentionally rejected because a flight-number range
    does not reliably map to one destination. Cached exact entries remain valid.
    """

    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.routes = self._load_json(ROUTES_FILE)
        self.destinations = self._load_json(DESTINATIONS_FILE)

    def resolve(self, callsign: str) -> Route:
        normalized = re.sub(r"\s+", "", callsign or "").upper()
        if not normalized:
            return Route()

        cached = self.storage.get_cache(f"route:{normalized}", 30 * 24 * 3600)
        if isinstance(cached, dict):
            try:
                return Route(**cached)
            except TypeError:
                pass

        route_data = self.routes.get(normalized)
        if not isinstance(route_data, dict):
            return Route()

        destination_code = route_data.get("destination_airport") or route_data.get("destination")
        destination_meta = self.destinations.get(destination_code, {}) if destination_code else {}
        route = Route(
            origin=route_data.get("origin_airport") or route_data.get("origin"),
            destination=destination_code,
            destination_country=destination_meta.get("country"),
            landmark=destination_meta.get("landmark"),
            source=str(route_data.get("source") or "local_exact"),
            verified_at=route_data.get("verified_at"),
        )
        self.storage.set_cache(f"route:{normalized}", {
            "origin": route.origin,
            "destination": route.destination,
            "destination_country": route.destination_country,
            "landmark": route.landmark,
            "source": route.source,
            "verified_at": route.verified_at,
        })
        return route

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
