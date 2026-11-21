"""Fixed centre-crop geometry for a 9:16 reel.

Rules fixed here: the crop is as tall as the source; its width is the even integer nearest to
``height * 9 / 16`` (ties upward); ``x`` is the largest even integer not above the centre offset;
``y`` is 0. A source narrower than the crop is rejected.
"""

from dataclasses import dataclass
from fractions import Fraction

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920


class FramingError(ValueError):
    """The source cannot be framed as 9:16."""


@dataclass(frozen=True)
class CropBox:
    """A crop rectangle in source pixels."""

    width: int
    height: int
    x: int
    y: int


def centre_crop(source_width: int, source_height: int) -> CropBox:
    """Compute the fixed 9:16 centre crop of a source frame."""
    half_width = Fraction(source_height * 9, 32) + Fraction(1, 2)
    width = 2 * (half_width.numerator // half_width.denominator)
    if width > source_width:
        raise FramingError(
            f"source {source_width}x{source_height} is narrower than 9:16 "
            f"(needs at least {width} px of width)"
        )
    x = 2 * ((source_width - width) // 4)
    return CropBox(width=width, height=source_height, x=x, y=0)
