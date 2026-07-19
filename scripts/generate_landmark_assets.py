from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
DESTINATIONS_FILE = ROOT / "data" / "destinations.json"
GENERATED_DIR = ROOT / "assets" / "landmarks" / "generated"
ASSET_SIZE = (480, 180)
BACKGROUND = 242


def _slugify(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")


def _seed_for(code: str, city: str, country: str) -> int:
    payload = f"{code}|{city}|{country}".encode("utf-8", errors="ignore")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def _draw_landmark(code: str, city: str, country: str) -> Image.Image:
    rng = random.Random(_seed_for(code, city, country))
    image = Image.new("L", ASSET_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(image)

    width, height = ASSET_SIZE
    ground = rng.randint(128, 140)

    draw.line((0, ground, width - 1, ground), fill=68, width=2)
    draw.line((0, ground + 1, width - 1, ground + 1), fill=122, width=1)

    count = rng.randint(9, 15)
    x = rng.randint(8, 20)
    for _ in range(count):
        building_w = rng.randint(18, 38)
        building_h = rng.randint(24, 84)
        if x + building_w >= width - 8:
            break
        top = ground - building_h
        fill = rng.randint(195, 222)
        draw.rectangle((x, top, x + building_w, ground), outline=58, fill=fill, width=1)
        window_step = rng.randint(7, 10)
        for wy in range(top + 5, ground - 2, window_step):
            draw.line((x + 3, wy, x + building_w - 3, wy), fill=112, width=1)
        x += building_w + rng.randint(4, 10)

    motif = rng.choice(("spire", "bridge", "dome", "wheel", "tower"))
    cx = width // 2
    if motif == "spire":
        draw.polygon(((cx, 26), (cx - 16, ground), (cx + 16, ground)), outline=35, fill=205)
        draw.line((cx, 20, cx, 27), fill=28, width=1)
    elif motif == "bridge":
        left, right = cx - 110, cx + 110
        draw.arc((left, ground - 42, right, ground + 36), 182, 358, fill=48, width=3)
        for pylon in (left + 26, right - 26):
            draw.rectangle((pylon - 4, ground - 58, pylon + 4, ground), outline=48, fill=192, width=2)
        draw.line((left + 8, ground - 8, right - 8, ground - 8), fill=34, width=3)
    elif motif == "dome":
        draw.ellipse((cx - 50, ground - 84, cx + 50, ground + 12), outline=40, fill=212, width=2)
        draw.rectangle((cx - 56, ground - 10, cx + 56, ground), outline=52, fill=206, width=2)
        draw.line((cx, ground - 92, cx, ground - 84), fill=32, width=1)
    elif motif == "wheel":
        draw.ellipse((cx - 48, ground - 96, cx + 48, ground), outline=42, fill=224, width=2)
        for spoke in range(0, 180, 20):
            sx = int(cx + 44 * math.cos(math.radians(spoke)))
            sy = int(ground - 48 + 44 * math.sin(math.radians(spoke)))
            draw.line((cx, ground - 48, sx, sy), fill=108, width=1)
        draw.rectangle((cx - 6, ground - 8, cx + 6, ground), outline=52, fill=186, width=2)
    else:
        draw.rectangle((cx - 22, 30, cx + 22, ground), outline=36, fill=204, width=2)
        draw.rectangle((cx - 14, 18, cx + 14, 30), outline=36, fill=190, width=2)
        draw.polygon(((cx, 8), (cx - 8, 18), (cx + 8, 18)), fill=32)

    for _ in range(rng.randint(2, 4)):
        cloud_x = rng.randint(16, width - 130)
        cloud_y = rng.randint(14, 52)
        cloud_w = rng.randint(40, 100)
        cloud_h = rng.randint(10, 18)
        draw.arc((cloud_x, cloud_y, cloud_x + cloud_w, cloud_y + cloud_h), 180, 360, fill=148, width=1)

    return image


def _load_destinations(path: Path) -> dict[str, dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_assets(destinations: dict[str, dict[str, str]], output_dir: Path, overwrite: bool) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    skipped = 0
    for code in sorted(destinations):
        normalized = code.strip().lower()
        if not normalized:
            continue
        filename = output_dir / f"dest-{normalized}.png"
        if filename.exists() and not overwrite:
            skipped += 1
            continue
        meta = destinations.get(code) or {}
        city = str(meta.get("city") or "")
        country = str(meta.get("country") or "")
        _draw_landmark(code.upper(), city, country).save(filename, format="PNG", optimize=True)
        created += 1
    return created, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic e-ink landmark assets for destinations.")
    parser.add_argument("--destinations", type=Path, default=DESTINATIONS_FILE, help="Path to destinations.json")
    parser.add_argument("--output", type=Path, default=GENERATED_DIR, help="Directory for generated PNG assets")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate existing files")
    args = parser.parse_args()

    destinations = _load_destinations(args.destinations)
    created, skipped = generate_assets(destinations, args.output, overwrite=args.overwrite)
    print(f"Generated {created} assets, skipped {skipped} existing files.")


if __name__ == "__main__":
    main()
