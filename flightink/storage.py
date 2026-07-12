from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class Storage:
    def __init__(self, database_path: str = "data/flightink.db", cache_path: str = "data/cache.json") -> None:
        self.database_path = Path(database_path)
        self.cache_path = Path(cache_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sightings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seen_at INTEGER NOT NULL,
                    hex TEXT NOT NULL,
                    callsign TEXT,
                    registration TEXT,
                    type_code TEXT,
                    airline_code TEXT,
                    distance_km REAL,
                    altitude_ft REAL,
                    speed_knots REAL,
                    origin TEXT,
                    destination TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sightings_seen_at ON sightings(seen_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sightings_hex ON sightings(hex)"
            )

    def record_sighting(self, aircraft: Any, route: Any | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sightings (
                    seen_at, hex, callsign, registration, type_code, airline_code,
                    distance_km, altitude_ft, speed_knots, origin, destination
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(time.time()),
                    aircraft.hex,
                    aircraft.callsign,
                    aircraft.registration,
                    aircraft.type_code,
                    aircraft.airline_code,
                    aircraft.distance_km,
                    aircraft.altitude_ft,
                    aircraft.speed_knots,
                    getattr(route, "origin", None),
                    getattr(route, "destination", None),
                ),
            )

    def stats_today(self) -> dict[str, int]:
        start = int(time.time()) - (int(time.time()) % 86400)
        with self._connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM sightings WHERE seen_at >= ?", (start,)
            ).fetchone()[0]
            unique = connection.execute(
                "SELECT COUNT(DISTINCT hex) FROM sightings WHERE seen_at >= ?", (start,)
            ).fetchone()[0]
        return {"sightings": int(total), "unique_aircraft": int(unique)}

    def get_cache(self, key: str, max_age_seconds: int) -> Any | None:
        payload = self._read_cache()
        item = payload.get(key)
        if not isinstance(item, dict):
            return None
        if time.time() - float(item.get("stored_at", 0)) > max_age_seconds:
            return None
        return item.get("value")

    def set_cache(self, key: str, value: Any) -> None:
        payload = self._read_cache()
        payload[key] = {"stored_at": time.time(), "value": value}
        temporary = self.cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.cache_path)

    def _read_cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            value = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
