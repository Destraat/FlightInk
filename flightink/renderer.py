from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .aircraft_shapes import ShapeContext, draw_aircraft_shape
from .catalog import aircraft_definition, airline_livery
from .models import Aircraft, Weather, aircraft_name
from .prediction import PassagePrediction


def render_dashboard(
    aircraft: Aircraft | None,
    weather: Weather | None,
    output_path: str,
    size: tuple[int, int] = (800, 480),
    route: Any | None = None,
    stats: dict[str, int] | None = None,
    prediction: PassagePrediction | None = None,
    status: str = "live",
    stale_minutes: int | None = None,
) -> Path:
    image = Image.new("L", size, 244)
    draw = ImageDraw.Draw(image)
    fonts = _fonts()
    _draw_frame(draw, size)

    left = (26, 24, 546, 438)
    right = (558, 24, 774, 438)
    _draw_scene_header(draw, fonts, status, left)
    _draw_scene_background(draw, left, weather)

    if aircraft is None:
        _draw_empty_state(draw, fonts, status, stale_minutes, left)
        _draw_right_panel_placeholder(draw, fonts, right)
    else:
        _draw_aircraft_scene(draw, fonts, aircraft, weather, left)
        _draw_right_panel(draw, fonts, aircraft, route, prediction, right)

    _draw_footer(draw, fonts, weather, stats or {}, stale_minutes, size)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1", dither=Image.Dither.FLOYDSTEINBERG).save(output)
    return output


def _draw_frame(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    width, height = size
    draw.rectangle((8, 8, width - 8, height - 8), outline=20, width=3)
    draw.rectangle((14, 14, width - 14, height - 14), outline=70, width=1)


def _draw_scene_header(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    status: str,
    box: tuple[int, int, int, int],
) -> None:
    x1, y1, x2, _ = box
    draw.text((x1 + 4, y1), "BOVEN ONS", font=fonts["title"], fill=16)
    draw.text((x1 + 4, y1 + 30), "LIVE VLUCHTINFORMATIE", font=fonts["small"], fill=40)
    draw.text((x2 - 180, y1 + 4), _status_title(status), font=fonts["tiny"], fill=60)
    draw.line((x1 + 4, y1 + 52, x1 + 36, y1 + 52), fill=45, width=2)


def _draw_scene_background(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], weather: Weather | None) -> None:
    x1, y1, x2, y2 = box
    horizon_y = y2 - 66
    draw.line((x1 + 6, horizon_y, x2 - 6, horizon_y), fill=140, width=1)
    for idx in range(10):
        y = horizon_y + 2 + idx * 5
        draw.line((x1 + 8, y, x2 - 8, y), fill=236 - idx * 9, width=1)

    cloud_cover = weather.cloud_cover if weather and weather.cloud_cover is not None else 25
    cloud_count = max(2, min(7, int(cloud_cover / 18)))
    positions = [
        (x1 + 44, y1 + 108, 0.65),
        (x1 + 220, y1 + 84, 0.78),
        (x1 + 402, y1 + 106, 0.72),
        (x1 + 120, y1 + 202, 0.95),
        (x1 + 312, y1 + 220, 0.86),
        (x1 + 60, y1 + 276, 0.7),
        (x1 + 390, y1 + 272, 0.62),
    ]
    for x, y, scale in positions[:cloud_count]:
        _cloud(draw, x, y, scale)


