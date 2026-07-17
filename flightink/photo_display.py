from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Iterator

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .models import Aircraft, Weather
from .planespotters import AircraftPhoto

LOGGER = logging.getLogger(__name__)
_ACTIVE_PHOTO: AircraftPhoto | None = None
_INSTALLED = False


@contextmanager
def active_aircraft_photo(photo: AircraftPhoto | None) -> Iterator[None]:
    global _ACTIVE_PHOTO
    previous = _ACTIVE_PHOTO
    _ACTIVE_PHOTO = photo
    try:
        yield
    finally:
        _ACTIVE_PHOTO = previous


def install_photo_renderer(renderer_module: ModuleType) -> None:
    """Wrap the existing aircraft illustration with a cached-photo renderer."""
    global _INSTALLED
    if _INSTALLED:
        return

    original = renderer_module._draw_aircraft_illustration

    def draw_aircraft(
        draw: ImageDraw.ImageDraw,
        fonts: dict[str, ImageFont.ImageFont],
        box: tuple[int, int, int, int],
        aircraft: Aircraft,
        weather: Weather | None,
    ) -> None:
        photo = _ACTIVE_PHOTO
        if photo and photo.image_path and _draw_cached_photo(draw, fonts, box, aircraft, photo):
            return
        original(draw, fonts, box, aircraft, weather)

    renderer_module._draw_aircraft_illustration = draw_aircraft
    _INSTALLED = True


def _draw_cached_photo(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[int, int, int, int],
    aircraft: Aircraft,
    photo: AircraftPhoto,
) -> bool:
    path = Path(photo.image_path or "")
    if not path.is_file():
        return False

    x1, y1, x2, _ = box
    photo_box = (x1 + 16, y1 + 66, x2 - 10, y1 + 300)
    width = photo_box[2] - photo_box[0]
    height = photo_box[3] - photo_box[1]

    try:
        with Image.open(path) as source:
            if source.size == (width, height):
                canvas = source.convert("L")
            else:
                canvas = ImageOps.fit(
                    source.convert("L"),
                    (width, height),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.42),
                )
    except (OSError, ValueError):
        LOGGER.warning("Could not render cached aircraft photo %s", path, exc_info=True)
        return False

    target = getattr(draw, "_image", None)
    if target is None:
        return False
    target.paste(canvas, (photo_box[0], photo_box[1]))
    draw.rectangle(photo_box, outline=92, width=1)

    registration = aircraft.registration or aircraft.hex.upper()
    draw.rectangle((photo_box[0], photo_box[3] - 31, photo_box[2], photo_box[3]), fill=244)
    draw.line((photo_box[0], photo_box[3] - 31, photo_box[2], photo_box[3] - 31), fill=126, width=1)
    draw.text((photo_box[0] + 6, photo_box[3] - 27), registration, font=fonts["small_bold"], fill=24)
    credit = f"Foto: {photo.photographer} / Planespotters.net"
    draw.text((photo_box[0] + 6, photo_box[3] - 14), _truncate(credit, 66), font=fonts["tiny"], fill=58)
    return True


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: max(0, limit - 1)].rstrip() + "…"
