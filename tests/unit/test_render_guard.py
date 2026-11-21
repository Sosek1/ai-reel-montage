"""Guards of ``render_clip`` that fire before any file or subprocess is touched."""

from fractions import Fraction
from pathlib import Path

import pytest

from ai_reel_montage.core.framing import CropBox
from ai_reel_montage.core.window import FrameRange
from ai_reel_montage.shell.video import VideoError, partial_path, render_clip

FRAMES = FrameRange(start_frame=0, n_frames=10)
CROP = CropBox(width=608, height=1080, x=656, y=0)


def test_partial_path_appends_suffix_to_the_whole_name() -> None:
    assert partial_path(Path("out/clip.mp4")) == Path("out/clip.mp4.partial")


@pytest.mark.parametrize("source", ["out/clip.mp4", "out/./clip.mp4", "out/clip.mp4.partial"])
def test_source_that_is_the_output_or_its_partial_file_is_refused(source: str) -> None:
    with pytest.raises(VideoError, match="refusing to render"):
        render_clip(Path(source), FRAMES, Fraction(50), CROP, Path("out/clip.mp4"))
