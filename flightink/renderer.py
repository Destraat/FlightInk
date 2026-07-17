from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .catalog import airline_livery
from .models import Aircraft, Weather, aircraft_name
from .prediction import PassagePrediction


AIRCRAFT_ASSETS: dict[str, dict[str, object]] = {
    "narrowbody": {
        "body": [(2, 52), (10, 46), (92, 44), (99, 50), (92, 56), (12, 58)],
        "wing_top": [(38, 52), (56, 28), (67, 30), (48, 53)],
        "wing_bottom": [(38, 53), (61, 74), (72, 73), (46, 52)],
        "tail": [(12, 50), (18, 31), (23, 33), (20, 51)],
        "engine": [(50, 58, 58, 65), (61, 58, 69, 65)],
        "windows": (22, 78, 12),
        "stripe": (15, 89, 53),
        "hatch": [(20, 49, 86, 49), (20, 50, 86, 50), (20, 51, 86, 51)],
    },
    "widebody": {
        "body": [(2, 54), (10, 45), (90, 42), (99, 50), (90, 59), (12, 61)],
        "wing_top": [(34, 53), (58, 22), (72, 25), (47, 54)],
        "wing_bottom": [(35, 55), (64, 78), (76, 76), (45, 54)],
        "tail": [(11, 51), (17, 28), (24, 31), (19, 53)],
        "engine": [(47, 60, 57, 69), (62, 61, 72, 70)],
        "windows": (19, 80, 16),
        "stripe": (14, 88, 55),
        "hatch": [(18, 49, 88, 49), (18, 50, 88, 50), (18, 52, 88, 52)],
    },
    "regional_jet": {
        "body": [(5, 52), (14, 47), (92, 45), (99, 50), (93, 55), (15, 57)],
        "wing_top": [(42, 52), (59, 33), (67, 34), (49, 53)],
        "wing_bottom": [(41, 53), (60, 71), (68, 70), (47, 52)],
        "tail": [(14, 50), (21, 35), (26, 36), (22, 50)],
        "engine": [(24, 55, 31, 61), (31, 55, 38, 61)],
        "windows": (25, 75, 10),
        "stripe": (19, 90, 53),
        "hatch": [(24, 50, 87, 50), (24, 51, 87, 51)],
    },
    "turboprop": {
        "body": [(6, 52), (15, 47), (91, 45), (99, 50), (92, 55), (16, 57)],
        "wing_top": [(42, 52), (59, 36), (67, 37), (48, 53)],
        "wing_bottom": [(42, 53), (60, 67), (68, 66), (48, 52)],
        "tail": [(15, 50), (21, 36), (26, 37), (22, 50)],
        "engine": [(45, 56, 52, 62), (58, 56, 65, 62)],
        "windows": (27, 73, 8),
        "stripe": (20, 89, 53),
        "hatch": [(24, 50, 87, 50), (24, 51, 87, 51)],
        "props": [48, 62],
    },
    "business_jet": {
        "body": [(8, 53), (18, 49), (90, 47), (99, 50), (90, 54), (19, 56)],
        "wing_top": [(41, 53), (56, 37), (63, 38), (48, 53)],
        "wing_bottom": [(41, 53), (57, 65), (64, 64), (47, 53)],
        "tail": [(18, 51), (24, 39), (29, 40), (25, 52)],
        "engine": [(27, 53, 33, 58), (33, 53, 39, 58)],
        "windows": (29, 67, 7),
        "stripe": (23, 89, 53),
        "hatch": [(28, 50, 84, 50), (28, 51, 84, 51)],
    },
}


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
    image = Image.new("L", size, 245)
    draw = ImageDraw.Draw(image)
    fonts = _fonts()
    _draw_frame(draw, size)

    left = (28, 24, 546, 438)
    right = (558, 24, 772, 438)
    _draw_header(draw, fonts, left, status)
    _draw_scene_background(draw, left, weather)

    if aircraft is None:
        _draw_empty_state(draw, fonts, left, status, stale_minutes)
        _draw_panel_placeholder(draw, fonts, right)
    else:
        _draw_aircraft_illustration(draw, fonts, left, aircraft, weather)
        _draw_info_panel(draw, fonts, right, aircraft, route, prediction)

    _draw_footer(draw, fonts, weather, stats or {}, stale_minutes, size)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1", dither=Image.Dither.FLOYDSTEINBERG).save(output)
    return output


