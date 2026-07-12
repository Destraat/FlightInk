from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .catalog import aircraft_definition, airline_livery
from .models import Aircraft, Weather, aircraft_name
from .routes import Route


def render_dashboard(
    aircraft: Aircraft | None,
    weather: Weather | None,
    output_path: str,
    size: tuple[int, int] = (800, 480),
    route: Route | None = None,
    stats: dict[str, int] | None = None,
) -> Path:
    image = Image.new("L", size, 255)
    draw = ImageDraw.Draw(image)
    fonts = _fonts()
    route = route or Route()
    stats = stats or {}

    draw.rectangle((8, 8, size[0] - 8, size[1] - 8), outline=25, width=3)
    draw.text((28, 22), "FLIGHTINK", font=fonts["small_bold"], fill=20)
    draw.text((28, 49), "LIVE BOVEN ONS HUIS", font=fonts["title"], fill=10)
    draw.line((28, 91, size[0] - 28, 91), fill=65, width=2)

    if aircraft is None:
        draw.text((190, 185), "Geen vliegtuig in de buurt", font=fonts["heading"], fill=25)
        draw.text((235, 225), "Het scherm blijft automatisch zoeken", font=fonts["body"], fill=65)
    else:
        _draw_aircraft(draw, aircraft, weather, box=(35, 105, 545, 330), fonts=fonts)
        _draw_details(draw, aircraft, route, fonts, x=565, y=108)

    _draw_footer(draw, weather, stats, fonts, y=372)
    draw.text((616, 438), datetime.now().strftime("Bijgewerkt %H:%M"), font=fonts["small"], fill=55)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1", dither=Image.Dither.FLOYDSTEINBERG).save(output)
    return output


def _draw_aircraft(draw: ImageDraw.ImageDraw, aircraft: Aircraft, weather: Weather | None,
                   box: tuple[int, int, int, int], fonts: dict[str, ImageFont.ImageFont]) -> None:
    x1, _, x2, _ = box
    direction_right = aircraft.track is None or not (180 < aircraft.track < 360)
    livery = airline_livery(aircraft.airline_code)
    cloud_count = max(0, min(5, round((weather.cloud_cover or 0) / 20))) if weather else 0
    clouds = [(85, 135, 1.0), (400, 145, .8), (245, 285, .7), (470, 275, .6), (145, 260, .6)]
    for cx, cy, scale in clouds[:cloud_count]:
        _cloud(draw, cx, cy, scale)

    definition = aircraft_definition(aircraft.type_code)
    scale = {"short": .82, "medium": 1.0, "long": 1.08, "extra_long": 1.15}.get(
        str(definition.get("length_class", "medium")), 1.0)
    center = (x1 + x2) // 2
    half = int(220 * scale)
    left, right = max(x1 + 8, center - half), min(x2 - 8, center + half)
    nose, tail = (right, left) if direction_right else (left, right)
    sign = 1 if direction_right else -1

    body = [(tail, 202), (nose - 48 * sign, 192), (nose, 222), (nose - 48 * sign, 247), (tail, 247)]
    draw.polygon(body, fill=int(livery["body_gray"]), outline=20)
    draw.polygon([(center, 222), (center + 120 * sign, 305), (center + 42 * sign, 300),
                  (center - 35 * sign, 232)], fill=165, outline=25)
    draw.polygon([(tail + 24 * sign, 208), (tail + 62 * sign, 132), (tail + 94 * sign, 208)],
                 fill=int(livery["tail_gray"]), outline=25)
    draw.line((tail + 10 * sign, 230, nose - 65 * sign, 230), fill=int(livery["stripe_gray"]), width=5)

    count = 15 if aircraft.family == "widebody" else 11
    start, step = tail + 105 * sign, 20 * sign
    for i in range(count):
        wx = start + i * step
        draw.ellipse((wx, 213, wx + 7, 220), fill=35)

    engine_positions = [center + 20 * sign]
    if aircraft.engine_count == 4:
        engine_positions = [center - 78, center + 45]
    for ex in engine_positions:
        draw.ellipse((ex, 262, ex + 65, 290), fill=int(livery["engine_gray"]), outline=25, width=2)

    marking = str(livery.get("marking") or aircraft.airline_code)
    draw.text((center - min(100, len(marking) * 4), 176), marking, fill=30, font=fonts["small_bold"])


