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
            connection.execute("""
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
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_sightings_seen_at ON sightings(seen_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_sightings_hex ON sightings(hex)")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS passages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aircraft_hex TEXT NOT NULL,
                    callsign TEXT,
                    registration TEXT,
                    type_code TEXT,
                    airline_code TEXT,
                    first_seen_at INTEGER NOT NULL,
                    last_seen_at INTEGER NOT NULL,
                    closest_seen_at INTEGER NOT NULL,
                    closest_distance_km REAL NOT NULL,
                    predicted_closest_distance_km REAL,
                    altitude_ft REAL,
                    speed_knots REAL,
                    origin TEXT,
                    destination TEXT,
                    UNIQUE(aircraft_hex, first_seen_at)
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_passages_last_seen ON passages(last_seen_at)")

    def record_sighting(self, aircraft: Any, route: Any | None = None, prediction: Any | None = None) -> None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO sightings (seen_at, hex, callsign, registration, type_code, airline_code, distance_km, altitude_ft, speed_knots, origin, destination)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (now, aircraft.hex, aircraft.callsign, aircraft.registration, aircraft.type_code, aircraft.airline_code, aircraft.distance_km, aircraft.altitude_ft, aircraft.speed_knots, getattr(route, "origin", None), getattr(route, "destination", None)))

            active = connection.execute("""
                SELECT * FROM passages
                WHERE aircraft_hex = ? AND last_seen_at >= ?
                ORDER BY last_seen_at DESC LIMIT 1
            """, (aircraft.hex, now - 300)).fetchone()
            predicted = getattr(prediction, "closest_distance_km", None)
            if active is None:
                connection.execute("""
                    INSERT INTO passages (aircraft_hex, callsign, registration, type_code, airline_code, first_seen_at, last_seen_at, closest_seen_at, closest_distance_km, predicted_closest_distance_km, altitude_ft, speed_knots, origin, destination)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (aircraft.hex, aircraft.callsign, aircraft.registration, aircraft.type_code, aircraft.airline_code, now, now, now, aircraft.distance_km, predicted, aircraft.altitude_ft, aircraft.speed_knots, getattr(route, "origin", None), getattr(route, "destination", None)))
            else:
                closest_distance = min(float(active["closest_distance_km"]), float(aircraft.distance_km))
                closest_seen_at = now if aircraft.distance_km <= float(active["closest_distance_km"]) else int(active["closest_seen_at"])
                predicted_values = [value for value in (active["predicted_closest_distance_km"], predicted) if value is not None]
                predicted_closest = min(map(float, predicted_values)) if predicted_values else None
                connection.execute("""
                    UPDATE passages
                    SET callsign=?, registration=?, type_code=?, airline_code=?, last_seen_at=?, closest_seen_at=?, closest_distance_km=?, predicted_closest_distance_km=?, altitude_ft=?, speed_knots=?, origin=?, destination=?
                    WHERE id=?
                """, (aircraft.callsign, aircraft.registration, aircraft.type_code, aircraft.airline_code, now, closest_seen_at, closest_distance, predicted_closest, aircraft.altitude_ft, aircraft.speed_knots, getattr(route, "origin", None), getattr(route, "destination", None), int(active["id"])))

    def stats_today(self) -> dict[str, int]:
        now = int(time.time())
        start = now - (now % 86400)
        with self._connect() as connection:
            passages = connection.execute("SELECT COUNT(*) FROM passages WHERE first_seen_at >= ?", (start,)).fetchone()[0]
            unique = connection.execute("SELECT COUNT(DISTINCT aircraft_hex) FROM passages WHERE first_seen_at >= ?", (start,)).fetchone()[0]
        return {"passages": int(passages), "unique_aircraft": int(unique)}

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
