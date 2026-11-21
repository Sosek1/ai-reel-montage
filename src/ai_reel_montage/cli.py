"""Command-line entry point (IO shell). Argument parsing and wiring only; no montage logic.

Two kinds of error are kept apart. Usage errors (a missing, unknown or repeated argument) keep
argparse's own behaviour: ``parser.error`` prints the usage line and raises ``SystemExit(2)``.
Engine errors are returned by ``main`` as an exit code with one ``error: ...`` line on stderr:
2 for a bad input, output or window, 1 for a probe or render failure.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from ai_reel_montage.core.framing import FramingError, centre_crop
from ai_reel_montage.core.window import WindowError, parse_window, to_frame_range
from ai_reel_montage.shell.video import VideoError, probe_source, render_clip


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
    parser.add_argument("--output", type=Path, metavar="PATH", help="clip file to write")
    return parser


def _input_exists(path: Path) -> bool:
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
    if args.input is None and args.window is None and args.output is None:
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

    return _run(args.input, args.window[0], args.output)


def _run(source: Path, window_text: str, output: Path) -> int:
    if not _input_exists(source):
        return _fail(f"input file not found: {source}", 2)
    if output.resolve() == source.resolve():
        return _fail("output would overwrite the input", 2)

    try:
        info = probe_source(source)
        frames = to_frame_range(parse_window(window_text), info.fps, info.total_frames)
        crop = centre_crop(info.width, info.height)
        render_clip(source, frames, info.fps, crop, output)
    except (WindowError, FramingError) as exc:
        return _fail(str(exc), 2)
    except VideoError as exc:
        return _fail(str(exc), 1)

    seconds = float(frames.n_frames / info.fps)
    print(f"wrote {output}: {frames.n_frames} frames, {seconds:.2f} s")
    return 0
