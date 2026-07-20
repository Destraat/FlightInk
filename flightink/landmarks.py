from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

LandmarkDrawer = Callable[[ImageDraw.ImageDraw, int, int, int, int], None]
ROOT = Path(__file__).resolve().parent.parent
LANDMARK_ASSET_DIR = ROOT / "assets" / "landmarks"
LANDMARK_GENERATED_ASSET_DIR = LANDMARK_ASSET_DIR / "generated"


def draw_landmark(
    draw: ImageDraw.ImageDraw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    landmark: str,
) -> None:
    """Draw a strong monochrome destination illustration.

    The drawing intentionally uses dark outlines and large shapes so it remains
    visible after conversion to the Waveshare panel's one-bit output. Unknown
    landmarks receive a full skyline fallback instead of an empty box.
    """
    if _draw_landmark_asset(draw, x1, y1, x2, y2, landmark):
        return

    key = _normalise(landmark)
    drawer = _resolve_drawer(key)

    draw.rounded_rectangle((x1, y1, x2, y2), radius=4, outline=70, width=1, fill=238)
    draw.line((x1 + 3, y2 - 5, x2 - 3, y2 - 5), fill=55, width=2)
    drawer(draw, x1 + 5, y1 + 3, x2 - 5, y2 - 6)


def _draw_landmark_asset(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, landmark: str) -> bool:
    image = getattr(draw, "_image", None)
    if not isinstance(image, Image.Image):
        return False

    for slug in _asset_candidates(landmark):
        asset = _load_asset(slug)
        if asset is None:
            continue
        panel = Image.new("L", (max(1, x2 - x1 + 1), max(1, y2 - y1 + 1)), 244)
        prepared = _prepare_asset(asset)
        inner_w = max(1, panel.size[0] - 10)
        inner_h = max(1, panel.size[1] - 10)
        fitted = _fit_asset(prepared, (inner_w, inner_h))
        # Strong two-tone contrast survives e-ink dithering much better.
        fitted = fitted.point(lambda px: 20 if px < 150 else 236)
        ox = (panel.size[0] - fitted.size[0]) // 2
        oy = max(3, panel.size[1] - fitted.size[1] - 4)
        panel.paste(fitted, (ox, oy))
        ImageDraw.Draw(panel).rounded_rectangle((0, 0, panel.size[0] - 1, panel.size[1] - 1), radius=4, outline=70, width=1)
        image.paste(panel, (x1, y1))
        return True
    return False


def _asset_candidates(landmark: str) -> list[str]:
    name = _normalise(landmark)
    raw = (landmark or "").strip()
    candidates = [_slugify(name)]
    if raw.isalpha() and len(raw) in {3, 4}:
        candidates.insert(0, raw.lower())
    if "sagrada" in name or "barcelona" in name:
        candidates.append("barcelona")
    if "eiffel" in name or "parijs" in name:
        candidates.append("paris")
    candidates.append("default")
    values: list[str] = []
    for item in candidates:
        if not item:
            continue
        values.append(item)
        values.append(f"dest-{item}")
    return values