def _draw_frame(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw.rectangle((8, 8, w - 8, h - 8), outline=18, width=3)
    draw.rectangle((13, 13, w - 13, h - 13), outline=70, width=1)


def _draw_header(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], box: tuple[int, int, int, int], status: str) -> None:
    x1, y1, x2, _ = box
    draw.text((x1, y1 + 2), "BOVEN ONS", font=fonts["title"], fill=18)
    draw.text((x1, y1 + 26), "LIVE VLUCHTINFORMATIE", font=fonts["small"], fill=45)
    draw.line((x1, y1 + 44, x1 + 30, y1 + 44), fill=55, width=2)
    draw.text((x2 - 96, y1 + 6), _status_label(status), font=fonts["tiny"], fill=65)


def _draw_scene_background(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], weather: Weather | None) -> None:
    x1, y1, x2, y2 = box
    scene_top = y1 + 52
    scene_bottom = y2 - 16
    for i, shade in enumerate((246, 244, 242, 240, 238)):
        draw.rectangle((x1 + i * 2, scene_top + i * 2, x2 - i * 2, scene_bottom - i * 2), outline=shade, width=1)

    horizon = y2 - 70
    draw.line((x1 + 8, horizon, x2 - 8, horizon), fill=132, width=1)
    for idx in range(12):
        y = horizon + 2 + idx * 4
        draw.line((x1 + 10, y, x2 - 10, y), fill=234 - idx * 8, width=1)

    clouds = max(2, min(7, int(((weather.cloud_cover or 25) / 100.0) * 8))) if weather else 3
    presets = [
        (x1 + 34, y1 + 110, 0.58),
        (x1 + 198, y1 + 88, 0.74),
        (x1 + 360, y1 + 112, 0.68),
        (x1 + 90, y1 + 204, 0.96),
        (x1 + 290, y1 + 214, 0.9),
        (x1 + 44, y1 + 286, 0.65),
        (x1 + 392, y1 + 282, 0.62),
    ]
    for px, py, scale in presets[:clouds]:
        _draw_cloud(draw, px, py, scale)


def _draw_aircraft_illustration(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[int, int, int, int],
    aircraft: Aircraft,
    weather: Weather | None,
) -> None:
    x1, y1, x2, _ = box
    livery = airline_livery(aircraft.airline_code)
    family = aircraft.family if aircraft.family in AIRCRAFT_ASSETS else "narrowbody"
    asset = AIRCRAFT_ASSETS[family]
    rightward = aircraft.track is None or not (180 < aircraft.track < 360)

    body_box = (x1 + 30, y1 + 106, x2 - 18, y1 + 252)
    _draw_aircraft_asset(draw, body_box, asset, rightward, livery)
    draw.text((body_box[0] + 110, body_box[1] + 30), str(livery.get("marking") or aircraft.airline_code), font=fonts["small_bold"], fill=26)

    reg = aircraft.registration or "REG ONBEKEND"
    draw.text((body_box[0] + 86, body_box[1] + 70), reg, font=fonts["tiny"], fill=70)

    if weather and weather.cloud_cover and weather.cloud_cover > 50:
        for xx in range(x1 + 16, x2 - 12, 18):
            draw.line((xx, y1 + 72, xx + 8, y1 + 82), fill=226, width=1)


