from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import Aircraft, Weather, aircraft_name

AIRLINE_LIVERIES = {
    "KLM": {"body": 205, "tail": 120, "stripe": 80},
    "TRA": {"body": 225, "tail": 95, "stripe": 140},
    "RYR": {"body": 220, "tail": 55, "stripe": 90},
    "EZY": {"body": 225, "tail": 110, "stripe": 120},
    "DLH": {"body": 220, "tail": 50, "stripe": 100},
    "BAW": {"body": 215, "tail": 70, "stripe": 95},
    "AFR": {"body": 225, "tail": 90, "stripe": 115},
    "DEFAULT": {"body": 220, "tail": 105, "stripe": 125},
}


def render_dashboard(
    aircraft: Aircraft | None,
    weather: Weather | None,
    output_path: str,
    size: tuple[int, int] = (800, 480),
) -> Path:
    image = Image.new("L", size, 255)
    draw = ImageDraw.Draw(image)
    fonts = _fonts()

    draw.rectangle((8, 8, size[0] - 8, size[1] - 8), outline=25, width=3)
    draw.text((28, 24), "FLIGHTINK", font=fonts["small_bold"], fill=20)
    draw.text((28, 52), "LIVE BOVEN ONS HUIS", font=fonts["title"], fill=10)
    draw.line((28, 92, size[0] - 28, 92), fill=65, width=2)

    if aircraft is None:
        draw.text((215, 205), "Geen vliegtuig in de buurt", font=fonts["heading"], fill=25)
    else:
        _draw_aircraft(draw, aircraft, box=(45, 120, 545, 335))
        _draw_details(draw, aircraft, fonts, x=575, y=118)

    _draw_weather(draw, weather, fonts, x=28, y=382)
    draw.text((610, 432), datetime.now().strftime("Bijgewerkt %H:%M"), font=fonts["small"], fill=55)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1", dither=Image.Dither.FLOYDSTEINBERG).save(output)
    return output


def _draw_aircraft(draw: ImageDraw.ImageDraw, aircraft: Aircraft, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    direction_right = aircraft.track is None or not (180 < aircraft.track < 360)
    livery = AIRLINE_LIVERIES.get(aircraft.airline_code, AIRLINE_LIVERIES["DEFAULT"])

    # Clouds reflect current weather elsewhere in the layout; kept subtle for e-ink.
    for cx, cy, scale in [(105, 150, 1.0), (420, 165, 0.8), (280, 290, 0.7)]:
        _cloud(draw, cx, cy, scale)

    nose_x = x2 - 20 if direction_right else x1 + 20
    tail_x = x1 + 35 if direction_right else x2 - 35
    body_top, body_bottom = 205, 250
    body = [(tail_x, body_top), (nose_x - 50 if direction_right else nose_x + 50, body_top - 10),
            (nose_x, 225), (nose_x - 50 if direction_right else nose_x + 50, body_bottom), (tail_x, body_bottom)]
    draw.polygon(body, fill=livery["body"], outline=20)

    wing_root = 300
    wing = [(wing_root, 225), (wing_root + (120 if direction_right else -120), 310),
            (wing_root + (45 if direction_right else -45), 305), (wing_root - (35 if direction_right else -35), 235)]
    draw.polygon(wing, fill=165, outline=25)

    tail = [(tail_x + (25 if direction_right else -25), 210), (tail_x + (65 if direction_right else -65), 135),
            (tail_x + (95 if direction_right else -95), 210)]
    draw.polygon(tail, fill=livery["tail"], outline=25)
    draw.line((tail_x + (10 if direction_right else -10), 232, nose_x - (65 if direction_right else -65), 232), fill=livery["stripe"], width=5)

    for i in range(12):
        wx = tail_x + (120 if direction_right else -120) + i * (22 if direction_right else -22)
        draw.ellipse((wx, 215, wx + 7, 222), fill=35)

    draw.ellipse((310, 265, 375, 292), fill=150, outline=25, width=2)
    draw.text((230, 180), aircraft.airline_code, fill=30, font=_fonts()["small_bold"])


def _draw_details(draw: ImageDraw.ImageDraw, aircraft: Aircraft, fonts: dict[str, ImageFont.ImageFont], x: int, y: int) -> None:
    draw.text((x, y), aircraft.callsign or aircraft.hex.upper(), font=fonts["heading"], fill=10)
    draw.text((x, y + 42), aircraft_name(aircraft.type_code), font=fonts["body"], fill=25)
    draw.text((x, y + 78), aircraft.registration or "Registratie onbekend", font=fonts["small"], fill=55)

    altitude = f"{aircraft.altitude_ft:,.0f} ft" if aircraft.altitude_ft is not None else "onbekend"
    speed = f"{aircraft.speed_knots * 1.852:,.0f} km/u" if aircraft.speed_knots is not None else "onbekend"
    rows = [("AFSTAND", f"{aircraft.distance_km:.1f} km"), ("HOOGTE", altitude), ("SNELHEID", speed)]
    yy = y + 135
    for label, value in rows:
        draw.text((x, yy), label, font=fonts["tiny"], fill=80)
        draw.text((x, yy + 17), value, font=fonts["body_bold"], fill=20)
        yy += 57


def _draw_weather(draw: ImageDraw.ImageDraw, weather: Weather | None, fonts: dict[str, ImageFont.ImageFont], x: int, y: int) -> None:
    draw.line((x, y - 18, 772, y - 18), fill=100, width=1)
    if weather is None:
        text = "Actueel weer niet beschikbaar"
    else:
        temperature = f"{weather.temperature_c:.1f} °C" if weather.temperature_c is not None else "-- °C"
        clouds = f"{weather.cloud_cover}% bewolking" if weather.cloud_cover is not None else "bewolking onbekend"
        text = f"WEER BOVEN HUIS   {temperature}   ·   {clouds}"
    draw.text((x, y), text, font=fonts["body_bold"], fill=30)


def _cloud(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    w = int(85 * scale)
    h = int(28 * scale)
    draw.arc((x, y, x + w, y + h), 180, 360, fill=190, width=2)


def _fonts() -> dict[str, ImageFont.ImageFont]:
    def load(size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    return {
        "title": load(28, True), "heading": load(24, True), "body": load(17),
        "body_bold": load(17, True), "small": load(14), "small_bold": load(14, True), "tiny": load(11, True),
    }
