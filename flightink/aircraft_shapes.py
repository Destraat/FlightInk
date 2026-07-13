from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PIL import ImageDraw


@dataclass(frozen=True)
class ShapeContext:
    left: int
    right: int
    center: int
    baseline: int
    direction: int
    body_gray: int
    tail_gray: int
    engine_gray: int


def draw_aircraft_shape(draw: ImageDraw.ImageDraw, family: str, type_code: str, ctx: ShapeContext) -> None:
    code = (type_code or "").upper()
    if code.startswith("B74"):
        _draw_747(draw, ctx)
    elif code == "A388":
        _draw_a380(draw, ctx)
    elif code.startswith(("AT", "DH8")) or family == "turboprop":
        _draw_turboprop(draw, ctx)
    elif family == "business_jet":
        _draw_business_jet(draw, ctx)
    elif family == "widebody":
        _draw_widebody(draw, ctx)
    elif family == "regional_jet":
        _draw_regional(draw, ctx)
    else:
        _draw_narrowbody(draw, ctx)


def _mirror_x(ctx: ShapeContext, x: int) -> int:
    return x if ctx.direction > 0 else ctx.left + ctx.right - x


def _poly(ctx: ShapeContext, points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(_mirror_x(ctx, x), y) for x, y in points]


def _draw_narrowbody(draw: ImageDraw.ImageDraw, c: ShapeContext) -> None:
    y = c.baseline
    body = [(c.left, y-21), (c.right-48, y-28), (c.right, y), (c.right-48, y+20), (c.left, y+20)]
    draw.polygon(_poly(c, body), fill=c.body_gray, outline=20)
    draw.polygon(_poly(c, [(c.center-30,y+5),(c.center+115,y+82),(c.center+38,y+76),(c.center-55,y+14)]), fill=160, outline=25)
    draw.polygon(_poly(c, [(c.left+20,y-10),(c.left+62,y-88),(c.left+92,y-10)]), fill=c.tail_gray, outline=25)
    draw.ellipse((_mirror_x(c,c.center+5)-28, y+34, _mirror_x(c,c.center+5)+28, y+60), fill=c.engine_gray, outline=25)


def _draw_regional(draw: ImageDraw.ImageDraw, c: ShapeContext) -> None:
    _draw_narrowbody(draw, c)
    y=c.baseline
    draw.polygon(_poly(c, [(c.left+25,y-12),(c.left+65,y-70),(c.left+90,y-12)]), fill=c.tail_gray, outline=25)
    for offset in (5, 42):
        x=_mirror_x(c,c.left+offset)
        draw.ellipse((x-20,y+7,x+20,y+27), fill=c.engine_gray, outline=25)


def _draw_widebody(draw: ImageDraw.ImageDraw, c: ShapeContext) -> None:
    y=c.baseline
    body=[(c.left,y-30),(c.right-65,y-36),(c.right,y),(c.right-62,y+29),(c.left,y+29)]
    draw.polygon(_poly(c,body),fill=c.body_gray,outline=20)
    draw.polygon(_poly(c,[(c.center-55,y+7),(c.center+135,y+92),(c.center+45,y+83),(c.center-85,y+18)]),fill=150,outline=25)
    draw.polygon(_poly(c,[(c.left+25,y-17),(c.left+72,y-100),(c.left+110,y-17)]),fill=c.tail_gray,outline=25)
    for ox in (-45,55):
        x=_mirror_x(c,c.center+ox)
        draw.ellipse((x-34,y+40,x+34,y+72),fill=c.engine_gray,outline=25)


def _draw_747(draw: ImageDraw.ImageDraw, c: ShapeContext) -> None:
    _draw_widebody(draw,c)
    y=c.baseline
    hump=[(c.left+95,y-31),(c.left+145,y-55),(c.center-5,y-48),(c.center+45,y-31)]
    draw.polygon(_poly(c,hump),fill=c.body_gray,outline=20)


def _draw_a380(draw: ImageDraw.ImageDraw, c: ShapeContext) -> None:
    y=c.baseline
    body=[(c.left,y-38),(c.right-70,y-42),(c.right,y),(c.right-65,y+34),(c.left,y+34)]
    draw.polygon(_poly(c,body),fill=c.body_gray,outline=20)
    draw.line((_mirror_x(c,c.left+85),y-12,_mirror_x(c,c.right-95),y-12),fill=40,width=3)
    draw.polygon(_poly(c,[(c.center-70,y+7),(c.center+145,y+98),(c.center+50,y+88),(c.center-100,y+19)]),fill=150,outline=25)
    draw.polygon(_poly(c,[(c.left+30,y-20),(c.left+82,y-110),(c.left+120,y-20)]),fill=c.tail_gray,outline=25)
    for ox in (-85,-15,55,125):
        x=_mirror_x(c,c.center+ox)
        draw.ellipse((x-25,y+43,x+25,y+70),fill=c.engine_gray,outline=25)


def _draw_turboprop(draw: ImageDraw.ImageDraw, c: ShapeContext) -> None:
    y=c.baseline
    body=[(c.left,y-18),(c.right-35,y-23),(c.right,y),(c.right-38,y+17),(c.left,y+17)]
    draw.polygon(_poly(c,body),fill=c.body_gray,outline=20)
    draw.polygon(_poly(c,[(c.center-65,y-2),(c.center+95,y+52),(c.center+30,y+55),(c.center-85,y+8)]),fill=155,outline=25)
    draw.polygon(_poly(c,[(c.left+18,y-8),(c.left+55,y-72),(c.left+82,y-8)]),fill=c.tail_gray,outline=25)
    for ox in (-35,45):
        x=_mirror_x(c,c.center+ox)
        draw.ellipse((x-22,y+22,x+22,y+43),fill=c.engine_gray,outline=25)
        draw.line((x,y+10,x,y+60),fill=20,width=2)
        draw.line((x-24,y+35,x+24,y+35),fill=20,width=2)


def _draw_business_jet(draw: ImageDraw.ImageDraw, c: ShapeContext) -> None:
    y=c.baseline
    body=[(c.left+35,y-14),(c.right-35,y-22),(c.right,y),(c.right-40,y+14),(c.left+35,y+14)]
    draw.polygon(_poly(c,body),fill=c.body_gray,outline=20)
    draw.polygon(_poly(c,[(c.center-30,y+4),(c.center+95,y+50),(c.center+25,y+48),(c.center-55,y+10)]),fill=155,outline=25)
    draw.polygon(_poly(c,[(c.left+42,y-6),(c.left+72,y-62),(c.left+95,y-6)]),fill=c.tail_gray,outline=25)
    for ox in (45,78):
        x=_mirror_x(c,c.left+ox)
        draw.ellipse((x-16,y+8,x+16,y+25),fill=c.engine_gray,outline=25)
