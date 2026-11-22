"""Tracking reader against the delivered file: grid, runs without a ball, memory, whole match."""

import subprocess
import sys
import textwrap
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from ai_reel_montage.core.camera import BallTrack, crop_path
from ai_reel_montage.core.framing import centre_crop
from ai_reel_montage.core.window import FrameRange
from ai_reel_montage.shell.tracking import (
    TrackingError,
    load_ball_track,
    read_ball_track,
    read_metadata,
)

pytestmark = pytest.mark.integration

SOURCE_WIDTH = 1920
_MEMORY_LIMIT_MB = 200


def _read(path: Path, frames: FrameRange) -> BallTrack:
    with path.open("rb") as stream:
        return read_ball_track(stream, frames, 3)


def test_metadata_fps_matches_the_recording(tracking_file: Path) -> None:
    with tracking_file.open("rb") as stream:
        metadata = read_metadata(stream)
    assert metadata.video_fps == Fraction(50)
    assert metadata.stride == 3


def test_window_samples_lie_on_the_three_frame_grid(tracking_file: Path) -> None:
    track = _read(tracking_file, FrameRange(19000, 500))
    assert track.frame_idx[0] == 18999
    assert track.frame_idx[-1] == 19500
    assert np.all(np.diff(track.frame_idx) == 3)
    assert not np.isnan(track.x).any()
    # Two values of the delivered file itself, so the real-file tier pins the field that is read.
    assert track.x[0] == 310.05
    assert track.x[-1] == 1495.79


def test_load_ball_track_returns_the_window_track(tracking_file: Path) -> None:
    track = load_ball_track(tracking_file, FrameRange(19000, 500), Fraction(50))
    assert len(track.frame_idx) == 168
    assert track.frame_idx[0] == 18999
    assert track.frame_idx[-1] == 19500


def test_window_starting_inside_a_run_without_ball(tracking_file: Path) -> None:
    track = _read(tracking_file, FrameRange(18200, 750))
    assert len(track.frame_idx) == 252
    assert track.frame_idx[0] == 18198
    assert track.frame_idx[-1] == 18951
    assert int(np.isnan(track.x).sum()) == 108


def test_fps_mismatch_is_rejected(tracking_file: Path) -> None:
    with pytest.raises(TrackingError, match="25"):
        load_ball_track(tracking_file, FrameRange(19000, 500), Fraction(25))


def test_late_window_is_read_in_bounded_memory(tracking_file: Path) -> None:
    # The child imports numpy and ijson itself, so its peak is the reader's, not pytest's.
    code = textwrap.dedent(
        """
        import resource
        import sys
        from fractions import Fraction
        from pathlib import Path

        from ai_reel_montage.core.window import FrameRange
        from ai_reel_montage.shell.tracking import load_ball_track

        track = load_ball_track(Path(sys.argv[1]), FrameRange(270000, 750), Fraction(50))
        assert len(track.frame_idx) > 200
        print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(tracking_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    peak_mb = int(result.stdout.strip()) / 1024  # ru_maxrss is in KiB on Linux
    assert peak_mb < _MEMORY_LIMIT_MB, f"peak {peak_mb:.0f} MB; a whole-file load takes ~2600 MB"


def test_ball_is_inside_the_crop_over_the_whole_match(tracking_file: Path) -> None:
    frames = FrameRange(0, 297469)
    track = _read(tracking_file, frames)
    assert len(track.frame_idx) == 99157
    positioned = ~np.isnan(track.x)
    assert int(positioned.sum()) == 94415

    centre = centre_crop(SOURCE_WIDTH, 1080)
    path = crop_path(frames, track, SOURCE_WIDTH, centre)
    width = centre.width
    assert len(path.x) == frames.n_frames
    assert np.all(path.x % 2 == 0)
    assert path.x.min() >= 0
    assert path.x.max() <= SOURCE_WIDTH - width

    # Every positioned sample, compared with the value read from the file at its own frame.
    at_samples = path.x[track.frame_idx[positioned]]
    sample_x = track.x[positioned]
    assert np.all(at_samples <= sample_x)
    assert np.all(sample_x < at_samples + width)

    # Frames between two neighbouring positioned samples stay between those samples' own crops.
    left = np.flatnonzero(positioned[:-1] & positioned[1:])
    crop_at_sample = path.x[track.frame_idx]
    low = np.minimum(crop_at_sample[left], crop_at_sample[left + 1])
    high = np.maximum(crop_at_sample[left], crop_at_sample[left + 1])
    for offset in (1, 2):  # the two frames between samples three frames apart
        between = path.x[track.frame_idx[left] + offset]
        assert np.all((low <= between) & (between <= high))
