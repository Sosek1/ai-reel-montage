"""Fixtures for the integration tier: the real recording and the ffmpeg tools."""

import shutil
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def source_video() -> Path:
    """The single recording under ``transfer-*/``; skips when it or ffmpeg is absent."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    found = sorted(_REPO_ROOT.glob("transfer-*/*.mp4"))
    if not found:
        pytest.skip("no recording under transfer-*/")
    return found[0]