def _draw_aircraft_asset(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    asset: dict[str, object],
    rightward: bool,
    livery: dict[str, object],
) -> None:
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1

    def map_point(px: float, py: float) -> tuple[int, int]:
        mx = x1 + int((px / 100.0) * w)
        my = y1 + int((py / 100.0) * h)
        if rightward:
            return mx, my
        return x1 + x2 - mx, my

    def map_rect(rect: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
        rx1, ry1 = map_point(rect[0], rect[1])
        rx2, ry2 = map_point(rect[2], rect[3])
        return min(rx1, rx2), min(ry1, ry2), max(rx1, rx2), max(ry1, ry2)

    body = [map_point(px, py) for px, py in asset["body"]]  # type: ignore[index]
    wing_top = [map_point(px, py) for px, py in asset["wing_top"]]  # type: ignore[index]
    wing_bottom = [map_point(px, py) for px, py in asset["wing_bottom"]]  # type: ignore[index]
    tail = [map_point(px, py) for px, py in asset["tail"]]  # type: ignore[index]

    draw.polygon(body, fill=int(livery["body_gray"]), outline=18)
    draw.polygon(wing_top, fill=178, outline=26)
    draw.polygon(wing_bottom, fill=168, outline=26)
    draw.polygon(tail, fill=int(livery["tail_gray"]), outline=22)

    sx1, sx2, sy = asset["stripe"]  # type: ignore[misc]
    lx1, ly = map_point(sx1, sy)
    lx2, _ = map_point(sx2, sy)
    draw.line((lx1, ly, lx2, ly), fill=int(livery["stripe_gray"]), width=4)
    draw.line((lx1, ly + 4, lx2, ly + 4), fill=208, width=1)

    for rect in asset["engine"]:  # type: ignore[index]
        draw.ellipse(map_rect(rect), fill=int(livery["engine_gray"]), outline=20)

    if "props" in asset:
        for p in asset["props"]:  # type: ignore[index]
            cx, cy = map_point(p, 59)
            draw.line((cx, cy - 12, cx, cy + 12), fill=20, width=1)
            draw.line((cx - 12, cy, cx + 12, cy), fill=20, width=1)

    start, end, count = asset["windows"]  # type: ignore[misc]
    for idx in range(count):
        px = start + ((end - start) / max(1, count - 1)) * idx
        wx, wy = map_point(px, 49)
        draw.ellipse((wx - 2, wy - 1, wx + 2, wy + 2), fill=28)

    for hx1, hy1, hx2, hy2 in asset["hatch"]:  # type: ignore[index]
        p1 = map_point(hx1, hy1)
        p2 = map_point(hx2, hy2)
        draw.line((*p1, *p2), fill=150, width=1)


def _draw_info_panel(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[int, int, int, int],
    aircraft: Aircraft,
    route: Any | None,
    prediction: PassagePrediction | None,
) -> None:
    x1, y1, x2, y2 = box
    livery = airline_livery(aircraft.airline_code)
    origin = getattr(route, "origin", None) or "---"
    destination = getattr(route, "destination", None) or "---"
    destination_country = getattr(route, "destination_country", None) or livery.get("country", "--")
    landmark = getattr(route, "landmark", None) or "Onbekende landmark"

    draw.rounded_rectangle((x1, y1, x2, y2), radius=8, outline=75, width=1, fill=248)
    _draw_flight_card(draw, fonts, (x1 + 8, y1 + 8, x2 - 8, y1 + 90), aircraft, livery)

    cursor = y1 + 106
    draw.text((x1 + 10, cursor), "VAN", font=fonts["tiny"], fill=80)
    draw.text((x1 + 114, cursor), "NAAR", font=fonts["tiny"], fill=80)
    cursor += 14
    draw.text((x1 + 10, cursor), origin, font=fonts["heading"], fill=18)
    draw.text((x1 + 114, cursor), destination, font=fonts["heading"], fill=18)
    draw.text((x1 + 88, cursor + 2), ">", font=fonts["body_bold"], fill=38)
    draw.text((x1 + 10, cursor + 22), _city_for_code(origin), font=fonts["tiny"], fill=70)
    draw.text((x1 + 114, cursor + 22), _city_for_code(destination), font=fonts["tiny"], fill=70)
    draw.text((x1 + 114, cursor + 35), _country_name(destination_country), font=fonts["tiny"], fill=70)
    _draw_flag(draw, x2 - 50, cursor + 2, 36, 22, destination_country)
    cursor += 54
    draw.line((x1 + 8, cursor, x2 - 8, cursor), fill=128, width=1)
    cursor += 6

    metrics = [
        ("HOOGTE", _format_altitude(aircraft), _icon_altitude),
        ("SNELHEID", _format_speed(aircraft), _icon_speed),
        ("KOERS", _format_track(aircraft), _icon_compass),
        ("AFSTAND", f"{aircraft.distance_km:.1f} km".replace(".", ","), _icon_pin),
        ("OVER ONS HUIS", _format_eta(prediction), _icon_clock),
    ]
    for label, value, icon in metrics:
        icon(draw, x1 + 10, cursor + 1)
        draw.text((x1 + 28, cursor), label, font=fonts["tiny"], fill=82)
        draw.text((x1 + 104, cursor), value, font=fonts["small_bold"], fill=24)
        cursor += 20

    draw.line((x1 + 8, cursor + 1, x2 - 8, cursor + 1), fill=128, width=1)
    cursor += 8
    draw.text((x1 + 10, cursor), "BESTEMMING", font=fonts["tiny"], fill=82)
    cursor += 13
    draw.text((x1 + 10, cursor), _city_for_code(destination).upper(), font=fonts["heading"], fill=16)
    draw.text((x1 + 10, cursor + 22), _country_name(destination_country), font=fonts["small"], fill=65)
    draw.text((x1 + 10, cursor + 36), landmark, font=fonts["tiny"], fill=70)
    _draw_landmark_asset(draw, (x1 + 8, y2 - 60, x2 - 8, y2 - 8), landmark)


def _draw_flight_card(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[int, int, int, int],
    aircraft: Aircraft,
    livery: dict[str, object],
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1, y1, x2, y2), radius=4, outline=118, width=1, fill=246)
    draw.text((x1 + 4, y1 + 4), "VLUCHT", font=fonts["tiny"], fill=84)
    draw.text((x1 + 4, y1 + 18), aircraft.callsign or aircraft.hex.upper(), font=fonts["panel_title"], fill=12)
    draw.text((x1 + 4, y1 + 36), str(livery.get("name", aircraft.airline_code)), font=fonts["small"], fill=50)
    draw.text((x1 + 4, y1 + 50), aircraft_name(aircraft.type_code), font=fonts["small"], fill=34)
    _draw_airline_badge(draw, fonts, (x2 - 46, y1 + 8, x2 - 6, y1 + 34), str(livery.get("marking") or aircraft.airline_code))