def _draw_aircraft_scene(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    aircraft: Aircraft,
    weather: Weather | None,
    box: tuple[int, int, int, int],
) -> None:
    x1, y1, x2, _ = box
    livery = airline_livery(aircraft.airline_code)
    definition = aircraft_definition(aircraft.type_code)
    rightward = aircraft.track is None or not (180 < aircraft.track < 360)

    scene_left = x1 + 16
    scene_right = x2 - 16
    center = (scene_left + scene_right) // 2
    scale = {"short": 0.84, "medium": 1.0, "long": 1.1, "extra_long": 1.16}.get(
        str(definition.get("length_class", "medium")),
        1.0,
    )
    half = int(218 * scale)
    left = max(scene_left + 4, center - half)
    right = min(scene_right - 4, center + half)
    baseline = y1 + 210
    body_gray = int(livery["body_gray"])
    tail_gray = int(livery["tail_gray"])
    engine_gray = int(livery["engine_gray"])

    for offset in range(6):
        draw.line(
            (left + 36, baseline - 40 + offset * 8, right - 16, baseline - 20 + offset * 7),
            fill=205,
            width=1,
        )

    ctx = ShapeContext(
        left=left,
        right=right,
        center=center,
        baseline=baseline,
        direction=1 if rightward else -1,
        body_gray=body_gray,
        tail_gray=tail_gray,
        engine_gray=engine_gray,
    )
    draw_aircraft_shape(draw, aircraft.family, aircraft.type_code, ctx)

    stripe_y = baseline + 8
    draw.line((left + 18, stripe_y, right - 54, stripe_y), fill=int(livery["stripe_gray"]), width=4)
    draw.line((left + 22, stripe_y + 6, right - 56, stripe_y + 6), fill=205, width=1)

    windows = 17 if aircraft.family == "widebody" else 12
    for index in range(windows):
        wx = left + 84 + index * max(12, (right - left - 172) // max(1, windows - 1))
        if not rightward:
            wx = left + right - wx
        draw.ellipse((wx, baseline - 11, wx + 5, baseline - 6), fill=32)
        draw.line((wx, baseline - 5, wx + 5, baseline - 5), fill=180, width=1)

    marking = str(livery.get("marking") or aircraft.airline_code)
    if marking:
        draw.text((center - min(100, len(marking) * 4), baseline - 46), marking, fill=24, font=fonts["small_bold"])

    if weather and weather.cloud_cover and weather.cloud_cover > 55:
        for x in range(x1 + 16, x2 - 16, 22):
            draw.line((x, y1 + 64, x + 16, y1 + 88), fill=224, width=1)


def _draw_empty_state(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    status: str,
    stale_minutes: int | None,
    box: tuple[int, int, int, int],
) -> None:
    messages = {
        "offline": ("Geen internetverbinding", "De gegevens worden automatisch opnieuw opgehaald."),
        "aircraft_error": ("Vluchtbron tijdelijk niet beschikbaar", "Lokale cache blijft beschikbaar voor herstel."),
        "no_aircraft": ("Geen vliegtuig in bereik", "Zodra er verkeer binnenkomt verschijnt het hier."),
        "stale": ("Toont laatst bekende vlucht", "Live-data is tijdelijk niet beschikbaar."),
    }
    heading, body = messages.get(status, messages["no_aircraft"])
    x1, y1, x2, _ = box
    draw.text((x1 + 58, y1 + 176), heading, font=fonts["heading"], fill=24)
    draw.text((x1 + 58, y1 + 210), body, font=fonts["small"], fill=64)
    draw.text((x1 + 58, y1 + 248), f"Status: {_status_title(status)}", font=fonts["tiny"], fill=90)
    if stale_minutes is not None:
        draw.text((x1 + 58, y1 + 266), f"Laatste live update {stale_minutes} min geleden.", font=fonts["tiny"], fill=90)
    draw.rectangle((x1 + 50, y1 + 154, x2 - 52, y1 + 304), outline=138, width=1)


def _draw_right_panel(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    aircraft: Aircraft,
    route: Any | None,
    prediction: PassagePrediction | None,
    box: tuple[int, int, int, int],
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1, y1, x2, y2), radius=8, outline=70, width=1, fill=248)
    livery = airline_livery(aircraft.airline_code)
    route_origin = getattr(route, "origin", None) or "---"
    route_destination = getattr(route, "destination", None) or "---"
    destination_country = getattr(route, "destination_country", None) or livery.get("country", "--")
    destination_city = _city_for_code(route_destination)
    landmark = getattr(route, "landmark", None) or "Onbekende bestemming"

    cursor = y1 + 12
    draw.text((x1 + 10, cursor), "VLUCHT", font=fonts["tiny"], fill=80)
    cursor += 16
    draw.text((x1 + 10, cursor), aircraft.callsign or aircraft.hex.upper(), font=fonts["panel_title"], fill=12)
    draw.text((x2 - 58, cursor + 2), str(livery.get("marking") or aircraft.airline_code), font=fonts["small_bold"], fill=28)
    cursor += 28
    draw.text((x1 + 10, cursor), str(livery.get("name", aircraft.airline_code)), font=fonts["small"], fill=50)
    cursor += 20
    draw.text((x1 + 10, cursor), aircraft_name(aircraft.type_code), font=fonts["body"], fill=28)
    draw.text((x1 + 10, cursor + 18), aircraft.registration or "Registratie onbekend", font=fonts["tiny"], fill=82)
    cursor += 44
    draw.line((x1 + 8, cursor, x2 - 8, cursor), fill=130, width=1)
    cursor += 8

    draw.text((x1 + 10, cursor), "VAN", font=fonts["tiny"], fill=80)
    draw.text((x1 + 116, cursor), "NAAR", font=fonts["tiny"], fill=80)
    cursor += 14
    draw.text((x1 + 10, cursor), route_origin, font=fonts["heading"], fill=18)
    draw.text((x1 + 117, cursor), route_destination, font=fonts["heading"], fill=18)
    draw.text((x1 + 87, cursor + 3), ">", font=fonts["body_bold"], fill=34)
    draw.text((x1 + 10, cursor + 28), _city_for_code(route_origin), font=fonts["tiny"], fill=72)
    draw.text((x1 + 117, cursor + 28), destination_city, font=fonts["tiny"], fill=72)
    draw.text((x1 + 117, cursor + 42), _country_name(destination_country), font=fonts["tiny"], fill=72)
    _draw_flag(draw, destination_country, x2 - 52, cursor + 4, 38, 24)
    cursor += 62
    draw.line((x1 + 8, cursor, x2 - 8, cursor), fill=130, width=1)
    cursor += 8

    altitude = _format_altitude_m(aircraft)
    speed = _format_speed_kmh(aircraft)
    track = _format_track(aircraft)
    distance = f"{aircraft.distance_km:.1f} km".replace(".", ",")
    eta = _format_eta(prediction)
    metrics = [
        ("HOOGTE", altitude, _icon_altitude),
        ("SNELHEID", speed, _icon_speed),
        ("KOERS", track, _icon_compass),
        ("AFSTAND", distance, _icon_pin),
        ("OVER ONS HUIS", eta, _icon_clock),
    ]
    for label, value, icon in metrics:
        icon(draw, x1 + 10, cursor + 2)
        draw.text((x1 + 30, cursor), label, font=fonts["tiny"], fill=80)
        draw.text((x1 + 106, cursor), value, font=fonts["small_bold"], fill=22)
        cursor += 22

    draw.line((x1 + 8, cursor + 2, x2 - 8, cursor + 2), fill=130, width=1)
    cursor += 10
    draw.text((x1 + 10, cursor), "BESTEMMING", font=fonts["tiny"], fill=82)
    cursor += 14
    draw.text((x1 + 10, cursor), destination_city.upper(), font=fonts["heading"], fill=18)
    draw.text((x1 + 10, cursor + 24), _country_name(destination_country), font=fonts["small"], fill=60)
    draw.text((x1 + 10, cursor + 42), landmark, font=fonts["tiny"], fill=70)
    _draw_landmark(draw, x1 + 8, y2 - 60, x2 - 8, y2 - 8, landmark)


