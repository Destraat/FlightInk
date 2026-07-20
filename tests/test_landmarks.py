from PIL import Image, ImageDraw

from flightink.landmarks import _trim_asset_bounds, draw_landmark


def _ink_pixels(name: str) -> int:
    image = Image.new("L", (210, 70), 255)
    draw_landmark(ImageDraw.Draw(image), 2, 2, 207, 67, name)
    return sum(1 for value in image.getdata() if value < 128)


def test_known_landmarks_render_with_strong_eink_contrast() -> None:
    for name in (
        "Eiffeltoren",
        "Sagrada Familia",
        "Big Ben",
        "Colosseum",
        "Westertoren",
        "Stadhuis van Stockholm",
        "Operahuis Oslo",
        "Burj Khalifa",
    ):
        assert _ink_pixels(name) > 100


def test_unknown_landmark_uses_visible_skyline_fallback() -> None:
    assert _ink_pixels("Onbekende bestemming") > 100


def test_trim_asset_bounds_removes_large_white_margins() -> None:
    image = Image.new("L", (120, 60), 244)
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 10, 80, 45), fill=20)

    trimmed = _trim_asset_bounds(image)

    assert trimmed is not None
    assert trimmed.width < image.width
    assert trimmed.height < image.height