def _draw_panel_placeholder(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1, y1, x2, y2), radius=8, outline=105, width=1, fill=248)
    draw.text((x1 + 14, y1 + 18), "WACHT OP VLUCHT", font=fonts["small_bold"], fill=45)
    draw.text((x1 + 14, y1 + 48), "Geen toestel", font=fonts["small"], fill=70)
    draw.text((x1 + 14, y1 + 62), "in bereik.", font=fonts["small"], fill=70)
    draw.rectangle((x1 + 12, y1 + 92, x2 - 12, y2 - 12), outline=150, width=1)


def _draw_empty_state(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[int, int, int, int],
    status: str,
    stale_minutes: int | None,
) -> None:
    messages = {
        "offline": ("Geen internetverbinding", "Automatisch opnieuw proberen."),
        "aircraft_error": ("Vluchtbron onbereikbaar", "Cache wordt gebruikt waar mogelijk."),
        "stale": ("Laatst bekende vlucht", "Live-feed tijdelijk onderbroken."),
        "no_aircraft": ("Geen vliegtuig in bereik", "Wacht op nieuw verkeer."),
    }
    head, body = messages.get(status, messages["no_aircraft"])
    x1, y1, x2, _ = box
    draw.rectangle((x1 + 56, y1 + 160, x2 - 56, y1 + 308), outline=136, width=1, fill=248)
    draw.text((x1 + 74, y1 + 192), head, font=fonts["heading"], fill=22)
    draw.text((x1 + 74, y1 + 216), body, font=fonts["small"], fill=66)
    if stale_minutes is not None:
        draw.text((x1 + 74, y1 + 236), f"Data {stale_minutes} min oud", font=fonts["tiny"], fill=86)


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    weather: Weather | None,
    stats: dict[str, int],
    stale_minutes: int | None,
    size: tuple[int, int],
) -> None:
    w, _ = size
    y = 446
    draw.line((24, y - 14, w - 24, y - 14), fill=108, width=1)
    temp = f"{weather.temperature_c:.0f} C" if weather and weather.temperature_c is not None else "-- C"
    sky = _weather_label(weather.cloud_cover if weather else None).upper()
    draw.text((34, y - 4), f"{temp}   {sky}", font=fonts["small_bold"], fill=30)
    draw.text((284, y - 4), datetime.now().strftime("%d %b %Y"), font=fonts["small"], fill=42)
    passages = int(stats.get("passages", stats.get("unique_aircraft", 0)))
    draw.text((384, y - 4), f"{passages} passages", font=fonts["small"], fill=42)
    freshness = f" - {stale_minutes} min oud" if stale_minutes else ""
    draw.text((614, y - 4), datetime.now().strftime("%H:%M") + freshness, font=fonts["small"], fill=42)


