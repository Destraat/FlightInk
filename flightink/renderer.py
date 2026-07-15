from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .aircraft_shapes import ShapeContext, draw_aircraft_shape
from .catalog import aircraft_definition, airline_livery
from .models import Aircraft, Weather, aircraft_name
from .prediction import PassagePrediction


def render_dashboard(aircraft: Aircraft | None, weather: Weather | None, output_path: str, size: tuple[int, int] = (800, 480), route: Any | None = None, stats: dict[str, int] | None = None, prediction: PassagePrediction | None = None, status: str = "live", stale_minutes: int | None = None) -> Path:
    image = Image.new("L", size, 255)
    draw = ImageDraw.Draw(image)
    fonts = _fonts()
    draw.rectangle((8, 8, size[0] - 8, size[1] - 8), outline=25, width=3)
    draw.text((28, 23), "FLIGHTINK", font=fonts["small_bold"], fill=20)
    draw.text((28, 49), _status_title(status), font=fonts["title"], fill=10)
    draw.line((28, 90, size[0] - 28, 90), fill=65, width=2)
    if aircraft is None:
        _draw_empty_state(draw, fonts, status, stale_minutes)
    else:
        _draw_aircraft(draw, aircraft, (35, 105, 535, 330), fonts, weather)
        _draw_details(draw, aircraft, fonts, 555, 108, route, prediction)
    _draw_footer(draw, weather, stats or {}, fonts, stale_minutes)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1", dither=Image.Dither.FLOYDSTEINBERG).save(output)
    return output


def _status_title(status: str) -> str:
    return {"live":"LIVE NEAR HOME","offline":"NO INTERNET CONNECTION","aircraft_error":"FLIGHT SOURCE UNAVAILABLE","stale":"LAST KNOWN FLIGHT","no_aircraft":"QUIET AIRSPACE"}.get(status, "LIVE NEAR HOME")


def _draw_empty_state(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], status: str, stale_minutes: int | None) -> None:
    messages = {"offline":("No internet connection","The display will retry automatically."),"aircraft_error":("Aircraft data is temporarily unavailable","Stored data remains available locally."),"no_aircraft":("No aircraft nearby","A flight will appear when one approaches.")}
    heading, body = messages.get(status, messages["no_aircraft"])
    draw.text((95, 190), heading, font=fonts["heading"], fill=20)
    draw.text((95, 238), body, font=fonts["body"], fill=60)
    if stale_minutes is not None:
        draw.text((95, 278), f"Last valid data: {stale_minutes} minutes ago", font=fonts["small"], fill=80)


