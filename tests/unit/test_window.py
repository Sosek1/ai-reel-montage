from fractions import Fraction

import pytest

from ai_reel_montage.core.window import (
    FrameRange,
    Window,
    WindowError,
    duration_time,
    parse_window,
    seek_time,
    to_frame_range,
)

FPS = Fraction(50)
TOTAL = 297_469  # frames of the real recording: 5949.38 s at 50 fps


def test_parses_seconds_and_clock_forms_to_the_same_window() -> None:
    expected = Window(start=Fraction("604.78"), end=Fraction("614.78"))

    assert parse_window("604.78-614.78") == expected
    assert parse_window("10:04.78-10:14.78") == expected
    assert parse_window("0:10:04.78-0:10:14.78") == expected


def test_parsing_is_exact_not_floating_point() -> None:
    assert parse_window("0.1-0.3") == Window(start=Fraction(1, 10), end=Fraction(3, 10))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "10",
        "10-",
        "-10",
        "10-20-30",
        "-5-10",
        "+5-10",
        "1:60-2:00",
        "1:00:60-2:00:00",
        "1:60:00-2:00:00",
        "a-b",
        "10 -20",
        "1e3-2e3",
        "1:2:3:4-5",
    ],
)
def test_rejects_malformed_window_text(text: str) -> None:
    with pytest.raises(WindowError):
        parse_window(text)


def test_boundary_rounds_to_nearest_frame_ties_upward() -> None:
    # 604.785 s * 50 = 30239.25 -> 30239; 604.79 s * 50 = 30239.5 -> tie, up -> 30240.
    below_tie = to_frame_range(Window(Fraction("604.785"), Fraction("604.785") + 1), FPS, TOTAL)
    tie = to_frame_range(Window(Fraction("604.79"), Fraction("604.79") + 1), FPS, TOTAL)

    assert below_tie.start_frame == 30239
    assert tie.start_frame == 30240


@pytest.mark.parametrize("start", ["604.785", "604.801"])
def test_ten_second_window_is_500_frames_for_off_grid_starts(start: str) -> None:
    window = Window(Fraction(start), Fraction(start) + 10)

    assert to_frame_range(window, FPS, TOTAL).n_frames == 500


def test_window_past_end_is_rejected() -> None:
    with pytest.raises(WindowError) as info:
        to_frame_range(parse_window("5945-5955"), FPS, TOTAL)

    assert str(info.value) == "window 5945-5955 s is outside the recording (5949.38 s)"


def test_window_ending_on_last_frame_is_accepted() -> None:
    result = to_frame_range(parse_window("5947.38-5949.38"), FPS, TOTAL)

    assert result == FrameRange(start_frame=297_369, n_frames=100)


def test_window_starting_after_end_is_rejected() -> None:
    with pytest.raises(WindowError, match="outside the recording"):
        to_frame_range(parse_window("6000-6010"), FPS, TOTAL)


@pytest.mark.parametrize("text", ["10-10", "20-10", "10-10.009"])
def test_empty_or_reversed_window_is_rejected(text: str) -> None:
    with pytest.raises(WindowError, match="at least one frame"):
        to_frame_range(parse_window(text), FPS, TOTAL)


def test_seek_and_duration_are_exact_at_50_fps() -> None:
    assert seek_time(30239, FPS) == "604.780000"
    assert duration_time(500, FPS) == "10.000000"


def test_seek_time_rounds_down_for_non_decimal_rates() -> None:
    fps = Fraction(30000, 1001)
    exact = Fraction(30239) / fps  # 1008.97... s, not representable in decimal
    printed = Fraction(seek_time(30239, fps))

    assert printed <= exact
    assert exact - printed < Fraction(1, 10**6)
    assert seek_time(30239, fps) == "1008.974633"
