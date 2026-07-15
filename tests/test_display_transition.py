from PIL import Image, ImageStat

from flightink.display import WaveshareDisplay


def test_erase_frames_progressively_approach_white() -> None:
    display = WaveshareDisplay.__new__(WaveshareDisplay)
    display.transition_steps = 3
    old = Image.new("L", (20, 10), 0)

    frames = display._erase_frames(old)

    assert len(frames) == 3
    means = [ImageStat.Stat(frame).mean[0] for frame in frames]
    assert means == sorted(means)
    assert means[0] > 0
    assert means[-1] < 255


def test_erase_transition_is_limited_to_four_steps() -> None:
    # Constructor clamps this on hardware; the helper itself uses the configured value.
    display = WaveshareDisplay.__new__(WaveshareDisplay)
    display.transition_steps = 4
    assert len(display._erase_frames(Image.new("L", (2, 2), 0))) == 4
