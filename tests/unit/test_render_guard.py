"""Guards of ``render_clip`` that fire before any file or subprocess is touched."""

from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from ai_reel_montage.core.camera import CropPath, crop_x_expression
from ai_reel_montage.core.framing import CropBox
from ai_reel_montage.core.window import FrameRange
from ai_reel_montage.shell.video import (
    VideoError,
    _render_command,
    crop_filter,
    partial_path,
    render_clip,
)

FRAMES = FrameRange(start_frame=0, n_frames=10)
CROP = CropBox(width=608, height=1080, x=656, y=0)


def test_partial_path_appends_suffix_to_the_whole_name() -> None:
    assert partial_path(Path("out/clip.mp4")) == Path("out/clip.mp4.partial")


@pytest.mark.parametrize("source", ["out/clip.mp4", "out/./clip.mp4", "out/clip.mp4.partial"])
def test_source_that_is_the_output_or_its_partial_file_is_refused(source: str) -> None:
    with pytest.raises(VideoError, match="refusing to render"):
        render_clip(Path(source), FRAMES, Fraction(50), CROP, Path("out/clip.mp4"))


def _path(values: list[int]) -> CropPath:
    return CropPath(
        x=np.array(values, dtype=np.int64), fallback=np.zeros(len(values), dtype=np.bool_)
    )


def test_crop_filter_without_path_is_the_fixed_crop_text() -> None:
    assert crop_filter(CROP, None) == "crop=608:1080:656:0"


def test_crop_filter_with_path_quotes_the_expression() -> None:
    path = _path([656, 658, 658, 656])
    assert crop_filter(CROP, path) == (f"crop=608:1080:x='{crop_x_expression(path.x)}':y=0")
    assert "x='656+2*gte(n,1)-2*gte(n,3)'" in crop_filter(CROP, path)


def test_render_command_carries_the_crop_filter_of_the_path() -> None:
    path = _path([656, 700, 700])
    command = _render_command(
        Path("in.mp4"), FrameRange(0, 3), Fraction(50), CROP, Path("out.partial"), path
    )
    assert command[command.index("-vf") + 1] == (
        crop_filter(CROP, path) + ",scale=1080:1920,setsar=1"
    )


def test_path_of_wrong_length_is_refused(tmp_path: Path) -> None:
    out = tmp_path / "sub" / "clip.mp4"
    with pytest.raises(VideoError, match="9 positions for 10 frames"):
        render_clip(Path("in.mp4"), FRAMES, Fraction(50), CROP, out, _path([656] * 9))
    assert not out.parent.exists()


def test_oversized_expression_is_refused(tmp_path: Path) -> None:
    n = 20_000
    path = _path([0, 2] * (n // 2))
    out = tmp_path / "sub" / "clip.mp4"
    with pytest.raises(VideoError, match="100000"):
        render_clip(Path("in.mp4"), FrameRange(0, n), Fraction(50), CROP, out, path)
    assert not out.parent.exists()