def _slugify(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")


def _load_asset(slug: str) -> Image.Image | None:
    for base in (LANDMARK_ASSET_DIR, LANDMARK_GENERATED_ASSET_DIR):
        for extension in (".png", ".jpg", ".jpeg", ".webp"):
            candidate = base / f"{slug}{extension}"
            if not candidate.exists():
                continue
            try:
                return Image.open(candidate).convert("L")
            except OSError:
                return None
    return None


def _fit_asset(asset: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    if target_w <= 0 or target_h <= 0:
        return asset
    ratio = min(target_w / asset.width, target_h / asset.height)
    width = max(1, int(asset.width * ratio))
    height = max(1, int(asset.height * ratio))
    return asset.resize((width, height), Image.Resampling.LANCZOS)


def _prepare_asset(asset: Image.Image) -> Image.Image:
    prepared = ImageOps.autocontrast(asset, cutoff=2)
    trimmed = _trim_asset_bounds(prepared)
    if trimmed is None:
        return prepared
    return trimmed


def _trim_asset_bounds(asset: Image.Image) -> Image.Image | None:
    margin = 6
    dark = asset.point(lambda px: 255 if px < 220 else 0)
    dark_rows = [sum(1 for x in range(asset.width) if dark.getpixel((x, y))) for y in range(asset.height)]
    top = _trim_dense_edge(dark_rows, asset.width)
    bottom = _trim_dense_edge(list(reversed(dark_rows)), asset.width)
    if top or bottom:
        asset = asset.crop((0, top, asset.width, max(top + 1, asset.height - bottom)))
        dark = asset.point(lambda px: 255 if px < 220 else 0)
    dark_cols = [sum(1 for y in range(asset.height) if dark.getpixel((x, y))) for x in range(asset.width)]
    left = _trim_dense_edge(dark_cols, asset.height)
    right = _trim_dense_edge(list(reversed(dark_cols)), asset.height)
    if left or right:
        asset = asset.crop((left, 0, max(left + 1, asset.width - right), asset.height))
        dark = asset.point(lambda px: 255 if px < 220 else 0)
    bbox = dark.getbbox()
    if bbox is None:
        return None
    left = max(0, bbox[0] - margin)
    top = max(0, bbox[1] - margin)
    right = min(asset.width, bbox[2] + margin)
    bottom = min(asset.height, bbox[3] + margin)
    trimmed = asset.crop((left, top, right, bottom))
    return trimmed if trimmed.width > 0 and trimmed.height > 0 else None


def _trim_dense_edge(counts: list[int], span: int) -> int:
    trimmed = 0
    dense_threshold = max(1, int(span * 0.75))
    sparse_threshold = max(4, int(span * 0.03))
    for value in counts:
        if value == 0 or value >= dense_threshold:
            trimmed += 1
            continue
        if value <= sparse_threshold and trimmed < 2:
            trimmed += 1
            continue
        break
    return trimmed


def _normalise(value: str) -> str:
    return (value or "").strip().lower().replace("ë", "e").replace("é", "e")


def _resolve_drawer(name: str) -> LandmarkDrawer:
    matches: tuple[tuple[tuple[str, ...], LandmarkDrawer], ...] = (
        (("eiffel",), _eiffel),
        (("sagrada", "barcelona"), _barcelona_scene),
        (("big ben", "westminster"), _big_ben),
        (("colosseum", "colosseum"), _colosseum),
        (("westertoren", "grachten", "amsterdam"), _amsterdam),
        (("brandenburg",), _brandenburg_gate),
        (("main tower", "frankfurt"), _modern_tower),
        (("kleine zeemeermin", "mermaid"), _mermaid),
        (("stadhuis van stockholm", "stockholm city hall"), _stockholm_city_hall),
        (("operahuis oslo", "oslo opera"), _oslo_opera),
        (("stephansdom", "st stephen"), _cathedral),
        (("grossmunster",), _twin_towers),
        (("torre de belem", "belem"), _belem_tower),
        (("burj khalifa",), _burj_khalifa),
        (("vrijheidsbeeld", "statue of liberty"), _statue_of_liberty),
        (("empire state",), _empire_state),
        (("golden gate",), _golden_gate),
        (("atomium",), _atomium),
        (("acropolis", "parthenon"), _temple),
        (("dom van keulen", "cologne cathedral"), _cathedral),
        (("pisa", "leaning tower"), _leaning_tower),
        (("tokyo tower",), _eiffel),
        (("opera house sydney", "sydney opera"), _sydney_opera),
        (("christ the redeemer", "cristo redentor"), _christ_redeemer),
    )
    for needles, drawer in matches:
        if any(needle in name for needle in needles):
            return drawer
    return _skyline


def _barcelona_scene(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    """Detailed Barcelona skyline inspired by Sagrada + city silhouette."""
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)

    def px(rx: float) -> int:
        return x1 + int(w * rx)

    def py(ry: float) -> int:
        return y1 + int(h * ry)

    ground = py(0.93)
    draw.line((px(0.0), ground, px(1.0), ground), fill=35, width=2)

    # Left city silhouette.
    left_blocks = (
        (0.02, 0.62, 0.05),
        (0.07, 0.66, 0.05),
        (0.12, 0.58, 0.06),
        (0.18, 0.64, 0.04),
        (0.22, 0.56, 0.06),
        (0.28, 0.60, 0.05),
    )
    for rx, top, rw in left_blocks:
        bx1, bx2 = px(rx), px(rx + rw)
        by1, by2 = py(top), ground
        draw.rectangle((bx1, by1, bx2, by2), outline=70, fill=222, width=1)
        draw.line((bx1 + 2, by1 + 4, bx2 - 2, by1 + 4), fill=120, width=1)

    # Right side modern tower (Torre Glories style).
    tower_l, tower_r = px(0.84), px(0.95)
    tower_t = py(0.24)
    draw.ellipse((tower_l, tower_t, tower_r, ground), outline=35, fill=210, width=2)
    for i in range(6):
        y = tower_t + int((ground - tower_t) * (i + 1) / 7)
        draw.line((tower_l + 3, y, tower_r - 3, y), fill=95, width=1)

    # Palm trees for foreground texture.
    for trunk_x in (0.74, 0.79, 0.97):
        tx = px(trunk_x)
        draw.line((tx, ground, tx, py(0.79)), fill=40, width=1)
        top = py(0.79)
        draw.line((tx, top, tx - 6, top - 4), fill=60, width=1)
        draw.line((tx, top, tx + 6, top - 4), fill=60, width=1)
        draw.line((tx, top, tx - 5, top - 1), fill=60, width=1)
        draw.line((tx, top, tx + 5, top - 1), fill=60, width=1)

    # Sagrada Familia cluster center.
    spires = (
        (0.37, 0.34, 0.03),
        (0.42, 0.18, 0.035),
        (0.47, 0.08, 0.038),
        (0.52, 0.11, 0.038),
        (0.57, 0.2, 0.034),
        (0.62, 0.31, 0.03),
    )
    for rx, top, rw in spires:
        sx1, sx2 = px(rx), px(rx + rw)
        sy1 = py(top)
        draw.rectangle((sx1, sy1, sx2, ground), outline=35, fill=205, width=1)
        cx = (sx1 + sx2) // 2
        draw.polygon(((cx, sy1 - 5), (sx1 + 1, sy1), (sx2 - 1, sy1)), fill=28)
        # Gothic window/stone texture.
        for row in range(sy1 + 5, ground - 2, max(4, h // 14)):
            draw.line((sx1 + 1, row, sx2 - 1, row), fill=110, width=1)
        draw.line((cx, sy1 + 2, cx, ground - 2), fill=95, width=1)

    # Central basilica base and arches.
    base_l, base_r = px(0.35), px(0.64)
    base_t = py(0.46)
    draw.rectangle((base_l, base_t, base_r, ground), outline=35, fill=215, width=2)
    span = base_r - base_l
    for i in range(8):
        ax = base_l + int((i + 0.5) * span / 8)
        draw.arc((ax - 6, py(0.69), ax + 6, ground), 180, 360, fill=65, width=1)
    for i in range(5):
        y = base_t + int((ground - base_t) * (i + 1) / 6)
        draw.line((base_l + 2, y, base_r - 2, y), fill=120, width=1)

    # Fine foreground hatch to mimic engraved style.
    for xx in range(px(0.0), px(1.0), 7):
        draw.line((xx, ground + 1, xx + 3, ground + 3), fill=145, width=1)


def _eiffel(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    draw.line((cx, y1 + 1, cx - 28, y2), fill=25, width=3)
    draw.line((cx, y1 + 1, cx + 28, y2), fill=25, width=3)
    draw.line((cx - 18, y2 - 18, cx + 18, y2 - 18), fill=35, width=2)
    draw.line((cx - 10, y2 - 35, cx + 10, y2 - 35), fill=35, width=2)
    draw.arc((cx - 13, y2 - 15, cx + 13, y2 + 4), 180, 360, fill=35, width=2)


def _sagrada(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    widths = [13, 15, 17, 15, 13]
    heights = [31, 43, 51, 41, 34]
    total = sum(widths) + 4 * 3
    x = (x1 + x2 - total) // 2
    for width, height in zip(widths, heights):
        draw.rectangle((x, y2 - height, x + width, y2), outline=30, fill=205, width=2)
        draw.polygon(((x + width // 2, y2 - height - 8), (x + 2, y2 - height), (x + width - 2, y2 - height)), fill=45)
        x += width + 3


def _big_ben(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    draw.rectangle((cx - 11, y1 + 13, cx + 11, y2), outline=25, fill=205, width=2)
    draw.rectangle((cx - 14, y1 + 8, cx + 14, y1 + 20), outline=25, fill=185, width=2)
    draw.polygon(((cx, y1), (cx - 10, y1 + 8), (cx + 10, y1 + 8)), fill=35)
    draw.ellipse((cx - 7, y1 + 23, cx + 7, y1 + 37), outline=25, width=2)


def _colosseum(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.rounded_rectangle((x1 + 5, y1 + 10, x2 - 5, y2), radius=12, outline=25, fill=210, width=2)
    for row in range(2):
        top = y1 + 15 + row * 19
        for idx in range(7):
            left = x1 + 12 + idx * max(13, (x2 - x1 - 28) // 7)
            draw.arc((left, top, left + 11, top + 16), 180, 360, fill=35, width=2)


def _amsterdam(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    base = y2
    cx = (x1 + x2) // 2
    draw.rectangle((cx - 8, y1 + 12, cx + 8, base), outline=25, fill=195, width=2)
    draw.polygon(((cx, y1), (cx - 8, y1 + 13), (cx + 8, y1 + 13)), fill=30)
    draw.line((cx, y1 - 1, cx, y1 + 5), fill=25, width=1)
    for offset, height in ((-48, 24), (-28, 31), (24, 27), (43, 21)):
        left = cx + offset
        draw.rectangle((left, base - height, left + 17, base), outline=35, fill=215, width=2)
        draw.polygon(((left + 8, base - height - 7), (left + 1, base - height), (left + 16, base - height)), fill=70)


def _brandenburg_gate(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.rectangle((x1 + 16, y1 + 10, x2 - 16, y1 + 20), outline=25, fill=180, width=2)
    for idx in range(6):
        x = x1 + 20 + idx * max(16, (x2 - x1 - 45) // 5)
        draw.rectangle((x, y1 + 20, x + 7, y2), outline=30, fill=205, width=1)
    draw.line((x1 + 10, y2, x2 - 10, y2), fill=25, width=2)


def _modern_tower(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    draw.polygon(((cx - 13, y2), (cx - 7, y1 + 7), (cx + 8, y1 + 2), (cx + 16, y2)), outline=25, fill=195)
    for y in range(y1 + 12, y2 - 4, 7):
        draw.line((cx - 7, y, cx + 10, y - 1), fill=80, width=1)
    _small_skyline(draw, x1, y2 - 22, x2, y2)


def _mermaid(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    draw.ellipse((cx - 7, y1 + 5, cx + 7, y1 + 19), outline=25, fill=190, width=2)
    draw.line((cx, y1 + 19, cx - 5, y1 + 37), fill=25, width=3)
    draw.line((cx - 5, y1 + 37, cx + 12, y2 - 7), fill=25, width=3)
    draw.arc((cx - 1, y2 - 17, cx + 27, y2 + 1), 170, 350, fill=25, width=2)
    draw.ellipse((cx - 28, y2 - 8, cx + 30, y2 + 5), outline=55, fill=210, width=2)


def _stockholm_city_hall(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.rectangle((x1 + 8, y2 - 27, x2 - 8, y2), outline=30, fill=210, width=2)
    tower_x = x2 - 40
    draw.rectangle((tower_x, y1 + 8, tower_x + 17, y2), outline=25, fill=190, width=2)
    draw.polygon(((tower_x + 8, y1), (tower_x + 2, y1 + 8), (tower_x + 15, y1 + 8)), fill=30)
    for x in range(x1 + 15, x2 - 45, 17):
        draw.arc((x, y2 - 20, x + 10, y2 - 5), 180, 360, fill=45, width=1)


def _oslo_opera(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.polygon(((x1 + 5, y2), (x1 + 49, y1 + 10), (x2 - 12, y1 + 20), (x2 - 3, y2)), outline=25, fill=205)
    draw.line((x1 + 22, y2 - 6, x2 - 16, y1 + 19), fill=60, width=2)
    draw.line((x1 + 3, y2, x2 - 3, y2), fill=25, width=2)


def _cathedral(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    for offset in (-21, 21):
        left = cx + offset - 8
        draw.rectangle((left, y1 + 17, left + 16, y2), outline=25, fill=200, width=2)
        draw.polygon(((left + 8, y1), (left + 1, y1 + 17), (left + 15, y1 + 17)), fill=35)
    draw.rectangle((cx - 18, y2 - 27, cx + 18, y2), outline=35, fill=215, width=2)
    draw.arc((cx - 7, y2 - 19, cx + 7, y2 + 2), 180, 360, fill=35, width=2)


def _twin_towers(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    for left in (cx - 28, cx + 10):
        draw.rectangle((left, y1 + 12, left + 18, y2), outline=25, fill=205, width=2)
        draw.polygon(((left + 9, y1), (left + 2, y1 + 12), (left + 16, y1 + 12)), fill=35)
    draw.rectangle((cx - 9, y2 - 24, cx + 10, y2), outline=35, fill=215, width=2)


def _belem_tower(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    draw.rectangle((cx - 20, y1 + 15, cx + 20, y2), outline=25, fill=205, width=2)
    draw.rectangle((cx - 13, y1 + 4, cx + 13, y1 + 18), outline=25, fill=185, width=2)
    for x in (cx - 18, cx - 5, cx + 8):
        draw.arc((x, y2 - 19, x + 10, y2 - 3), 180, 360, fill=35, width=1)


def _burj_khalifa(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    base = y2
    podium_top = y2 - 10
    draw.line((x1 + 8, base, x2 - 8, base), fill=35, width=2)
    draw.rectangle((cx - 26, podium_top, cx + 26, base), outline=30, fill=214, width=2)
    silhouette = (
        (cx - 24, podium_top),
        (cx - 18, y1 + 64),
        (cx - 14, y1 + 50),
        (cx - 10, y1 + 38),
        (cx - 7, y1 + 24),
        (cx - 4, y1 + 12),
        (cx - 2, y1 + 6),
        (cx, y1),
        (cx + 2, y1 + 8),
        (cx + 5, y1 + 18),
        (cx + 8, y1 + 30),
        (cx + 12, y1 + 46),
        (cx + 17, y1 + 60),
        (cx + 23, podium_top),
    )
    draw.polygon(silhouette, outline=25, fill=188)
    draw.line((cx, y1 - 2, cx, y1 + 4), fill=20, width=1)
    for inset, top_y in ((18, y1 + 60), (13, y1 + 46), (9, y1 + 31), (6, y1 + 20)):
        draw.line((cx - inset, top_y, cx + inset - 1, top_y), fill=105, width=1)
    for side_x, width, height in ((x1 + 18, 16, 16), (x1 + 42, 20, 23), (x2 - 61, 18, 19), (x2 - 33, 14, 13)):
        draw.rectangle((side_x, base - height, side_x + width, base), outline=45, fill=220, width=1)


def _statue_of_liberty(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    draw.rectangle((cx - 14, y2 - 13, cx + 14, y2), outline=25, fill=205, width=2)
    draw.polygon(((cx - 9, y2 - 13), (cx - 5, y1 + 20), (cx + 7, y1 + 20), (cx + 11, y2 - 13)), outline=25, fill=190)
    draw.ellipse((cx - 6, y1 + 9, cx + 6, y1 + 21), outline=25, fill=180, width=2)
    draw.line((cx + 4, y1 + 16, cx + 17, y1 + 2), fill=25, width=3)
    draw.polygon(((cx + 17, y1), (cx + 13, y1 + 7), (cx + 21, y1 + 7)), fill=30)


def _empire_state(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    draw.rectangle((cx - 17, y1 + 22, cx + 17, y2), outline=25, fill=200, width=2)
    draw.rectangle((cx - 11, y1 + 12, cx + 11, y1 + 23), outline=25, fill=185, width=2)
    draw.rectangle((cx - 5, y1 + 5, cx + 5, y1 + 13), outline=25, fill=165, width=1)
    draw.line((cx, y1, cx, y1 + 6), fill=25, width=2)
    _small_skyline(draw, x1, y2 - 19, x2, y2)


def _golden_gate(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    left, right = x1 + 22, x2 - 22
    for x in (left, right):
        draw.rectangle((x - 4, y1 + 5, x + 4, y2), outline=25, fill=185, width=2)
        draw.line((x - 10, y1 + 17, x + 10, y1 + 17), fill=25, width=2)
    draw.arc((left, y1 + 5, right, y2 + 20), 180, 360, fill=25, width=2)
    draw.line((x1 + 5, y2 - 8, x2 - 5, y2 - 8), fill=25, width=3)


def _atomium(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    points = [(x1 + 25, y1 + 10), ((x1 + x2) // 2, y1 + 2), (x2 - 25, y1 + 12), (x1 + 32, y2 - 8), ((x1 + x2) // 2, y2 - 18), (x2 - 30, y2 - 7)]
    for a, b in zip(points, points[1:]):
        draw.line((*a, *b), fill=40, width=2)
    for x, y in points:
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), outline=25, fill=190, width=2)


def _temple(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.polygon(((x1 + 8, y1 + 13), ((x1 + x2) // 2, y1), (x2 - 8, y1 + 13)), outline=25, fill=190)
    draw.rectangle((x1 + 12, y1 + 13, x2 - 12, y1 + 20), outline=25, fill=205, width=2)
    for idx in range(6):
        x = x1 + 18 + idx * max(14, (x2 - x1 - 44) // 5)
        draw.rectangle((x, y1 + 20, x + 6, y2), outline=30, fill=215, width=1)


def _leaning_tower(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    levels = 6
    for idx in range(levels):
        top = y2 - (idx + 1) * 8
        shift = idx * 2
        draw.rectangle((cx - 15 + shift, top, cx + 15 + shift, top + 7), outline=30, fill=208, width=1)


def _sydney_opera(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    base = y2
    starts = [x1 + 16, x1 + 42, x1 + 70]
    heights = [34, 46, 31]
    for start, height in zip(starts, heights):
        draw.pieslice((start, base - height, start + 42, base + height // 2), 190, 315, outline=25, fill=205, width=2)
    draw.line((x1 + 5, base, x2 - 5, base), fill=25, width=2)


def _christ_redeemer(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    cx = (x1 + x2) // 2
    draw.ellipse((cx - 5, y1 + 3, cx + 5, y1 + 13), outline=25, fill=180, width=2)
    draw.line((cx, y1 + 13, cx, y2 - 8), fill=25, width=4)
    draw.line((cx - 29, y1 + 24, cx + 29, y1 + 24), fill=25, width=4)
    draw.polygon(((cx - 11, y2 - 8), (cx + 11, y2 - 8), (cx + 18, y2), (cx - 18, y2)), fill=195, outline=25)


def _skyline(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    _small_skyline(draw, x1, y1, x2, y2)
    cx = (x1 + x2) // 2
    draw.rectangle((cx - 7, y1 + 5, cx + 7, y2), outline=25, fill=185, width=2)
    draw.polygon(((cx, y1), (cx - 5, y1 + 6), (cx + 5, y1 + 6)), fill=30)


def _small_skyline(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    widths = [12, 16, 10, 18, 13, 15, 11]
    heights = [15, 24, 19, 30, 18, 26, 21]
    available = x2 - x1
    spacing = max(2, (available - sum(widths)) // (len(widths) + 1))
    x = x1 + spacing
    for width, height in zip(widths, heights):
        draw.rectangle((x, y2 - height, x + width, y2), outline=30, fill=205, width=2)
        for window_y in range(y2 - height + 5, y2 - 3, 7):
            draw.line((x + 3, window_y, x + width - 3, window_y), fill=90, width=1)
        x += width + spacing
