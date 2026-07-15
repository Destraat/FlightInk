from pathlib import Path

from PIL import Image, ImageDraw

from flightink import admin
from flightink.aircraft_shapes import ShapeContext, draw_aircraft_shape


def test_all_primary_aircraft_shapes_render(tmp_path: Path) -> None:
    variants = [
        ("narrowbody", "B738"),
        ("regional_jet", "E190"),
        ("widebody", "B789"),
        ("widebody", "B744"),
        ("widebody", "A388"),
        ("turboprop", "AT72"),
        ("business_jet", "GLF6"),
    ]
    for index, (family, code) in enumerate(variants):
        image = Image.new("L", (500, 220), 255)
        draw = ImageDraw.Draw(image)
        context = ShapeContext(25, 475, 250, 105, 1, 220, 70, 150)
        draw_aircraft_shape(draw, family, code, context)
        assert image.getbbox() is not None
        image.save(tmp_path / f"{index}-{code}.png")


def test_admin_health_and_config(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("HOME_LAT=50.8514\nHOME_LON=5.6910\nREFRESH_SECONDS=60\nDISPLAY_BACKEND=preview\n", encoding="utf-8")
    monkeypatch.setattr(admin, "ENV_PATH", env_path)
    monkeypatch.setattr(admin, "OUTPUT_PATH", tmp_path / "preview.png")
    monkeypatch.setattr(admin, "DB_PATH", tmp_path / "flightink.db")
    monkeypatch.setattr(admin, "_service_status", lambda: "active")
    app = admin.create_admin_app()
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["ok"] is True
    saved = client.post("/config", data={
        "HOME_LAT": "50.8600", "HOME_LON": "5.7000", "REFRESH_SECONDS": "90",
        "DISPLAY_BACKEND": "preview", "RADIUS_NM": "10",
    })
    assert saved.status_code == 302
    assert "HOME_LAT=50.8600" in env_path.read_text(encoding="utf-8")


def test_admin_main_uses_non_conflicting_default_port(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeApp:
        def run(self, host: str, port: int, debug: bool) -> None:
            calls["host"] = host
            calls["port"] = port
            calls["debug"] = debug

    monkeypatch.delenv("ADMIN_HOST", raising=False)
    monkeypatch.delenv("ADMIN_PORT", raising=False)
    monkeypatch.setattr(admin, "create_admin_app", lambda: FakeApp())

    admin.main()

    assert calls == {"host": "0.0.0.0", "port": 8090, "debug": False}
