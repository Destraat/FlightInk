from pathlib import Path

from PIL import Image

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