def _draw_details(draw: ImageDraw.ImageDraw, aircraft: Aircraft, route: Route,
                  fonts: dict[str, ImageFont.ImageFont], x: int, y: int) -> None:
    livery = airline_livery(aircraft.airline_code)
    draw.text((x, y), aircraft.callsign or aircraft.hex.upper(), font=fonts["heading"], fill=10)
    draw.text((x, y + 34), str(livery.get("name", aircraft.airline_code)), font=fonts["small"], fill=55)
    draw.text((x, y + 57), aircraft_name(aircraft.type_code), font=fonts["body"], fill=25)
    draw.text((x, y + 84), aircraft.registration or "Registratie onbekend", font=fonts["small"], fill=55)
    draw.text((x, y + 112), route.label, font=fonts["small_bold"], fill=25)
    if route.destination_country:
        _draw_flag(draw, route.destination_country, x + 178, y + 108)
    if route.landmark:
        draw.text((x, y + 134), route.landmark, font=fonts["tiny"], fill=70)

    rows = [
        ("AFSTAND", f"{aircraft.distance_km:.1f} km"),
        ("HOOGTE", f"{aircraft.altitude_m:,.0f} m" if aircraft.altitude_m is not None else "onbekend"),
        ("SNELHEID", f"{aircraft.speed_kmh:,.0f} km/u" if aircraft.speed_kmh is not None else "onbekend"),
    ]
    yy = y + 160
    for label, value in rows:
        draw.text((x, yy), label, font=fonts["tiny"], fill=80)
        draw.text((x, yy + 15), value, font=fonts["body_bold"], fill=20)
        yy += 48


def _draw_footer(draw: ImageDraw.ImageDraw, weather: Weather | None, stats: dict[str, int],
                 fonts: dict[str, ImageFont.ImageFont], y: int) -> None:
    draw.line((28, y - 14, 772, y - 14), fill=100, width=1)
    if weather:
        temp = f"{weather.temperature_c:.1f} °C" if weather.temperature_c is not None else "-- °C"
        clouds = f"{weather.cloud_cover}% bewolking" if weather.cloud_cover is not None else "bewolking onbekend"
        wind = f"{weather.wind_speed_kmh:.0f} km/u wind" if weather.wind_speed_kmh is not None else ""
        text = f"WEER   {temp} · {clouds}" + (f" · {wind}" if wind else "")
    else:
        text = "WEER   niet beschikbaar"
    draw.text((28, y), text, font=fonts["body_bold"], fill=30)
    draw.text((28, y + 34), f"VANDAAG   {stats.get('unique_aircraft', 0)} unieke toestellen · {stats.get('sightings', 0)} metingen",
              font=fonts["small"], fill=55)


def _draw_flag(draw: ImageDraw.ImageDraw, country: str, x: int, y: int) -> None:
    # E-ink-friendly symbolic flag: country code in one single bordered badge.
    draw.rectangle((x, y, x + 34, y + 20), outline=20, width=2)
    draw.text((x + 5, y + 3), country[:2].upper(), font=_fonts()["tiny"], fill=20)


def _cloud(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    w, h = int(85 * scale), int(28 * scale)
    draw.arc((x, y, x + w, y + h), 180, 360, fill=175, width=2)


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
    return {"title": load(28, True), "heading": load(23, True), "body": load(16),
            "body_bold": load(16, True), "small": load(13), "small_bold": load(13, True),
            "tiny": load(10, True)}
