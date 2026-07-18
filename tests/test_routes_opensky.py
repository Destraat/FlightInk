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
    def __init__(self, payload: Any, payloads_by_suffix: dict[str, Any] | None = None) -> None:
        self.payload = payload
        self.payloads_by_suffix = payloads_by_suffix or {}
        self.get_calls: list[dict[str, Any]] = []
        self.post_calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.get_calls.append({"url": url, **kwargs})
        for suffix, payload in self.payloads_by_suffix.items():
            if url.endswith(suffix):
                return FakeResponse(payload)
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


def test_partial_route_hints_are_completed_by_opensky() -> None:
    session = FakeSession([
        {
            "icao24": "484abc",
            "callsign": "KLM59W",
            "firstSeen": 100,
            "lastSeen": 200,
            "estDepartureAirport": "EDDH",
            "estArrivalAirport": "EHAM",
        }
    ])
    resolver = RouteResolver(FakeStorage(), settings(), session)  # type: ignore[arg-type]

    route = resolver.resolve("KLM59W", "484ABC", "PH-EXX", origin_hint="HAM", destination_hint="")

    assert route.origin == "HAM"
    assert route.destination == "AMS"
    assert route.destination_country == "NL"
    assert route.landmark == "Westertoren"
    assert route.source == "opensky_aircraft_flights"
    assert len(session.get_calls) == 1


def test_airport_departure_fallback_completes_partial_aircraft_route() -> None:
    session = FakeSession(
        [],
        payloads_by_suffix={
            "/flights/aircraft": [
                {
                    "icao24": "486495",
                    "callsign": "KLM59W",
                    "firstSeen": 100,
                    "lastSeen": 200,
                    "estDepartureAirport": "EDDH",
                    "estArrivalAirport": None,
                }
            ],
            "/flights/departure": [
                {
                    "icao24": "486495",
                    "callsign": "KLM59W",
                    "firstSeen": 100,
                    "lastSeen": 200,
                    "estDepartureAirport": "EDDH",
                    "estArrivalAirport": "EHAM",
                }
            ],
        },
    )
    resolver = RouteResolver(FakeStorage(), settings(), session)  # type: ignore[arg-type]

    route = resolver.resolve("KLM59W", "486495", "PH-BQH")

    assert route.origin == "HAM"
    assert route.destination == "AMS"
    assert route.destination_country == "NL"
    assert route.landmark == "Westertoren"
    assert route.source == "opensky_airport_departure"
    assert [call["url"].rsplit("/", 1)[-1] for call in session.get_calls] == ["aircraft", "departure"]
    departure_params = session.get_calls[1]["params"]
    assert departure_params["airport"] == "EDDH"
    assert departure_params["end"] >= departure_params["begin"]
    assert departure_params["end"] - departure_params["begin"] == 48 * 3600


def test_partial_cached_route_does_not_block_complete_opensky_match() -> None:
    storage = FakeStorage()
    storage.values["route:opensky:484abc:KLM59W"] = {
        "origin": "HAM",
        "destination": None,
        "destination_country": None,
        "landmark": None,
        "source": "opensky_aircraft_flights",
        "verified_at": "100",
    }
    session = FakeSession([
        {
            "icao24": "484abc",
            "callsign": "KLM59W",
            "firstSeen": 100,
            "lastSeen": 200,
            "estDepartureAirport": "EDDH",
            "estArrivalAirport": "EHAM",
        }
    ])
    resolver = RouteResolver(storage, settings(), session)  # type: ignore[arg-type]

    route = resolver.resolve("KLM59W", "484ABC", "PH-EXX")

    assert route.origin == "HAM"
    assert route.destination == "AMS"
    assert len(session.get_calls) == 1


def test_airport_fallback_prefers_matching_icao24() -> None:
    resolver = RouteResolver(FakeStorage(), settings(), FakeSession([]))  # type: ignore[arg-type]
    now = 10_000
    exact_hex = {
        "icao24": "486495",
        "callsign": "KLM59W",
        "firstSeen": 8_000,
        "lastSeen": 8_900,
        "estDepartureAirport": "EDDH",
        "estArrivalAirport": "EHAM",
    }
    wrong_hex = {
        "icao24": "486496",
        "callsign": "KLM59W",
        "firstSeen": 9_500,
        "lastSeen": 9_900,
        "estDepartureAirport": "EDDH",
        "estArrivalAirport": "LFPG",
    }

    assert resolver._flight_score(exact_hex, "KLM59W", now, "486495") > resolver._flight_score(wrong_hex, "KLM59W", now, "486495")


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
