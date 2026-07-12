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


@dataclass(frozen=True)
class Route:
    origin: str | None = None
    destination: str | None = None
    destination_country: str | None = None
    landmark: str | None = None
    source: str = "unknown"

    @property
    def label(self) -> str:
        if self.origin and self.destination:
            return f"{self.origin} → {self.destination}"
        return "Route onbekend"


class RouteResolver:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.routes = self._load_json(ROUTES_FILE)
        self.destinations = self._load_json(DESTINATIONS_FILE)

    def resolve(self, callsign: str) -> Route:
        normalized = re.sub(r"\s+", "", callsign or "").upper()
        if not normalized:
            return Route()

        cached = self.storage.get_cache(f"route:{normalized}", 7 * 24 * 3600)
        if isinstance(cached, dict):
            return Route(**cached)

        route_data = self.routes.get(normalized)
        if not route_data:
            route_data = self._match_prefix(normalized)
        if not isinstance(route_data, dict):
            return Route()

        destination = route_data.get("destination")
        destination_meta = self.destinations.get(destination, {}) if destination else {}
        route = Route(
            origin=route_data.get("origin"),
            destination=destination,
            destination_country=destination_meta.get("country"),
            landmark=destination_meta.get("landmark"),
            source="local_catalog",
        )
        self.storage.set_cache(f"route:{normalized}", route.__dict__)
        return route

    def _match_prefix(self, callsign: str) -> dict[str, Any] | None:
        for pattern, value in self.routes.items():
            if pattern.endswith("*") and callsign.startswith(pattern[:-1]):
                return value
        return None

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
