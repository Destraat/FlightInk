from pathlib import Path

from PIL import Image

import flightink.renderer as renderer_module
from flightink.models import Aircraft, Weather
from flightink.prediction import PassagePrediction
from flightink.renderer import render_dashboard
from flightink.routes import Route


def test_render_dashboard_generates_target_resolution(tmp_path: Path) -> None:
    output = tmp_path / "frame.png"
    aircraft = Aircraft("484506", "KLM1287", "PH-BVA", "B738", 52.12, 5.12, 35600, 445, 162, 1.9)
    weather = Weather(16.2, 32, 2, 21.0, 130)
    route = Route(origin="AMS", destination="BCN", destination_country="ES", landmark="Sagrada Familia")
    prediction = PassagePrediction(1.4, 32, True)

    path = render_dashboard(
        aircraft,
        weather,
        str(output),
        route=route,
        stats={"passages": 26},
        prediction=prediction,
        status="live",
    )

    assert path == output
    assert output.exists()
    image = Image.open(output)
    assert image.size == (800, 480)


def test_render_dashboard_handles_empty_state(tmp_path: Path) -> None:
    output = tmp_path / "empty.png"

    path = render_dashboard(
        None,
        None,
        str(output),
        route=None,
        prediction=None,
        status="no_aircraft",
        stale_minutes=12,
    )

    assert path == output
    assert output.exists()


def test_render_dashboard_uses_custom_landmark_drawer(tmp_path: Path) -> None:
    output = tmp_path / "custom-landmark.png"
    aircraft = Aircraft("484506", "KLM1287", "PH-BVA", "B738", 52.12, 5.12, 35600, 445, 162, 1.9)
    weather = Weather(16.2, 32, 2, 21.0, 130)
    route = Route(origin="AMS", destination="BCN", destination_country="ES", landmark="Sagrada Familia")
    prediction = PassagePrediction(1.4, 32, True)
    calls: list[str] = []

    def custom(draw, x1, y1, x2, y2, landmark):  # type: ignore[no-untyped-def]
        calls.append(landmark)
        draw.rectangle((x1, y1, x2, y2), fill=0)

    original = renderer_module._draw_landmark
    renderer_module._draw_landmark = custom
    try:
        render_dashboard(
            aircraft,
            weather,
            str(output),
            route=route,
            stats={"passages": 26},
            prediction=prediction,
            status="live",
        )
    finally:
        renderer_module._draw_landmark = original

    assert calls == ["Sagrada Familia"]


def test_fallback_landmark_is_deterministic_per_aircraft() -> None:
    aircraft = Aircraft("486898", "KLM60A", "PH-BXX", "B738", 52.12, 5.12, 35600, 445, 162, 1.9)
    first = renderer_module._fallback_landmark_for_aircraft(aircraft)
    second = renderer_module._fallback_landmark_for_aircraft(aircraft)
    assert first == second
    assert first
