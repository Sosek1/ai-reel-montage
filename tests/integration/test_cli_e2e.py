"""The real entry point on the real recording, 2 s windows only."""

from pathlib import Path

import pytest

from ai_reel_montage.cli import main
from ai_reel_montage.shell.video import probe_source

pytestmark = pytest.mark.integration


def test_cli_writes_playable_clip(source_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "clip.mp4"
    code = main(["--input", str(source_video), "--window", "604.78-606.78", "--output", str(out)])
    assert code == 0
    info = probe_source(out)
    assert (info.width, info.height) == (1080, 1920)
    assert info.total_frames == 100


def test_cli_out_of_range_window_writes_nothing(source_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "clip.mp4"
    code = main(["--input", str(source_video), "--window", "5945-5955", "--output", str(out)])
    assert code == 2
    assert not out.exists()
    assert not out.with_name("clip.mp4.partial").exists()
