import pytest

from ai_reel_montage.core.framing import (
    OUTPUT_HEIGHT,
    OUTPUT_WIDTH,
    CropBox,
    FramingError,
    centre_crop,
)


def test_centre_crop_of_1920x1080_is_608_wide_at_x_656() -> None:
    assert centre_crop(1920, 1080) == CropBox(width=608, height=1080, x=656, y=0)


def test_output_size_is_9_16() -> None:
    assert (OUTPUT_WIDTH, OUTPUT_HEIGHT) == (1080, 1920)


def test_crop_width_is_even_and_nearest_with_ties_upward() -> None:
    # 1008 * 9 / 16 = 567 is equidistant from the even 566 and 568 -> up.
    assert centre_crop(1920, 1008).width == 568
    # 1000 * 9 / 16 = 562.5 -> 562 is the nearest even.
    assert centre_crop(1920, 1000).width == 562
    # 1080 * 9 / 16 = 607.5 -> 608 is the nearest even.
    assert centre_crop(1920, 1080).width == 608


def test_x_is_largest_even_not_above_centre() -> None:
    # (1921 - 608) / 2 = 656.5 and (1923 - 608) / 2 = 657.5 both round down to the even 656.
    assert centre_crop(1921, 1080).x == 656
    assert centre_crop(1923, 1080).x == 656


def test_source_exactly_9_16_has_x_zero() -> None:
    assert centre_crop(608, 1080) == CropBox(width=608, height=1080, x=0, y=0)


def test_source_narrower_than_9_16_is_rejected() -> None:
    with pytest.raises(FramingError):
        centre_crop(600, 1080)
