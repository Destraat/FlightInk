from __future__ import annotations

import hashlib
import importlib
import logging
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw

LOGGER = logging.getLogger(__name__)


class Display(Protocol):
    def show(self, image_path: str | Path, force: bool = False) -> bool: ...
    def test(self, output_path: str | Path = "output/display-test.png") -> Path: ...
    def sleep(self) -> None: ...


class BaseDisplay:
    def __init__(self) -> None:
        self._last_digest: str | None = None

    def _changed(self, image_path: str | Path, force: bool) -> bool:
        digest = hashlib.sha256(Path(image_path).read_bytes()).hexdigest()
        if not force and digest == self._last_digest:
            LOGGER.info("Display content unchanged; refresh skipped")
            return False
        self._last_digest = digest
        return True

    def test(self, output_path: str | Path = "output/display-test.png") -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("1", (800, 480), 1)
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 5, 794, 474), outline=0, width=5)
        draw.rectangle((35, 45, 220, 170), fill=0)
        for index in range(8):
            x = 260 + index * 55
            draw.rectangle((x, 45, x + 35, 170), fill=0 if index % 2 == 0 else 1, outline=0)
        for y in range(220, 430, 25):
            draw.line((35, y, 765, y), fill=0, width=1 + ((y // 25) % 4))
        draw.text((35, 185), "FlightInk display test - 800x480 - black/white", fill=0)
        image.save(output)
        return output


class PreviewDisplay(BaseDisplay):
    """PNG-only backend used during development and on non-Pi systems."""

    def show(self, image_path: str | Path, force: bool = False) -> bool:
        if not self._changed(image_path, force):
            return False
        LOGGER.info("Preview updated: %s", image_path)
        return True

    def sleep(self) -> None:
        return None


class WaveshareDisplay(BaseDisplay):
    """Adapter for configurable Waveshare 7.5-inch black/white modules."""

    def __init__(self, module_name: str = "waveshare_epd.epd7in5_V2") -> None:
        super().__init__()
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            raise RuntimeError(
                f"Waveshare driver '{module_name}' not found. "
                "Install the official waveshare_epd package or use DISPLAY_BACKEND=preview."
            ) from exc
        self.epd = module.EPD()
        self.epd.init()

    def show(self, image_path: str | Path, force: bool = False) -> bool:
        if not self._changed(image_path, force):
            return False
        image = Image.open(image_path).convert("1")
        expected = (int(self.epd.width), int(self.epd.height))
        if image.size != expected:
            image = image.resize(expected)
        self.epd.display(self.epd.getbuffer(image))
        return True

    def test(self, output_path: str | Path = "output/display-test.png") -> Path:
        output = super().test(output_path)
        self.show(output, force=True)
        return output

    def sleep(self) -> None:
        try:
            self.epd.sleep()
        except Exception:
            LOGGER.exception("E-paper sleep failed")


def create_display(backend: str, waveshare_module: str) -> Display:
    normalized = backend.strip().lower()
    if normalized == "waveshare":
        return WaveshareDisplay(waveshare_module)
    if normalized == "preview":
        return PreviewDisplay()
    raise ValueError(f"Unknown display backend: {backend}")
