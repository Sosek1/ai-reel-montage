"""Piecewise-linear ball-following crop path: arrays in, arrays and text out.

Rules fixed here (each has a named test):

- The ball centre at source frame ``f`` is ``numpy.interp`` (float64) over the samples that have a
  position; outside the first and last such sample it holds the nearest known position.
- Crop x is ``centre - crop_width / 2`` rounded to the nearest even integer, ties upward
  (``2 * floor(v / 2 + 1/2)``; ``numpy.round`` would round ties to even), then clamped to
  ``0 .. source_width - crop_width``. ffmpeg silently rounds an odd x down, so x is even here.
- A frame is a fallback frame unless it coincides with a positioned sample or lies between two
  positioned samples that are neighbours in the track. With no position at all, every frame is a
  fallback frame at the centre crop's x.
- The check never counts a fallback frame as "inside", whatever position the fallback assumed.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ai_reel_montage.core.framing import CropBox
from ai_reel_montage.core.window import FrameRange


class CameraPathError(ValueError):
    """A ball track or a crop path is inconsistent."""


def _frozen_copy[T: np.generic](values: NDArray[T]) -> NDArray[T]:
    copy = values.copy()
    copy.flags.writeable = False
    return copy


@dataclass(frozen=True, eq=False)
class BallTrack:
    """Ball x per sample; NaN means no ball in that sample. ``frame_idx`` strictly increases."""

    frame_idx: NDArray[np.int64]
    x: NDArray[np.float64]

    def __post_init__(self) -> None:
        if self.frame_idx.ndim != 1 or self.x.ndim != 1 or len(self.frame_idx) != len(self.x):
            raise CameraPathError("frame_idx and x must be one-dimensional and of equal length")
        if np.any(np.diff(self.frame_idx) <= 0):
            raise CameraPathError("frame_idx must be strictly increasing")
        object.__setattr__(self, "frame_idx", _frozen_copy(self.frame_idx))
        object.__setattr__(self, "x", _frozen_copy(self.x))


@dataclass(frozen=True, eq=False)
class CropPath:
    """One even crop x per output frame and a flag saying whether the fallback framed it."""

    x: NDArray[np.int64]
    fallback: NDArray[np.bool_]

    def __post_init__(self) -> None:
        if self.x.ndim != 1 or self.fallback.ndim != 1 or len(self.x) != len(self.fallback):
            raise CameraPathError("x and fallback must be one-dimensional and of equal length")
        if np.any(self.x < 0) or np.any(self.x % 2 != 0):
            raise CameraPathError("crop x must be even and non-negative")
        object.__setattr__(self, "x", _frozen_copy(self.x))
        object.__setattr__(self, "fallback", _frozen_copy(self.fallback))


@dataclass(frozen=True)
class FollowCheck:
    """``tracked`` + ``fallback`` is the number of output frames; ``inside`` <= ``tracked``."""

    tracked: int
    inside: int
    fallback: int


def _frame_numbers(frames: FrameRange) -> NDArray[np.int64]:
    return np.arange(frames.start_frame, frames.start_frame + frames.n_frames, dtype=np.int64)


def ball_centre(frames: FrameRange, track: BallTrack) -> NDArray[np.float64]:
    """Ball centre per output frame; all NaN when the track has no positioned sample."""
    positioned = ~np.isnan(track.x)
    if not positioned.any():
        return np.full(frames.n_frames, np.nan, dtype=np.float64)
    return np.asarray(
        np.interp(_frame_numbers(frames), track.frame_idx[positioned], track.x[positioned]),
        dtype=np.float64,
    )


def _fallback_flags(frames: FrameRange, track: BallTrack) -> NDArray[np.bool_]:
    n_samples = len(track.frame_idx)
    if n_samples == 0:
        return np.ones(frames.n_frames, dtype=np.bool_)
    positioned = ~np.isnan(track.x)
    numbers = _frame_numbers(frames)
    # Last sample at or before each frame; -1 when the frame precedes the track.
    before = np.searchsorted(track.frame_idx, numbers, side="right") - 1
    has_before = before >= 0
    safe_before = np.where(has_before, before, 0)
    on_sample = has_before & (track.frame_idx[safe_before] == numbers)
    has_after = before + 1 < n_samples
    safe_after = np.where(has_after, before + 1, 0)
    both_sides = has_before & has_after & positioned[safe_before] & positioned[safe_after]
    tracked = np.where(on_sample, positioned[safe_before], both_sides)
    return np.asarray(~tracked, dtype=np.bool_)


def _even_round_up(values: NDArray[np.float64]) -> NDArray[np.int64]:
    return (2 * np.floor(values / 2 + 0.5)).astype(np.int64)


def crop_path(frames: FrameRange, track: BallTrack, source_width: int, centre: CropBox) -> CropPath:
    """One even, in-range crop x per output frame by the rule in the module docstring."""
    centres = ball_centre(frames, track)
    if np.isnan(centres).all():
        x = np.full(frames.n_frames, centre.x, dtype=np.int64)
    else:
        raw = _even_round_up(centres - centre.width / 2)
        x = np.clip(raw, 0, source_width - centre.width)
    return CropPath(x=x, fallback=_fallback_flags(frames, track))


def ball_inside(path: CropPath, centres: NDArray[np.float64], crop_width: int) -> NDArray[np.bool_]:
    """Per frame ``path.x <= centre < path.x + crop_width``; a NaN centre is never inside."""
    return np.asarray((path.x <= centres) & (centres < path.x + crop_width), dtype=np.bool_)


def check_follow(
    path: CropPath, centres: NDArray[np.float64], source_width: int, crop_width: int
) -> FollowCheck:
    """Count tracked, inside and fallback frames; fallback frames are never inside."""
    if len(centres) != len(path.x):
        raise CameraPathError("centres and crop path differ in length")
    if np.any(path.x > source_width - crop_width):
        raise CameraPathError("crop x beyond the right picture edge")
    tracked = ~path.fallback
    inside = ball_inside(path, centres, crop_width) & tracked
    return FollowCheck(
        tracked=int(tracked.sum()), inside=int(inside.sum()), fallback=int(path.fallback.sum())
    )


def crop_x_expression(x: NDArray[np.int64]) -> str:
    """Flat-sum ffmpeg expression in ``n``: the first value, then one term per change."""
    if len(x) == 0:
        raise CameraPathError("cannot build an expression for an empty crop path")
    parts = [str(int(x[0]))]
    for k in (np.flatnonzero(np.diff(x)) + 1).tolist():
        step = int(x[k]) - int(x[k - 1])
        parts.append(f"{'+' if step > 0 else '-'}{abs(step)}*gte(n,{k})")
    return "".join(parts)