def _draw_aircraft(draw: ImageDraw.ImageDraw, aircraft: Aircraft, box: tuple[int, int, int, int], fonts: dict[str, ImageFont.ImageFont], weather: Weather | None) -> None:
    x1, _, x2, _ = box
    rightward = aircraft.track is None or not (180 < aircraft.track < 360)
    livery = airline_livery(aircraft.airline_code)
    definition = aircraft_definition(aircraft.type_code)
    cloud_count = max(0, min(4, round((weather.cloud_cover or 0) / 25))) if weather else 1
    for cx, cy, scale in [(75,130,.8),(245,115,.65),(410,155,.75),(300,275,.55)][:cloud_count]:
        _cloud(draw, cx, cy, scale)
    scale = {"short":.82,"medium":1.0,"long":1.08,"extra_long":1.15}.get(str(definition.get("length_class","medium")),1.0)
    center = (x1 + x2) // 2
    half = int(215 * scale)
    left, right = max(x1 + 8, center - half), min(x2 - 8, center + half)
    ctx = ShapeContext(left=left, right=right, center=center, baseline=208, direction=1 if rightward else -1, body_gray=int(livery["body_gray"]), tail_gray=int(livery["tail_gray"]), engine_gray=int(livery["engine_gray"]))
    draw_aircraft_shape(draw, aircraft.family, aircraft.type_code, ctx)
    draw.line((left+15,217,right-60,217), fill=int(livery["stripe_gray"]), width=4)
    windows = 16 if aircraft.family == "widebody" else 10
    for i in range(windows):
        wx = left + 92 + i * max(14, (right-left-170)//max(1, windows-1))
        if not rightward:
            wx = left + right - wx
        draw.ellipse((wx,196,wx+5,201), fill=30)
    marking = str(livery.get("marking") or aircraft.airline_code)
    if marking:
        draw.text((center-min(95,len(marking)*4),160), marking, fill=25, font=fonts["small_bold"])


def _draw_details(draw: ImageDraw.ImageDraw, aircraft: Aircraft, fonts: dict[str, ImageFont.ImageFont], x: int, y: int, route: Any | None, prediction: PassagePrediction | None) -> None:
    livery = airline_livery(aircraft.airline_code)
    draw.text((x,y), aircraft.callsign or aircraft.hex.upper(), font=fonts["heading"], fill=10)
    draw.text((x,y+34), str(livery.get("name",aircraft.airline_code)), font=fonts["small"], fill=55)
    draw.text((x,y+57), aircraft_name(aircraft.type_code), font=fonts["body"], fill=25)
    draw.text((x,y+84), aircraft.registration or "Registration unknown", font=fonts["small"], fill=65)
    draw.text((x,y+111), getattr(route,"label","Route unknown") if route else "Route unknown", font=fonts["small_bold"], fill=30)
    if prediction:
        draw.text((x,y+137), prediction.label, font=fonts["tiny"], fill=45)
    altitude = f"{aircraft.altitude_ft:,.0f} ft" if aircraft.altitude_ft is not None else "unknown"
    speed = f"{aircraft.speed_knots*1.852:,.0f} km/h" if aircraft.speed_knots is not None else "unknown"
    for yy,(label,value) in zip((254,300,346),[("DISTANCE NOW",f"{aircraft.distance_km:.1f} km"),("ALTITUDE",altitude),("SPEED",speed)]):
        draw.text((x,yy), label, font=fonts["tiny"], fill=80)
        draw.text((x,yy+14), value, font=fonts["body_bold"], fill=20)


def _draw_footer(draw: ImageDraw.ImageDraw, weather: Weather | None, stats: dict[str, int], fonts: dict[str, ImageFont.ImageFont], stale_minutes: int | None) -> None:
    draw.line((28,394,772,394), fill=100, width=1)
    if weather:
        temp = f"{weather.temperature_c:.1f} deg C" if weather.temperature_c is not None else "-- deg C"
        clouds = f"{weather.cloud_cover}% cloud cover" if weather.cloud_cover is not None else "cloud cover unknown"
        text = f"WEATHER   {temp} - {clouds}"
    else:
        text = "WEATHER   unavailable"
    draw.text((28,407), text, font=fonts["body_bold"], fill=30)
    passages = int(stats.get("passages",stats.get("unique_aircraft",0)))
    draw.text((28,442), f"Today {passages} passages", font=fonts["small"], fill=55)
    freshness = f" - data {stale_minutes} min old" if stale_minutes else ""
    draw.text((545,442), datetime.now().strftime("Updated %H:%M")+freshness, font=fonts["small"], fill=55)


def _cloud(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    w,h=int(85*scale),int(28*scale)
    draw.arc((x,y,x+w,y+h),180,360,fill=185,width=2)


def _fonts() -> dict[str, ImageFont.ImageFont]:
    def load(size: int, bold: bool=False) -> ImageFont.ImageFont:
        paths=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
        for path in paths:
            if Path(path).exists(): return ImageFont.truetype(path,size)
        return ImageFont.load_default()
    return {"title":load(27,True),"heading":load(23,True),"body":load(16),"body_bold":load(16,True),"small":load(13),"small_bold":load(13,True),"tiny":load(10,True)}
