from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from .config import Settings
from .storage import Storage

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
ROUTES_FILE = ROOT / "data" / "routes.json"
DESTINATIONS_FILE = ROOT / "data" / "destinations.json"
AIRPORT_ALIASES_FILE = ROOT / "data" / "airport_aliases.json"


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
            return f"{self.origin} -> {self.destination}"
        return "Route unknown"


class RouteResolver:
    """Resolve routes from exact local callsigns, then OpenSky by ICAO24.

    OpenSky results are cached because the route endpoint is rate limited and a
    flight route normally does not change while an aircraft passes the house.
    """

    def __init__(self, storage: Storage, settings: Settings, session: requests.Session | None = None) -> None:
        self.storage = storage
        self.settings = settings
        self.session = session or requests.Session()
        self.routes = self._load_json(ROUTES_FILE)
        self.destinations = self._load_json(DESTINATIONS_FILE)
        self.airport_aliases = self._load_json(AIRPORT_ALIASES_FILE)
        self._token: str | None = None
        self._token_expires_at = 0.0

    def resolve(
        self,
        callsign: str,
        icao24: str | None = None,
        registration: str | None = None,
        origin_hint: str | None = None,
        destination_hint: str | None = None,
    ) -> Route:
        normalized_callsign = re.sub(r"\s+", "", callsign or "").upper()
        normalized_icao24 = re.sub(r"[^0-9a-f]", "", (icao24 or "").lower())
        last_known = self._last_known_route(normalized_icao24)
        last_known_callsign = self._last_known_callsign_route(normalized_callsign)

        local = self._resolve_local(normalized_callsign)
        hinted = self._resolve_hints(origin_hint, destination_hint)
        direct_local = self._merge_routes(local, hinted)
        if direct_local.origin and direct_local.destination:
            self._remember_last_known_route(normalized_icao24, direct_local)
            self._remember_last_known_callsign_route(normalized_callsign, direct_local)
            return direct_local
        merged_local = self._merge_routes(direct_local, last_known)
        merged_local = self._merge_routes(merged_local, last_known_callsign)

        if not self.settings.opensky_routes_enabled or len(normalized_icao24) != 6:
            self._remember_last_known_route(normalized_icao24, merged_local)
            self._remember_last_known_callsign_route(normalized_callsign, merged_local)
            return merged_local

        cache_key = f"route:opensky:{normalized_icao24}:{normalized_callsign or '-'}"
        cached = self.storage.get_cache(cache_key, self.settings.opensky_route_cache_seconds)
        if isinstance(cached, dict):
            try:
                cached_route = self._merge_routes(Route(**cached), merged_local)
            except TypeError:
                cached_route = Route()
            if cached_route.origin and cached_route.destination:
                self._remember_last_known_route(normalized_icao24, cached_route)
                self._remember_last_known_callsign_route(normalized_callsign, cached_route)
                return cached_route

        try:
            opensky = self._resolve_opensky(normalized_icao24, normalized_callsign)
        except requests.RequestException:
            LOGGER.warning(
                "OpenSky route lookup failed for %s (%s)",
                registration or normalized_icao24,
                normalized_callsign or "no callsign",
                exc_info=True,
            )
            self._remember_last_known_route(normalized_icao24, merged_local)
            self._remember_last_known_callsign_route(normalized_callsign, merged_local)
            return merged_local

        route = self._merge_routes(opensky, merged_local)
        if route.origin or route.destination:
            self.storage.set_cache(cache_key, asdict(route))
        self._remember_last_known_route(normalized_icao24, route)
        self._remember_last_known_callsign_route(normalized_callsign, route)
        return route

    def _resolve_hints(self, origin_hint: str | None, destination_hint: str | None) -> Route:
        origin = self._display_airport(origin_hint)
        destination = self._display_airport(destination_hint)
        if not origin and not destination:
            return Route()
        return self._build_route(origin, destination, source="adsb_route_hint", verified_at=None)

    def _last_known_route(self, normalized_icao24: str) -> Route:
        if len(normalized_icao24) != 6:
            return Route()
        cached = self.storage.get_cache(f"route:last_known:{normalized_icao24}", 7 * 24 * 3600)
        if not isinstance(cached, dict):
            return Route()
        try:
            return Route(**cached)
        except TypeError:
            return Route()

    def _remember_last_known_route(self, normalized_icao24: str, route: Route) -> None:
        if len(normalized_icao24) != 6:
            return
        if not (route.origin or route.destination):
            return
        self.storage.set_cache(f"route:last_known:{normalized_icao24}", asdict(route))

    def _last_known_callsign_route(self, normalized_callsign: str) -> Route:
        if not normalized_callsign:
            return Route()
        cached = self.storage.get_cache(f"route:last_known_callsign:{normalized_callsign}", 3 * 24 * 3600)
        if not isinstance(cached, dict):
            return Route()
        try:
            return Route(**cached)
        except TypeError:
            return Route()

    def _remember_last_known_callsign_route(self, normalized_callsign: str, route: Route) -> None:
        if not normalized_callsign:
            return
        if not (route.origin and route.destination):
            return
        self.storage.set_cache(f"route:last_known_callsign:{normalized_callsign}", asdict(route))

    def _merge_routes(self, primary: Route, fallback: Route) -> Route:
        if not (primary.origin or primary.destination):
            return fallback
        if not (fallback.origin or fallback.destination):
            return primary

        destination = primary.destination or fallback.destination
        source = primary.source
        if not primary.destination and fallback.destination:
            source = fallback.source
        elif not primary.origin and fallback.origin and not destination:
            source = fallback.source
        return self._build_route(
            primary.origin or fallback.origin,
            destination,
            source=source,
            verified_at=primary.verified_at or fallback.verified_at,
        )

    def _resolve_local(self, normalized_callsign: str) -> Route:
        if not normalized_callsign:
            return Route()

        cached = self.storage.get_cache(f"route:{normalized_callsign}", 30 * 24 * 3600)
        if isinstance(cached, dict):
            try:
                return Route(**cached)
            except TypeError:
                pass

        route_data = self.routes.get(normalized_callsign)
        if not isinstance(route_data, dict):
            return Route()

        route = self._build_route(
            route_data.get("origin_airport") or route_data.get("origin"),
            route_data.get("destination_airport") or route_data.get("destination"),
            source=str(route_data.get("source") or "local_exact"),
            verified_at=route_data.get("verified_at"),
        )
        self.storage.set_cache(f"route:{normalized_callsign}", asdict(route))
        return route

    def _resolve_opensky(self, icao24: str, callsign: str) -> Route:
        now = int(time.time())
        begin = now - self.settings.opensky_route_lookback_hours * 3600
        headers = {"Accept": "application/json"}
        token = self._access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = self.session.get(
            f"{self.settings.opensky_api_base}/flights/aircraft",
            params={"icao24": icao24, "begin": begin, "end": now},
            headers=headers,
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return Route()

        candidates = [item for item in payload if isinstance(item, dict)]
        if not candidates:
            return Route()

        best = self._best_flight(candidates, icao24, callsign, now)
        if not best:
            return Route()

        route = self._build_route(
            best.get("estDepartureAirport"),
            best.get("estArrivalAirport"),
            source="opensky_aircraft_flights",
            verified_at=str(best.get("lastSeen") or best.get("firstSeen") or now),
        )
        if route.origin and route.destination:
            return route

        origin = str(best.get("estDepartureAirport") or "").strip().upper()
        destination = str(best.get("estArrivalAirport") or "").strip().upper()
        if origin and not destination:
            try:
                fallback = self._resolve_opensky_airport_flights("departure", origin, icao24, callsign, now, headers, int(best.get("firstSeen") or now))
            except requests.RequestException:
                LOGGER.info("OpenSky departure fallback failed for %s (%s)", origin, icao24, exc_info=True)
                return route
            return self._merge_routes(fallback, route)
        if destination and not origin:
            try:
                fallback = self._resolve_opensky_airport_flights("arrival", destination, icao24, callsign, now, headers, int(best.get("lastSeen") or now))
            except requests.RequestException:
                LOGGER.info("OpenSky arrival fallback failed for %s (%s)", destination, icao24, exc_info=True)
                return route
            return self._merge_routes(fallback, route)
        return route

    def _resolve_opensky_airport_flights(
        self,
        endpoint: str,
        airport: str,
        icao24: str,
        callsign: str,
        now: int,
        headers: dict[str, str],
        reference_time: int,
    ) -> Route:
        # OpenSky airport endpoints support up to a 2-day interval. Query the
        # full recent window to recover routes that were not yet complete in
        # the newest aircraft-flight record.
        _ = reference_time
        begin = max(0, now - ((48 * 3600) - 1))
        end = now
        response = self.session.get(
            f"{self.settings.opensky_api_base}/flights/{endpoint}",
            params={"airport": airport, "begin": begin, "end": end},
            headers=headers,
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return Route()
        candidates = [item for item in payload if isinstance(item, dict)]
        best = self._best_flight(candidates, icao24, callsign, now)
        if not best:
            return Route()
        return self._build_route(
            best.get("estDepartureAirport"),
            best.get("estArrivalAirport"),
            source=f"opensky_airport_{endpoint}",
            verified_at=str(best.get("lastSeen") or best.get("firstSeen") or now),
        )

    @staticmethod
    def _best_flight(candidates: list[dict[str, Any]], icao24: str, callsign: str, now: int) -> dict[str, Any] | None:
        matching = [
            item
            for item in candidates
            if (
                (icao24 and re.sub(r"[^0-9a-f]", "", str(item.get("icao24") or "").lower()) == icao24)
                or (
                    callsign
                    and re.sub(r"\s+", "", str(item.get("callsign") or "")).upper() == callsign
                )
            )
        ]
        pool = matching or candidates
        if not pool:
            return None
        return max(pool, key=lambda item: RouteResolver._flight_score(item, callsign, now, icao24))

    @staticmethod
    def _flight_score(item: dict[str, Any], callsign: str, now: int, icao24: str = "") -> tuple[int, int, int, int, int]:
        item_icao24 = re.sub(r"[^0-9a-f]", "", str(item.get("icao24") or "").lower())
        icao24_score = 1 if icao24 and item_icao24 == icao24 else 0
        item_callsign = re.sub(r"\s+", "", str(item.get("callsign") or "")).upper()
        callsign_score = 1 if callsign and item_callsign == callsign else 0
        route_score = int(bool(item.get("estDepartureAirport"))) + int(bool(item.get("estArrivalAirport")))
        first_seen = int(item.get("firstSeen") or 0)
        last_seen = int(item.get("lastSeen") or 0)
        active_or_recent = 1 if first_seen <= now and (not last_seen or last_seen >= now - 12 * 3600) else 0
        return icao24_score, callsign_score, route_score, active_or_recent, max(first_seen, last_seen)

    def _build_route(
        self,
        origin: Any,
        destination: Any,
        source: str,
        verified_at: str | None,
    ) -> Route:
        origin_code = self._display_airport(origin)
        destination_code = self._display_airport(destination)
        destination_meta = self.destinations.get(destination_code, {}) if destination_code else {}
        return Route(
            origin=origin_code,
            destination=destination_code,
            destination_country=destination_meta.get("country"),
            landmark=destination_meta.get("landmark"),
            source=source,
            verified_at=verified_at,
        )

    def _display_airport(self, code: Any) -> str | None:
        value = str(code or "").strip().upper()
        if not value or value == "-":
            return None
        alias = self.airport_aliases.get(value)
        return str(alias).upper() if alias else value

    def _access_token(self) -> str | None:
        if not self.settings.opensky_client_id or not self.settings.opensky_client_secret:
            return None
        now = time.time()
        if self._token and now < self._token_expires_at - 30:
            return self._token

        response = self.session.post(
            self.settings.opensky_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.settings.opensky_client_id,
                "client_secret": self.settings.opensky_client_secret,
            },
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            return None
        self._token = str(token)
        self._token_expires_at = now + int(payload.get("expires_in") or 300)
        return self._token

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
