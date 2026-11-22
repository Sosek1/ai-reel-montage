"""Fixtures for the integration tier: the real recording and the ffmpeg tools."""

import os
import shutil
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Set to 1 where the recording and ffmpeg are known to be present: a missing input then fails
# the run instead of skipping, so the tier cannot turn green without verifying anything.
_REQUIRE_ENV = "REEL_REQUIRE_SOURCE"


def _unavailable(reason: str) -> None:
    if os.environ.get(_REQUIRE_ENV) == "1":
        pytest.fail(f"{reason} ({_REQUIRE_ENV}=1 forbids skipping)", pytrace=False)
    pytest.skip(reason)


@pytest.fixture(scope="session")
def source_video() -> Path:
    """The single recording under ``transfer-*/``; skips when it or ffmpeg is absent."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        _unavailable("ffmpeg/ffprobe not on PATH")
    found = sorted(_REPO_ROOT.glob("transfer-*/*.mp4"))
    if not found:
        _unavailable("no recording under transfer-*/")
    if len(found) > 1:
        names = ", ".join(str(p.relative_to(_REPO_ROOT)) for p in found)
        pytest.fail(f"expected a single recording under transfer-*/, found: {names}", pytrace=False)
    return found[0]


@pytest.fixture(scope="session")
def tracking_file() -> Path:
    """The single ``transfer-*/full_match_tracks.json``; skips (or fails) when it is absent."""
    found = sorted(_REPO_ROOT.glob("transfer-*/full_match_tracks.json"))
    if not found:
        _unavailable("no tracking file under transfer-*/")
    if len(found) > 1:
        names = ", ".join(str(p.relative_to(_REPO_ROOT)) for p in found)
        pytest.fail(
            f"expected a single tracking file under transfer-*/, found: {names}", pytrace=False
        )
    return found[0]
