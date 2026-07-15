from __future__ import annotations

import hashlib
import importlib
import logging
import time
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
    """Adapter for configurable Waveshare black/white e-paper modules.

    E-paper cannot perform a true continuous fade. The optional ``erase``
    transition simulates one with a small number of dithered full frames that
    progressively remove black pixels before the new frame is displayed.
    """

    def __init__(
        self,
        module_name: str = "waveshare_epd.epd7in5_V2",
        transition_mode: str = "direct",
        transition_steps: int = 2,
        transition_delay_seconds: float = 0.5,
    ) -> None:
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
        self.transition_mode = transition_mode.strip().lower()
        self.transition_steps = max(1, min(int(transition_steps), 4))
        self.transition_delay_seconds = max(0.0, float(transition_delay_seconds))
        self._last_image: Image.Image | None = None

    def _prepare(self, image: Image.Image) -> Image.Image:
        expected = (int(self.epd.width), int(self.epd.height))
        prepared = image.convert("L")
        if prepared.size != expected:
            prepared = prepared.resize(expected)
        return prepared

    def _display_image(self, image: Image.Image) -> None:
        monochrome = image.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
        self.epd.display(self.epd.getbuffer(monochrome))

    def _erase_frames(self, old_image: Image.Image) -> list[Image.Image]:
        white = Image.new("L", old_image.size, 255)
        return [
            Image.blend(old_image, white, step / (self.transition_steps + 1))
            for step in range(1, self.transition_steps + 1)
        ]

    def show(self, image_path: str | Path, force: bool = False) -> bool:
        if not self._changed(image_path, force):
            return False

        new_image = self._prepare(Image.open(image_path))
        if self._last_image is not None and not force:
            if self.transition_mode == "erase":
                LOGGER.info("Applying %s-step soft erase transition", self.transition_steps)
                for frame in self._erase_frames(self._last_image):
                    self._display_image(frame)
                    if self.transition_delay_seconds:
                        time.sleep(self.transition_delay_seconds)
            elif self.transition_mode == "white":
                LOGGER.info("Applying white intermediate transition")
                self._display_image(Image.new("L", new_image.size, 255))
                if self.transition_delay_seconds:
                    time.sleep(self.transition_delay_seconds)

        self._display_image(new_image)
        self._last_image = new_image.copy()
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


def create_display(
    backend: str,
    waveshare_module: str,
    transition_mode: str = "direct",
    transition_steps: int = 2,
    transition_delay_seconds: float = 0.5,
) -> Display:
    normalized = backend.strip().lower()
    if normalized == "waveshare":
        return WaveshareDisplay(
            waveshare_module,
            transition_mode=transition_mode,
            transition_steps=transition_steps,
            transition_delay_seconds=transition_delay_seconds,
        )
    if normalized == "preview":
        return PreviewDisplay()
    raise ValueError(f"Unknown display backend: {backend}")
