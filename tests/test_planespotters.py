from __future__ import annotations

from pathlib import Path

from flightink.planespotters import PlanespottersClient
from flightink.storage import Storage


def test_parses_large_thumbnail_without_downloading_image(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "db.sqlite"), str(tmp_path / "cache.json"))
    client = PlanespottersClient(storage, "FlightInk/1.0 (+https://example.com/contact)")
    photo = client._parse_photo({
        "thumbnail_large": {"src": "https://cdn.example/photo.jpg"},
        "link": "https://www.planespotters.net/photo/123",
        "photographer": "Jane Doe",
    })
    assert photo is not None
    assert photo.thumbnail_url == "https://cdn.example/photo.jpg"
    assert photo.link_url == "https://www.planespotters.net/photo/123"
    assert photo.photographer == "Jane Doe"


def test_registration_is_preferred_over_hex(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "db.sqlite"), str(tmp_path / "cache.json"))
    client = PlanespottersClient(storage, "FlightInk/1.0 (+https://example.com/contact)")
    assert client._identifier("PH-BXA", "484001") == ("reg", "PH-BXA")


def test_missing_photo_can_be_cached(tmp_path: Path) -> None:
    storage = Storage(str(tmp_path / "db.sqlite"), str(tmp_path / "cache.json"))
    client = PlanespottersClient(storage, "FlightInk/1.0 (+https://example.com/contact)")
    assert client._parse_cached({"missing": True}) is None
