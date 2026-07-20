from __future__ import annotations

from typing import Any

import main as flightink_main
from flightink.config import Settings
from flightink.models import Aircraft


def _settings(**overrides: Any) -> Settings:
    values = {
        "home_lat": 52.565,
        "home_lon": 5.933,
        "aircraft_source": "hybrid",
    }
    values.update(overrides)
    return Settings(**values)


def test_remote_route_hint_lookup_enriches_local_aircraft(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    local = Aircraft("4855d2", "KLM1234", "PH-EXX", "B738", 52.1, 5.1, 35000, 440, 180, 4.0)
    remote = Aircraft("4855d2", "KLM1234", "PH-EXX", "B738", 52.1, 5.1, 35000, 440, 180, 4.1, "AMS", "BCN")

    monkeypatch.setattr(flightink_main, "fetch_remote_aircraft", lambda settings, session: [remote])

    hints = flightink_main._remote_route_hint_lookup([local], _settings(), session=object())  # type: ignore[arg-type]

    assert hints[flightink_main._aircraft_hint_identity(local)] == ("AMS", "BCN")


def test_remote_route_hint_lookup_skips_when_hints_are_already_complete(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    local = Aircraft("4855d2", "KLM1234", "PH-EXX", "B738", 52.1, 5.1, 35000, 440, 180, 4.0, "AMS", "BCN")
    called = False

    def fake_remote(settings, session):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(flightink_main, "fetch_remote_aircraft", fake_remote)

    hints = flightink_main._remote_route_hint_lookup([local], _settings(), session=object())  # type: ignore[arg-type]

    assert hints == {}
    assert not called
