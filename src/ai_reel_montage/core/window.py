"""Window text, frame conversion and validation: numbers in, numbers out.

Rules fixed here (each has a named test):

- Times are parsed exactly (decimal text to ``Fraction``), never through ``float``.
- Each window boundary maps to the nearest source frame, ties upward:
  ``floor(seconds * fps + 1/2)``.
- A window is accepted only when its whole frame range lies inside the recording; the last frame
  of the recording is a valid last frame of a window. Nothing is clamped.
- ffmpeg exits 0 on a window it cannot honour, so this validation is the engine's own.
- Seconds in messages are printed exactly up to three decimals (rounded half up, trailing zeros
  dropped), so the same inputs always give the same text.
"""

import re
from dataclasses import dataclass
from fractions import Fraction

# S[.f] | M:SS[.f] | H:MM:SS[.f]; ranges of the clock fields are checked after matching.
_SECONDS = re.compile(r"(?P<s>\d+(?:\.\d+)?)")
# The fields after a colon are exactly two digits, as in the documented [h:]mm:ss form.
_MINUTES = re.compile(r"(?P<m>\d+):(?P<s>\d{2}(?:\.\d+)?)")
_HOURS = re.compile(r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2}(?:\.\d+)?)")

_MICRO = 10**6


class WindowError(ValueError):
    """A malformed or out-of-range window; the message is shown to the caller verbatim."""


@dataclass(frozen=True)
class Window:
    """A time interval in seconds from the start of the recording."""

    start: Fraction
    end: Fraction


@dataclass(frozen=True)
class FrameRange:
    """A range of whole source frames."""

    start_frame: int
    n_frames: int


def _parse_time(text: str) -> Fraction:
    if (match := _HOURS.fullmatch(text)) is not None:
        hours, minutes, seconds = (
            Fraction(match["h"]),
            Fraction(match["m"]),
            Fraction(match["s"]),
        )
        if minutes >= 60 or seconds >= 60:
            raise WindowError(f"invalid time {text!r}: minutes and seconds must be below 60")
        return hours * 3600 + minutes * 60 + seconds
    if (match := _MINUTES.fullmatch(text)) is not None:
        minutes, seconds = Fraction(match["m"]), Fraction(match["s"])
        if seconds >= 60:
            raise WindowError(f"invalid time {text!r}: seconds must be below 60")
        return minutes * 60 + seconds
    if (match := _SECONDS.fullmatch(text)) is not None:
        return Fraction(match["s"])
    raise WindowError(f"invalid time {text!r}: expected seconds or [h:]mm:ss[.fff]")


def parse_window(text: str) -> Window:
    """Parse ``<time>-<time>`` where a time is ``S[.f]``, ``M:SS[.f]`` or ``H:MM:SS[.f]``."""
    parts = text.split("-")
    if len(parts) != 2:
        raise WindowError(f"invalid window {text!r}: expected <start>-<end>")
    return Window(start=_parse_time(parts[0]), end=_parse_time(parts[1]))


def _nearest_frame(seconds: Fraction, fps: Fraction) -> int:
    return _floor(seconds * fps + Fraction(1, 2))


def _floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _format_seconds(seconds: Fraction) -> str:
    thousandths = _floor(seconds * 1000 + Fraction(1, 2))
    whole, frac = divmod(thousandths, 1000)
    return f"{whole}.{frac:03d}".rstrip("0").rstrip(".")


def to_frame_range(window: Window, fps: Fraction, total_frames: int) -> FrameRange:
    """Convert a window to whole frames and validate it against the recording."""
    start_frame = _nearest_frame(window.start, fps)
    n_frames = _nearest_frame(window.end, fps) - start_frame
    if n_frames < 1:
        raise WindowError("window is empty or reversed: it must cover at least one frame")
    if start_frame >= total_frames or start_frame + n_frames > total_frames:
        raise WindowError(
            f"window {_format_seconds(window.start)}-{_format_seconds(window.end)} s is outside "
            f"the recording ({_format_seconds(Fraction(total_frames) / fps)} s)"
        )
    return FrameRange(start_frame=start_frame, n_frames=n_frames)


def _decimal_rounded_down(seconds: Fraction) -> str:
    micros = _floor(seconds * _MICRO)
    whole, frac = divmod(micros, _MICRO)
    return f"{whole}.{frac:06d}"


def seek_time(start_frame: int, fps: Fraction) -> str:
    """ffmpeg ``-ss`` value: the frame time, six decimals, rounded down.

    ffmpeg snaps a start between two frames upward, so rounding down lands on the intended frame.
    """
    return _decimal_rounded_down(Fraction(start_frame) / fps)


def duration_time(n_frames: int, fps: Fraction) -> str:
    """ffmpeg ``-t`` value for ``n_frames``: six decimals, rounded down."""
    return _decimal_rounded_down(Fraction(n_frames) / fps)
