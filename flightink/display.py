from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Protocol

from PIL import Image

LOGGER = logging.getLogger(__name__)


class Display(Protocol):
    def show(self, image_path: str | Path) -> None: ...

    def sleep(self) -> None: ...


class PreviewDisplay:
    """PNG-only backend used during development and on non-Pi systems."""

    def show(self, image_path: str | Path) -> None:
        LOGGER.info("Preview bijgewerkt: %s", image_path)

    def sleep(self) -> None:
        return None


class WaveshareDisplay:
    """Adapter for Waveshare 7.5-inch 800x480 black/white modules.

    Waveshare has shipped several hardware revisions. The module name is
    configurable so the project does not hard-code one incompatible revision.
    """

    def __init__(self, module_name: str = "waveshare_epd.epd7in5_V2") -> None:
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            raise RuntimeError(
                f"Waveshare-driver '{module_name}' niet gevonden. "
                "Installeer de officiële waveshare_epd package of gebruik DISPLAY_BACKEND=preview."
            ) from exc
        self.epd = module.EPD()
        self.epd.init()

    def show(self, image_path: str | Path) -> None:
        image = Image.open(image_path).convert("1")
        expected = (int(self.epd.width), int(self.epd.height))
        if image.size != expected:
            image = image.resize(expected)
        self.epd.display(self.epd.getbuffer(image))

    def sleep(self) -> None:
        try:
            self.epd.sleep()
        except Exception:
            LOGGER.exception("E-paper sleep mislukt")


def create_display(backend: str, waveshare_module: str) -> Display:
    normalized = backend.strip().lower()
    if normalized == "waveshare":
        return WaveshareDisplay(waveshare_module)
    if normalized == "preview":
        return PreviewDisplay()
    raise ValueError(f"Onbekende displaybackend: {backend}")
