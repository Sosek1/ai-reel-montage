"""Tracking reader on small in-memory documents: windowing, early stop and every rejection."""

import io
import json
from typing import Any

import numpy as np
import pytest

from ai_reel_montage.core.window import FrameRange
from ai_reel_montage.shell.tracking import (
    TrackingError,
    read_ball_track,
    read_metadata,
)


def _doc(samples: list[tuple[int, float | None]], **metadata: Any) -> io.BytesIO:
    meta = {"video_fps": 50.0, "stride": 3, **metadata}
    frames: list[dict[str, Any]] = [
        {"frame_idx": i, "ball": None if x is None else {"x": x, "y": 1.0}, "players": []}
        for i, x in samples
    ]
    return io.BytesIO(json.dumps({"metadata": meta, "frames": frames}).encode())


def _grid(xs: list[float | None], start: int = 0) -> list[tuple[int, float | None]]:
    return [(start + 3 * k, x) for k, x in enumerate(xs)]


def test_returns_samples_from_the_position_before_to_the_position_after_the_window() -> None:
    doc = _doc(_grid([10, 20, 30, 40, 50, 60, 70, 80]))  # frames 0, 3, ..., 21
    track = read_ball_track(doc, FrameRange(7, 6), 3)  # frames 7..12
    assert track.frame_idx.tolist() == [6, 9, 12]
    assert track.x.tolist() == [30.0, 40.0, 50.0]


def test_null_ball_becomes_nan() -> None:
    doc = _doc(_grid([10, None, 30]))
    track = read_ball_track(doc, FrameRange(0, 7), 3)
    assert track.frame_idx.tolist() == [0, 3, 6]
    assert np.isnan(track.x[1])
    assert track.x[[0, 2]].tolist() == [10.0, 30.0]


def test_window_inside_a_run_reaches_back_and_forward_to_positions() -> None:
    doc = _doc(_grid([10, 20, None, None, None, 60, 70]))  # frames 0..18
    track = read_ball_track(doc, FrameRange(7, 4), 3)  # frames 7..10, all inside the run
    assert track.frame_idx.tolist() == [3, 6, 9, 12, 15]
    assert np.isnan(track.x[1:4]).all()
    assert track.x[[0, 4]].tolist() == [20.0, 60.0]


def test_file_without_a_position_before_the_window_starts_at_its_first_sample() -> None:
    doc = _doc(_grid([None, None, None, 40, 50]))
    track = read_ball_track(doc, FrameRange(6, 4), 3)  # frames 6..9
    assert track.frame_idx.tolist() == [0, 3, 6, 9]
    assert np.isnan(track.x[:3]).all()


def test_file_ending_before_the_window_end_stops_at_its_last_sample() -> None:
    doc = _doc(_grid([10, 20, 30, None]))  # frames 0..9, last without ball
    track = read_ball_track(doc, FrameRange(4, 100), 3)
    assert track.frame_idx.tolist() == [3, 6, 9]
    assert np.isnan(track.x[2])


def test_stops_reading_after_the_track_is_complete() -> None:
    good = json.dumps({"metadata": {"video_fps": 50.0, "stride": 3}, "frames": []})[:-2]
    records = [{"frame_idx": 3 * k, "ball": {"x": 100.0 + k}} for k in range(4)]
    body = ",".join(json.dumps(r) for r in records)
    # Valid up to the sample at frame 9; everything after it is garbage.
    doc = io.BytesIO((good + body + ",{ this is not json").encode())
    track = read_ball_track(doc, FrameRange(0, 8), 3)  # last frame 7: complete at 9
    assert track.frame_idx.tolist() == [0, 3, 6, 9]


def test_non_increasing_frame_idx_is_rejected() -> None:
    doc = _doc([(0, 1.0), (3, 1.0), (3, 1.0)])
    with pytest.raises(TrackingError, match="frame 3"):
        read_ball_track(doc, FrameRange(0, 100), 3)
    doc = _doc([(0, 1.0), (6, 1.0), (3, 1.0)])
    with pytest.raises(TrackingError, match="frame 3"):
        read_ball_track(doc, FrameRange(0, 100), 3)


def test_gap_in_frame_idx_is_rejected() -> None:
    doc = _doc([(0, 1.0), (3, 1.0), (9, 1.0)])
    with pytest.raises(TrackingError, match="frame 9"):
        read_ball_track(doc, FrameRange(0, 100), 3)


def test_ball_without_x_is_rejected() -> None:
    raw = {"metadata": {"video_fps": 50.0, "stride": 3}, "frames": [{"frame_idx": 0, "ball": {}}]}
    with pytest.raises(TrackingError, match="frame 0"):
        read_ball_track(io.BytesIO(json.dumps(raw).encode()), FrameRange(0, 10), 3)


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(TrackingError):
        read_ball_track(io.BytesIO(b'{"frames": [{"frame_idx": 0, '), FrameRange(0, 10), 3)


def test_missing_video_fps_is_rejected() -> None:
    doc = io.BytesIO(json.dumps({"metadata": {"stride": 3}, "frames": []}).encode())
    with pytest.raises(TrackingError, match="video_fps"):
        read_metadata(doc)


def test_missing_stride_is_rejected() -> None:
    doc = io.BytesIO(json.dumps({"metadata": {"video_fps": 50.0}, "frames": []}).encode())
    with pytest.raises(TrackingError, match="stride"):
        read_metadata(doc)


def test_metadata_is_read_exactly() -> None:
    meta = read_metadata(_doc([]))
    assert meta.video_fps == 50
    assert meta.stride == 3


def test_window_starting_on_a_sample_starts_at_that_sample() -> None:
    doc = _doc(_grid([10, 20, 30, 40, 50]))  # frames 0, 3, ..., 12
    track = read_ball_track(doc, FrameRange(6, 4), 3)  # frames 6..9
    assert track.frame_idx.tolist() == [6, 9]
