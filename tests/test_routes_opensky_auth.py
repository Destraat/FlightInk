from __future__ import annotations

from typing import Any

import requests

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
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError(f"{self.status_code} error")
            error.response = self
            raise error

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self) -> None:
        self.get_calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.get_calls.append({"url": url, **kwargs})
        return FakeResponse([], status_code=403)


def settings(**overrides: Any) -> Settings:
    values = {
        "home_lat": 52.565,
        "home_lon": 5.933,
        "opensky_routes_enabled": True,
        "opensky_route_cache_seconds": 180,
    }
    values.update(overrides)
    return Settings(**values)


def test_opensky_403_temporarily_disables_repeated_requests() -> None:
    session = FakeSession()
    resolver = RouteResolver(FakeStorage(), settings(), session)  # type: ignore[arg-type]

    first = resolver.resolve("KLM74N", "486495", "PH-BQH", origin_hint="AMS")
    second = resolver.resolve("KLM74N", "486495", "PH-BQH", origin_hint="AMS")

    assert first.origin == "AMS"
    assert second.origin == "AMS"
    assert len(session.get_calls) == 1
