"""Command-line entry point (IO shell). Argument parsing and wiring only; no montage logic.

Two kinds of error are kept apart. Usage errors (a missing, unknown or repeated argument) keep
argparse's own behaviour: ``parser.error`` prints the usage line and raises ``SystemExit(2)``.
Engine errors are returned by ``main`` as an exit code with one ``error: ...`` line on stderr:
2 for a bad input, tracking file, output or window, 1 for a probe, tracking, camera-path or render
failure.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path

from ai_reel_montage.core.camera import (
    CameraPathError,
    CropPath,
    ball_centre,
    check_follow,
    crop_path,
)
from ai_reel_montage.core.framing import CropBox, FramingError, centre_crop
from ai_reel_montage.core.window import FrameRange, WindowError, parse_window, to_frame_range
from ai_reel_montage.shell.tracking import TrackingError, load_ball_track
from ai_reel_montage.shell.video import VideoError, partial_path, probe_source, render_clip


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-reel-montage",
        description="Build a vertical 9:16 reel from a match recording, tracking data and windows.",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--input", type=Path, metavar="PATH", help="match recording to cut from")
    parser.add_argument(
        "--window",
        action="append",
        metavar="A-B",
        help="window to render; each side is seconds or [h:]mm:ss[.fff], e.g. 10:04.78-10:14.78",
    )
    parser.add_argument(
        "--tracking",
        type=Path,
        metavar="PATH",
        help="ball tracking JSON; the crop follows the ball (optional, default: centre crop)",
    )
    parser.add_argument("--output", type=Path, metavar="PATH", help="clip file to write")
    return parser


def _input_exists(path: Path) -> bool:
    return path.is_file()


def _tracking_exists(path: Path) -> bool:
    return path.is_file()


def _fail(message: str, code: int) -> int:
    print(f"error: {message}", file=sys.stderr)
    return code


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(version("ai-reel-montage"))
        return 0
    if args.input is None and args.window is None and args.output is None and args.tracking is None:
        parser.print_help()
        return 0
    missing = [
        flag
        for flag, value in (
            ("--input", args.input),
            ("--window", args.window),
            ("--output", args.output),
        )
        if value is None
    ]
    if missing:
        parser.error(f"the following arguments are required: {', '.join(missing)}")
    if len(args.window) > 1:
        parser.error("--window may be given only once")

    return _run(args.input, args.window[0], args.output, args.tracking)


def _follow(
    tracking: Path, frames: FrameRange, fps: Fraction, width: int, crop: CropBox
) -> tuple[CropPath, str]:
    """Read the track, build the crop path and its check; raises when the ball leaves the crop."""
    track = load_ball_track(tracking, frames, fps)
    path = crop_path(frames, track, width, crop)
    check = check_follow(path, ball_centre(frames, track), width, crop.width)
    if check.inside < check.tracked:
        raise CameraPathError(
            f"ball outside the crop in {check.tracked - check.inside} of "
            f"{check.tracked} tracked frames"
        )
    summary = (
        f"ball inside crop in {check.inside}/{check.tracked} tracked frames, "
        f"{check.fallback} frames on fallback"
    )
    return path, summary


def _path_problem(source: Path, output: Path, tracking: Path | None) -> str | None:
    """The first reason the given paths cannot be used, checked before anything is probed."""
    if not _input_exists(source):
        return f"input file not found: {source}"
    if output.resolve() == source.resolve():
        return "output would overwrite the input"
    if partial_path(output).resolve() == source.resolve():
        return "the output's temporary file would overwrite the input"
    if tracking is not None and not _tracking_exists(tracking):
        return f"tracking file not found: {tracking}"
    return None


def _run(source: Path, window_text: str, output: Path, tracking: Path | None) -> int:
    problem = _path_problem(source, output, tracking)
    if problem is not None:
        return _fail(problem, 2)

    try:
        # Parsed before the probe: a malformed window is the caller's error (exit 2) whatever
        # the input turns out to be, and costs no subprocess.
        window = parse_window(window_text)
        info = probe_source(source)
        frames = to_frame_range(window, info.fps, info.total_frames)
        crop = centre_crop(info.width, info.height)
        path = None
        summary = "centre crop"
        if tracking is not None:
            path, summary = _follow(tracking, frames, info.fps, info.width, crop)
        render_clip(source, frames, info.fps, crop, output, path=path)
    except (WindowError, FramingError) as exc:
        return _fail(str(exc), 2)
    except (VideoError, TrackingError, CameraPathError) as exc:
        return _fail(str(exc), 1)

    seconds = float(frames.n_frames / info.fps)
    print(f"wrote {output}: {frames.n_frames} frames, {seconds:.2f} s, {summary}")
    return 0
