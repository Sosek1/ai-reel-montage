"""Command-line entry point (IO shell). Argument parsing only; no montage logic lives here."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from importlib.metadata import version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-reel-montage",
        description="Build a vertical 9:16 reel from a match recording, tracking data and windows.",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(version("ai-reel-montage"))
        return 0
    build_parser().print_help()
    return 0
