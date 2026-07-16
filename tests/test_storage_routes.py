from pathlib import Path

from flightink.config import Settings
from flightink.models import Aircraft
from flightink.routes import RouteResolver
from flightink.storage import Storage


def test_storage_records_passage(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "flightink.db"), str(tmp_path / "cache.json"))
    aircraft = Aircraft("abc123", "KLM14001", "PH-ABC", "B738", 52.0, 5.0, 10000, 400, 90, 2.0)
    storage.record_sighting(aircraft)
    stats = storage.stats_today()
    assert stats["passages"] == 1
    assert stats["unique_aircraft"] == 1


def test_repeated_sightings_stay_one_passage(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "flightink.db"), str(tmp_path / "cache.json"))
    aircraft = Aircraft("abc123", "KLM14001", "PH-ABC", "B738", 52.0, 5.0, 10000, 400, 90, 2.0)
    storage.record_sighting(aircraft)
    storage.record_sighting(aircraft)
    assert storage.stats_today()["passages"] == 1


def test_cache_roundtrip(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "flightink.db"), str(tmp_path / "cache.json"))
    storage.set_cache("answer", {"value": 42})
    assert storage.get_cache("answer", 60) == {"value": 42}


def test_route_resolver_rejects_unverified_wildcard_guess(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "flightink.db"), str(tmp_path / "cache.json"))
    settings = Settings(home_lat=0, home_lon=0, opensky_routes_enabled=False)
    route = RouteResolver(storage, settings).resolve("KLM14001")
    assert route.destination is None
    assert route.label == "Route unknown"
