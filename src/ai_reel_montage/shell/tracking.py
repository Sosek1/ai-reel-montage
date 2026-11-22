"""Streaming reader for the tracking JSON: only the part of the ball track a window needs.

Rules fixed here (each has a named test):

- The file is streamed with ijson over ``frames.item`` and never loaded whole; reading stops as
  soon as the track is complete, so a window early in the match never touches the rest.
- The track reaches beyond the window on both sides, to the last positioned sample at or before
  the window's first frame and the first positioned sample at or after its last frame, because the
  gap rule of the camera path needs them. Samples without a ball in between stay, as NaN.
- ``frame_idx`` is taken from the file and must advance by exactly ``stride`` from record to
  record: a repeated, decreasing or skipped number is a broken file, never repaired on the fly.
- ijson hands back ``Decimal`` for non-integer numbers; everything is converted here, so only
  ``int``, ``float`` and ``None`` leave this module's ijson wrappers.
"""

import math
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import BinaryIO

import ijson
import numpy as np

from ai_reel_montage.core.camera import BallTrack
from ai_reel_montage.core.window import FrameRange


class TrackingError(RuntimeError):
    """The tracking file cannot be read, is not the expected JSON, or contradicts the recording."""


@dataclass(frozen=True)
class TrackingMetadata:
    """The two header values the engine relies on."""

    video_fps: Fraction
    stride: int


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, int | float | Decimal) and not isinstance(value, bool)


def _sample(record: object) -> tuple[int, float | None]:
    """One ``frames`` element as ``(frame_idx, ball x or None)``; anything else is an error."""
    if not isinstance(record, dict) or "frame_idx" not in record:
        raise TrackingError(f"tracking record without frame_idx: {record!r:.80}")
    frame_idx = record["frame_idx"]
    if not _is_integer(frame_idx):
        raise TrackingError(f"frame {frame_idx!r}: frame_idx is not an integer")
    if "ball" not in record:
        raise TrackingError(f"frame {frame_idx}: record has no ball field")
    ball = record["ball"]
    if ball is None:
        return int(frame_idx), None
    if not isinstance(ball, dict) or not _is_number(ball.get("x")):
        raise TrackingError(
            f"frame {frame_idx}: ball is neither null nor an object with a number x"
        )
    x = float(ball["x"])
    if not math.isfinite(x):
        raise TrackingError(f"frame {frame_idx}: ball x is not finite")
    return int(frame_idx), x


def _samples(stream: BinaryIO, stride: int) -> Iterator[tuple[int, float | None]]:
    """Stream ``frames.item`` as typed samples, checking that ``frame_idx`` advances by stride."""
    previous: int | None = None
    try:
        for record in ijson.items(stream, "frames.item"):
            frame_idx, x = _sample(record)
            if previous is not None and frame_idx != previous + stride:
                raise TrackingError(
                    f"frame {frame_idx}: expected frame {previous + stride} after frame "
                    f"{previous} (stride {stride}); the file repeats, reverses or skips frames"
                )
            previous = frame_idx
            yield frame_idx, x
    except ijson.JSONError as error:
        raise TrackingError(f"tracking file is not valid JSON: {error}") from error


def read_ball_track(stream: BinaryIO, frames: FrameRange, stride: int) -> BallTrack:
    """The ball track a window needs, from the last position at or before it to the first after.

    Stops reading at the first positioned sample at or after the window's last frame.
    """
    first = frames.start_frame
    last = frames.start_frame + frames.n_frames - 1
    kept: list[tuple[int, float | None]] = []
    for frame_idx, x in _samples(stream, stride):
        if frame_idx <= first:
            if x is not None:
                kept.clear()  # a nearer position at or before the window supersedes the rest
            kept.append((frame_idx, x))
            continue
        kept.append((frame_idx, x))
        if x is not None and frame_idx >= last:
            break
    return BallTrack(
        frame_idx=np.array([i for i, _ in kept], dtype=np.int64),
        x=np.array([math.nan if x is None else x for _, x in kept], dtype=np.float64),
    )


def read_metadata(stream: BinaryIO) -> TrackingMetadata:
    """``metadata.video_fps`` (exact) and ``metadata.stride``; both are required."""
    try:
        metadata = next(iter(ijson.items(stream, "metadata")), None)
    except ijson.JSONError as error:
        raise TrackingError(f"tracking file is not valid JSON: {error}") from error
    if not isinstance(metadata, dict):
        raise TrackingError("tracking file has no metadata object")
    fps = metadata.get("video_fps")
    if isinstance(fps, bool) or not isinstance(fps, int | float | Decimal) or fps <= 0:
        raise TrackingError(f"metadata.video_fps is missing or not a positive number: {fps!r}")
    stride = metadata.get("stride")
    if isinstance(stride, bool) or not isinstance(stride, int) or stride <= 0:
        raise TrackingError(f"metadata.stride is missing or not a positive integer: {stride!r}")
    return TrackingMetadata(video_fps=Fraction(fps), stride=stride)


def load_ball_track(path: Path, frames: FrameRange, fps: Fraction) -> BallTrack:
    """Open the tracking file, check it matches the recording's fps, read the window's track."""
    try:
        with path.open("rb") as stream:
            metadata = read_metadata(stream)
            if metadata.video_fps != fps:
                raise TrackingError(
                    f"tracking file was made for {metadata.video_fps} fps, "
                    f"the recording has {fps} fps"
                )
            # ijson reads ahead in blocks: after the metadata read the handle sits far into the
            # file and a second ijson call on it fails with a lexical error.
            stream.seek(0)
            return read_ball_track(stream, frames, metadata.stride)
    except OSError as error:
        raise TrackingError(f"cannot read tracking file {path}: {error}") from error
