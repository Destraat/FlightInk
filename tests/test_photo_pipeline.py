from __future__ import annotations

import io
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from flightink.models import Aircraft
from flightink.photo_display import _draw_cached_photo
from flightink.planespotters import AircraftPhoto, PlanespottersClient
from flightink.storage import Storage


class FakeResponse:
    def __init__(self, *, payload=None, content=b"", content_type="application/json"):
        self._payload = payload
        self.content = content
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class FailingSession:
    def get(self, url, **kwargs):
        raise requests.ConnectionError("offline")


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (420, 280), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 110, 380, 170), fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_registration_then_hex_fallback_downloads_and_prepares(tmp_path: Path) -> None:
    session = FakeSession([
        FakeResponse(payload={"photos": []}),
        FakeResponse(payload={"photos": [{
            "thumbnail_large": {"src": "https://cdn.example/photo.jpg"},
            "link": "https://www.planespotters.net/photo/1/example",
            "photographer": "Jane Doe",
        }]}),
        FakeResponse(content=_jpeg_bytes(), content_type="image/jpeg"),
    ])
    client = PlanespottersClient(
        Storage(str(tmp_path / "db.sqlite"), str(tmp_path / "cache.json")),
        "FlightInk/1.0 (+https://example.com/contact)",
        image_cache_enabled=True,
        image_cache_dir=tmp_path / "photos",
        session=session,
    )

    photo = client.latest("PH-BXA", "484001")

    assert photo is not None
    assert photo.image_path is not None
    assert Path(photo.image_path).exists()
    assert Image.open(photo.image_path).size == (500, 268)
    assert "/reg/PH-BXA" in session.calls[0][0]
    assert "/hex/484001" in session.calls[1][0]


def test_prepare_eink_image_fills_target_without_white_side_bars() -> None:
    image = Image.new("RGB", (420, 280), "black")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")

    prepared = PlanespottersClient.prepare_eink_image(buffer.getvalue(), (500, 268))

    assert prepared.size == (500, 268)
    assert prepared.getpixel((0, 134)) < 40
    assert prepared.getpixel((499, 134)) < 40


def test_prepare_eink_image_removes_bright_background() -> None:
    image = Image.new("RGB", (420, 280), (210, 210, 210))
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 110, 340, 170), fill=(45, 45, 45))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")

    prepared = PlanespottersClient.prepare_eink_image(buffer.getvalue(), (500, 268))

    assert prepared.getpixel((10, 10)) > 240
    assert prepared.getpixel((250, 140)) < 120


def test_cached_photo_is_drawn_on_frame(tmp_path: Path) -> None:
    photo_path = tmp_path / "photo.png"
    Image.new("L", (500, 268), 120).save(photo_path)
    canvas = Image.new("L", (800, 480), 245)
    draw = ImageDraw.Draw(canvas)
    fonts = {"small_bold": ImageFont.load_default(), "tiny": ImageFont.load_default()}
    aircraft = Aircraft("484001", "KLM1", "PH-BXA", "B738", 52.1, 5.1, 10000, 250, 90, 2.0)
    photo = AircraftPhoto(
        "https://cdn.example/photo.jpg",
        "https://www.planespotters.net/photo/1/example",
        "Jane Doe",
        str(photo_path),
    )

    assert _draw_cached_photo(draw, fonts, (28, 24, 546, 438), aircraft, photo)
    assert canvas.getpixel((50, 100)) != 245


def test_offline_request_reuses_local_processed_photo(tmp_path: Path) -> None:
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    image_path = photo_dir / "reg-PH-BXA.png"
    Image.new("L", (500, 268), 180).save(image_path)
    image_path.with_suffix(".json").write_text(
        '{"thumbnail_url":"https://cdn.example/photo.jpg","link_url":"https://www.planespotters.net/photo/1/example","photographer":"Jane Doe"}',
        encoding="utf-8",
    )
    client = PlanespottersClient(
        Storage(str(tmp_path / "db.sqlite"), str(tmp_path / "cache.json")),
        "FlightInk/1.0 (+https://example.com/contact)",
        image_cache_enabled=True,
        image_cache_dir=photo_dir,
        session=FailingSession(),
    )

    photo = client.latest("PH-BXA", "484001")

    assert photo is not None
    assert photo.image_path == str(image_path)
