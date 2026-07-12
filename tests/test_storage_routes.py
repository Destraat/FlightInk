from pathlib import Path

from flightink.models import Aircraft
from flightink.routes import RouteResolver
from flightink.storage import Storage


def test_storage_records_sighting(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "flightink.db"), str(tmp_path / "cache.json"))
    aircraft = Aircraft("abc123", "KLM14001", "PH-ABC", "B738", 52.0, 5.0, 10000, 400, 90, 2.0)
    storage.record_sighting(aircraft)
    assert storage.stats_today()["sightings"] == 1
    assert storage.stats_today()["unique_aircraft"] == 1


def test_cache_roundtrip(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "flightink.db"), str(tmp_path / "cache.json"))
    storage.set_cache("answer", {"value": 42})
    assert storage.get_cache("answer", 60) == {"value": 42}


def test_route_resolver_returns_route(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "flightink.db"), str(tmp_path / "cache.json"))
    route = RouteResolver(storage).resolve("KLM14001")
    assert route.destination == "BCN"
    assert route.destination_country == "ES"