def _draw_airline_badge(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[int, int, int, int],
    code: str,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1, y1, x2, y2), radius=3, outline=120, width=1, fill=242)
    draw.text((x1 + 7, y1 + 11), code[:4], font=fonts["tiny"], fill=26)
    draw.ellipse((x1 + 14, y1 + 4, x1 + 17, y1 + 7), fill=90)
    draw.ellipse((x1 + 19, y1 + 4, x1 + 22, y1 + 7), fill=90)
    draw.ellipse((x1 + 24, y1 + 4, x1 + 27, y1 + 7), fill=90)


def _draw_flag(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, code: str | None) -> None:
    cc = (code or "").strip().upper()
    draw.rectangle((x, y, x + w, y + h), outline=64, width=1, fill=240)
    if cc == "ES":
        draw.rectangle((x + 1, y + 1, x + w - 1, y + 6), fill=95)
        draw.rectangle((x + 1, y + 7, x + w - 1, y + h - 7), fill=226)
        draw.rectangle((x + 1, y + h - 6, x + w - 1, y + h - 1), fill=95)
    elif cc in {"NL", "FR", "DE"}:
        third = h // 3
        shades = (100, 200, 228)
        for i, shade in enumerate(shades):
            draw.rectangle((x + 1, y + 1 + i * third, x + w - 1, y + (i + 1) * third), fill=shade)
    elif cc in {"GB", "SE", "NO", "DK"}:
        draw.rectangle((x + 1, y + 1, x + w - 1, y + h - 1), fill=188)
        draw.line((x + w // 3, y + 1, x + w // 3, y + h - 1), fill=74, width=3)
        draw.line((x + 1, y + h // 2, x + w - 1, y + h // 2), fill=74, width=3)
    else:
        draw.text((x + 4, y + 7), cc or "--", fill=40)


def _draw_landmark_asset(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], landmark: str) -> None:
    x1, y1, x2, y2 = box
    draw.rectangle((x1, y1, x2, y2), outline=132, width=1, fill=244)
    for xx in range(x1 + 2, x2 - 2, 9):
        draw.line((xx, y2 - 4, xx + 4, y2 - 4), fill=214, width=1)

    name = landmark.lower()
    if "sagrada" in name:
        _landmark_sagrada(draw, x1 + 10, y2 - 4)
    elif "eiffel" in name:
        _landmark_eiffel(draw, (x1 + x2) // 2, y2 - 4, y1 + 5)
    elif "big ben" in name:
        _landmark_big_ben(draw, x1 + 18, y2 - 4)
    elif "colosseum" in name:
        _landmark_colosseum(draw, x1 + 10, y1 + 10, x2 - 10, y2 - 6)
    else:
        _landmark_cityline(draw, x1 + 8, y1 + 8, x2 - 8, y2 - 6)


def _landmark_sagrada(draw: ImageDraw.ImageDraw, start_x: int, base_y: int) -> None:
    heights = [30, 42, 52, 44, 34]
    x = start_x
    for h in heights:
        draw.rectangle((x, base_y - h, x + 12, base_y), outline=36, fill=214)
        draw.polygon([(x + 6, base_y - h - 8), (x + 2, base_y - h), (x + 10, base_y - h)], fill=132)
        x += 15


def _landmark_eiffel(draw: ImageDraw.ImageDraw, cx: int, base_y: int, top_y: int) -> None:
    draw.polygon([(cx, top_y), (cx - 24, base_y), (cx + 24, base_y)], outline=34, fill=218)
    draw.line((cx - 11, base_y - 22, cx + 11, base_y - 22), fill=42, width=1)
    draw.line((cx - 18, base_y - 38, cx + 18, base_y - 38), fill=42, width=1)


def _landmark_big_ben(draw: ImageDraw.ImageDraw, x: int, base_y: int) -> None:
    draw.rectangle((x, base_y - 44, x + 16, base_y), outline=34, fill=212)
    draw.rectangle((x - 2, base_y - 54, x + 18, base_y - 44), outline=34, fill=196)
    draw.polygon([(x + 8, base_y - 66), (x + 1, base_y - 54), (x + 15, base_y - 54)], outline=34, fill=182)


def _landmark_colosseum(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.rounded_rectangle((x1, y1, x2, y2), radius=10, outline=40, width=1, fill=216)
    span = x2 - x1
    for idx in range(8):
        cx = x1 + 8 + int(idx * (span - 16) / 7)
        draw.arc((cx - 6, y1 + 12, cx + 6, y2 - 8), start=180, end=360, fill=72, width=1)


def _landmark_cityline(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    span = x2 - x1
    ratios = [0.08, 0.18, 0.26, 0.38, 0.51, 0.62, 0.72, 0.82]
    heights = [14, 22, 18, 30, 20, 26, 18, 24]
    for idx, ratio in enumerate(ratios):
        bx = x1 + int(span * ratio)
        h = heights[idx]
        draw.rectangle((bx, y2 - h, bx + 10, y2), outline=36, fill=212)


def _icon_altitude(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.polygon([(x + 2, y + 10), (x + 8, y + 2), (x + 14, y + 10)], outline=26, fill=212)
    draw.line((x + 2, y + 11, x + 14, y + 11), fill=26, width=1)


def _icon_speed(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.arc((x + 2, y + 2, x + 14, y + 14), 180, 360, fill=26, width=1)
    draw.line((x + 8, y + 8, x + 13, y + 5), fill=26, width=1)


def _icon_compass(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 2, y + 2, x + 14, y + 14), outline=26, width=1)
    draw.polygon([(x + 8, y + 3), (x + 11, y + 11), (x + 8, y + 9), (x + 5, y + 11)], outline=26, fill=98)


def _icon_pin(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 3, y + 2, x + 13, y + 11), outline=26, width=1)
    draw.polygon([(x + 8, y + 15), (x + 5, y + 10), (x + 11, y + 10)], fill=26)


def _icon_clock(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 2, y + 2, x + 14, y + 14), outline=26, width=1)
    draw.line((x + 8, y + 8, x + 8, y + 4), fill=26, width=1)
    draw.line((x + 8, y + 8, x + 11, y + 10), fill=26, width=1)


def _draw_cloud(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    w = int(90 * scale)
    h = int(30 * scale)
    draw.arc((x, y, x + w, y + h), 180, 360, fill=170, width=1)
    draw.arc((x + w // 5, y - 8, x + w // 2, y + h - 5), 180, 360, fill=172, width=1)
    draw.arc((x + w // 2, y - 6, x + w - 5, y + h - 4), 180, 360, fill=172, width=1)
    for dx in range(0, w, 10):
        draw.line((x + dx, y + h + 2, x + dx + 4, y + h + 2), fill=208, width=1)


def _status_label(status: str) -> str:
    return {
        "live": "LIVE",
        "offline": "OFFLINE",
        "aircraft_error": "SOURCE ERROR",
        "stale": "STALE",
        "no_aircraft": "NO AIRCRAFT",
    }.get(status, "LIVE")


def _format_altitude(aircraft: Aircraft) -> str:
    if aircraft.altitude_m is None:
        return "onbekend"
    return f"{aircraft.altitude_m:,.0f} m".replace(",", ".")


def _format_speed(aircraft: Aircraft) -> str:
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
        "title": load(17, True),
        "panel_title": load(16, True),
        "heading": load(15, True),
        "body": load(13),
        "body_bold": load(13, True),
        "small": load(11),
        "small_bold": load(11, True),
        "tiny": load(9, True),
    }