def _draw_right_panel_placeholder(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1, y1, x2, y2), radius=8, outline=110, width=1, fill=248)
    draw.text((x1 + 14, y1 + 18), "VLUCHTPANEEL", font=fonts["small_bold"], fill=55)
    draw.text((x1 + 14, y1 + 44), "Wacht op een vliegtuig", font=fonts["body"], fill=30)
    draw.text((x1 + 14, y1 + 70), "in jouw ingestelde bereik.", font=fonts["small"], fill=65)
    draw.rectangle((x1 + 12, y1 + 100, x2 - 12, y2 - 14), outline=155, width=1)


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    weather: Weather | None,
    stats: dict[str, int],
    stale_minutes: int | None,
    size: tuple[int, int],
) -> None:
    width, _ = size
    y = 446
    draw.line((24, y - 14, width - 24, y - 14), fill=110, width=1)
    if weather:
        temp = f"{weather.temperature_c:.0f} C" if weather.temperature_c is not None else "-- C"
        cloud = _weather_label(weather.cloud_cover)
    else:
        temp = "-- C"
        cloud = "weer onbekend"
    draw.text((34, y - 4), f"{temp}   {cloud.upper()}", font=fonts["small"], fill=30)

    passages = int(stats.get("passages", stats.get("unique_aircraft", 0)))
    date_text = datetime.now().strftime("%d %b %Y")
    draw.text((300, y - 4), f"{date_text}   {passages} passages", font=fonts["small"], fill=42)

    updated = datetime.now().strftime("%H:%M")
    suffix = f" - data {stale_minutes} min oud" if stale_minutes else ""
    draw.text((610, y - 4), f"{updated}{suffix}", font=fonts["small"], fill=42)


