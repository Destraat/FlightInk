from __future__ import annotations

from typing import Any

from flightink.config import Settings
from flightink.routes import RouteResolver


class FakeStorage:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def get_cache(self, key: str, max_age_seconds: int) -> Any:
        return self.values.get(key)

    def set_cache(self, key: str, value: Any) -> None:
        self.values[key] = value


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.get_calls: list[dict[str, Any]] = []
        self.post_calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.get_calls.append({"url": url, **kwargs})
        return FakeResponse(self.payload)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.post_calls.append({"url": url, **kwargs})
        return FakeResponse({"access_token": "test-token", "expires_in": 300})


def settings(**overrides: Any) -> Settings:
    values = {
        "home_lat": 52.565,
        "home_lon": 5.933,
        "opensky_routes_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_opensky_resolves_route_by_aircraft_hex() -> None:
    session = FakeSession([
        {
            "icao24": "4855d2",
            "callsign": "KLM1234 ",
            "firstSeen": 100,
            "lastSeen": 200,
            "estDepartureAirport": "EHAM",
            "estArrivalAirport": "EGLL",
        }
    ])
    resolver = RouteResolver(FakeStorage(), settings(), session)  # type: ignore[arg-type]

    route = resolver.resolve("KLM1234", "4855D2", "PH-EXX")

    assert route.origin == "AMS"
    assert route.destination == "LHR"
    assert route.destination_country == "GB"
    assert route.landmark == "Big Ben"
    assert route.source == "opensky_aircraft_flights"
    assert session.get_calls[0]["params"]["icao24"] == "4855d2"


def test_exact_local_route_wins_without_opensky_request() -> None:
    session = FakeSession([])
    resolver = RouteResolver(FakeStorage(), settings(), session)  # type: ignore[arg-type]
    resolver.routes = {
        "KLM1234": {
            "origin": "AMS",
            "destination": "CDG",
            "source": "test",
        }
    }

    route = resolver.resolve(" KLM1234 ", "4855d2", "PH-EXX")

    assert route.destination == "CDG"
    assert route.source == "test"
    assert session.get_calls == []


def test_callsign_match_is_preferred_over_newer_other_flight() -> None:
    resolver = RouteResolver(FakeStorage(), settings(), FakeSession([]))  # type: ignore[arg-type]
    now = 10_000
    matching = {
        "callsign": "KLM1234",
        "firstSeen": 8_000,
        "lastSeen": 9_000,
        "estDepartureAirport": "EHAM",
        "estArrivalAirport": "EGLL",
    }
    newer_other = {
        "callsign": "KLM9999",
        "firstSeen": 9_500,
        "lastSeen": 9_900,
        "estDepartureAirport": "EHAM",
        "estArrivalAirport": "EDDF",
    }

    assert resolver._flight_score(matching, "KLM1234", now) > resolver._flight_score(newer_other, "KLM1234", now)


def test_route_hints_fill_destination_without_opensky() -> None:
    session = FakeSession([])
    resolver = RouteResolver(FakeStorage(), settings(), session)  # type: ignore[arg-type]

    route = resolver.resolve("KLM1234", "4855d2", "PH-EXX", origin_hint="AMS", destination_hint="BCN")

    assert route.origin == "AMS"
    assert route.destination == "BCN"
    assert route.destination_country == "ES"
    assert route.landmark == "Sagrada Família"
    assert route.source == "adsb_route_hint"
    assert session.get_calls == []


def test_more_complete_route_wins_over_newer_partial_match() -> None:
    resolver = RouteResolver(FakeStorage(), settings(), FakeSession([]))  # type: ignore[arg-type]
    now = 10_000
    complete = {
        "callsign": "BTI98R",
        "firstSeen": 8_000,
        "lastSeen": 8_900,
        "estDepartureAirport": "EBBR",
        "estArrivalAirport": "EVRA",
    }
    partial_newer = {
        "callsign": "BTI98R",
        "firstSeen": 9_500,
        "lastSeen": 9_900,
        "estDepartureAirport": "EBBR",
        "estArrivalAirport": None,
    }

    assert resolver._flight_score(complete, "BTI98R", now) > resolver._flight_score(partial_newer, "BTI98R", now)


def test_opensky_uses_bearer_token_when_credentials_exist() -> None:
    session = FakeSession([
        {
            "icao24": "300000",
            "callsign": "ITY112",
            "firstSeen": 100,
            "lastSeen": 200,
            "estDepartureAirport": "LIML",
            "estArrivalAirport": "EHAM",
        }
    ])
    resolver = RouteResolver(
        FakeStorage(),
        settings(opensky_client_id="client-id", opensky_client_secret="client-secret"),
        session,  # type: ignore[arg-type]
    )

    resolver.resolve("ITY112", "300000", "EI-XYZ")

    assert session.post_calls
    assert session.get_calls[0]["headers"]["Authorization"] == "Bearer test-token"