def _draw_flag(draw: ImageDraw.ImageDraw, country_code: str | None, x: int, y: int, width: int, height: int) -> None:
    code = (country_code or "").strip().upper()
    draw.rectangle((x, y, x + width, y + height), outline=60, width=1, fill=240)
    if code in {"NL", "FR", "DE"}:
        third = height // 3
        for idx in range(3):
            shade = 90 if idx == 0 else 180 if idx == 1 else 230
            draw.rectangle((x + 1, y + 1 + idx * third, x + width - 1, y + (idx + 1) * third), fill=shade)
    elif code in {"ES", "IT", "IE"}:
        third = width // 3
        for idx in range(3):
            shade = 100 if idx == 0 else 220 if idx == 1 else 140
            draw.rectangle((x + 1 + idx * third, y + 1, x + (idx + 1) * third, y + height - 1), fill=shade)
    elif code in {"GB", "SE", "NO", "DK"}:
        draw.rectangle((x + 1, y + 1, x + width - 1, y + height - 1), fill=200)
        draw.line((x + width // 3, y + 1, x + width // 3, y + height - 1), fill=85, width=3)
        draw.line((x + 1, y + height // 2, x + width - 1, y + height // 2), fill=85, width=3)
    else:
        draw.text((x + 5, y + 7), code or "--", fill=40)


def _draw_landmark(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, landmark: str) -> None:
    draw.rectangle((x1, y1, x2, y2), outline=135, width=1)
    for x in range(x1 + 3, x2 - 2, 10):
        draw.line((x, y2 - 5, x + 4, y2 - 5), fill=210, width=1)
    name = landmark.lower()
    if "eiffel" in name:
        _draw_eiffel(draw, (x1 + x2) // 2, y2 - 4, y1 + 6)
    elif "sagrada" in name:
        _draw_sagrada(draw, x1 + 14, y2 - 4)
    elif "big ben" in name:
        _draw_big_ben(draw, x1 + 24, y2 - 4)
    elif "colosseum" in name:
        _draw_colosseum(draw, x1 + 12, y1 + 10, x2 - 12, y2 - 8)
    else:
        _draw_cityline(draw, x1 + 10, y1 + 8, x2 - 10, y2 - 8)


def _draw_eiffel(draw: ImageDraw.ImageDraw, center_x: int, base_y: int, top_y: int) -> None:
    draw.polygon([(center_x, top_y), (center_x - 26, base_y), (center_x + 26, base_y)], outline=30, fill=220)
    draw.line((center_x - 12, base_y - 24, center_x + 12, base_y - 24), fill=40, width=1)
    draw.line((center_x - 20, base_y - 42, center_x + 20, base_y - 42), fill=40, width=1)


def _draw_sagrada(draw: ImageDraw.ImageDraw, start_x: int, base_y: int) -> None:
    heights = [34, 46, 56, 44, 38]
    x = start_x
    for h in heights:
        draw.rectangle((x, base_y - h, x + 12, base_y), outline=30, fill=214)
        draw.polygon([(x + 6, base_y - h - 8), (x + 2, base_y - h), (x + 10, base_y - h)], fill=130)
        x += 16


def _draw_big_ben(draw: ImageDraw.ImageDraw, x: int, base_y: int) -> None:
    draw.rectangle((x, base_y - 46, x + 18, base_y), outline=35, fill=212)
    draw.rectangle((x - 2, base_y - 56, x + 20, base_y - 46), outline=35, fill=195)
    draw.polygon([(x + 9, base_y - 68), (x + 1, base_y - 56), (x + 17, base_y - 56)], outline=35, fill=180)


def _draw_colosseum(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.rounded_rectangle((x1, y1, x2, y2), radius=12, outline=40, width=1, fill=216)
    span = x2 - x1
    for idx in range(8):
        cx = x1 + 8 + int(idx * (span - 16) / 7)
        draw.arc((cx - 6, y1 + 14, cx + 6, y2 - 8), start=180, end=360, fill=70, width=1)


def _draw_cityline(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    width = x2 - x1
    steps = [0.12, 0.19, 0.27, 0.35, 0.48, 0.57, 0.66, 0.78]
    heights = [16, 26, 20, 32, 18, 28, 22, 30]
    for idx, ratio in enumerate(steps):
        bx = x1 + int(width * ratio)
        h = heights[idx]
        draw.rectangle((bx, y2 - h, bx + 12, y2), outline=35, fill=212)


def _icon_altitude(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.polygon([(x + 3, y + 10), (x + 9, y + 3), (x + 15, y + 10)], outline=25, fill=215)
    draw.line((x + 2, y + 11, x + 16, y + 11), fill=25, width=1)


def _icon_speed(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.arc((x + 2, y + 2, x + 16, y + 16), 180, 360, fill=25, width=1)
    draw.line((x + 9, y + 9, x + 14, y + 6), fill=25, width=1)


def _icon_compass(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 2, y + 2, x + 16, y + 16), outline=25, width=1)
    draw.polygon([(x + 9, y + 4), (x + 12, y + 12), (x + 9, y + 10), (x + 6, y + 12)], outline=25, fill=90)


def _icon_pin(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 4, y + 2, x + 14, y + 12), outline=25, width=1)
    draw.polygon([(x + 9, y + 16), (x + 6, y + 10), (x + 12, y + 10)], fill=25)


def _icon_clock(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 2, y + 2, x + 16, y + 16), outline=25, width=1)
    draw.line((x + 9, y + 9, x + 9, y + 5), fill=25, width=1)
    draw.line((x + 9, y + 9, x + 12, y + 11), fill=25, width=1)


def _cloud(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    width = int(90 * scale)
    height = int(32 * scale)
    draw.arc((x, y, x + width, y + height), 180, 360, fill=170, width=1)
    draw.arc((x + width // 5, y - 8, x + width // 2, y + height - 6), 180, 360, fill=172, width=1)
    draw.arc((x + width // 2, y - 6, x + width - 6, y + height - 4), 180, 360, fill=172, width=1)
    for offset in range(0, width, 12):
        draw.line((x + offset, y + height + 2, x + offset + 6, y + height + 2), fill=208, width=1)


def _status_title(status: str) -> str:
    return {
        "live": "LIVE",
        "offline": "OFFLINE",
        "aircraft_error": "SOURCE ERROR",
        "stale": "STALE",
        "no_aircraft": "NO AIRCRAFT",
    }.get(status, "LIVE")


def _format_altitude_m(aircraft: Aircraft) -> str:
    if aircraft.altitude_m is None:
        return "onbekend"
    return f"{aircraft.altitude_m:,.0f} m".replace(",", ".")


def _format_speed_kmh(aircraft: Aircraft) -> str:
    if aircraft.speed_kmh is None:
        return "onbekend"
    return f"{aircraft.speed_kmh:,.0f} km/u".replace(",", ".")


def _format_track(aircraft: Aircraft) -> str:
    if aircraft.track is None:
        return "onbekend"
    return f"{aircraft.track:.0f} deg"


def _format_eta(prediction: PassagePrediction | None) -> str:
    if prediction is None or prediction.seconds_until_closest is None:
        return "onbekend"
    if prediction.approaching:
        return f"{prediction.seconds_until_closest} sec"
    return "voorbij"


def _weather_label(cloud_cover: int | None) -> str:
    if cloud_cover is None:
        return "onbekend"
    if cloud_cover < 20:
        return "helder"
    if cloud_cover < 50:
        return "licht bewolkt"
    if cloud_cover < 80:
        return "bewolkt"
    return "zwaar bewolkt"


def _country_name(country_code: str | None) -> str:
    mapping = {
        "NL": "Nederland",
        "BE": "Belgie",
        "DE": "Duitsland",
        "FR": "Frankrijk",
        "ES": "Spanje",
        "GB": "Verenigd Koninkrijk",
        "PT": "Portugal",
        "IT": "Italie",
        "CH": "Zwitserland",
        "AT": "Oostenrijk",
        "SE": "Zweden",
        "NO": "Noorwegen",
        "DK": "Denemarken",
        "IE": "Ierland",
        "TR": "Turkije",
    }
    code = (country_code or "").strip().upper()
    return mapping.get(code, code or "Onbekend")


def _city_for_code(code: str | None) -> str:
    mapping = {
        "AMS": "Amsterdam",
        "BCN": "Barcelona",
        "CDG": "Parijs",
        "LHR": "Londen",
        "FRA": "Frankfurt",
        "CPH": "Kopenhagen",
        "ARN": "Stockholm",
        "OSL": "Oslo",
        "VIE": "Wenen",
        "ZRH": "Zurich",
        "LIS": "Lisbon",
        "FCO": "Rome",
    }
    value = (code or "").strip().upper()
    return mapping.get(value, value or "Onbekend")


def _fonts() -> dict[str, ImageFont.ImageFont]:
    def load(size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()

    return {
        "title": load(38, True),
        "panel_title": load(36, True),
        "heading": load(30, True),
        "body": load(19),
        "body_bold": load(19, True),
        "small": load(14),
        "small_bold": load(14, True),
        "tiny": load(11, True),
    }
