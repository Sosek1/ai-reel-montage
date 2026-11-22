"""The real entry point on the real recording, 2 s windows only."""

import hashlib
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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cli_with_tracking_writes_a_ball_following_clip(
    source_video: Path, tracking_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    window = ["--input", str(source_video), "--window", "386-388"]
    followed, centred = tmp_path / "followed.mp4", tmp_path / "centred.mp4"
    code = main([*window, "--tracking", str(tracking_file), "--output", str(followed)])
    out = capsys.readouterr().out
    assert code == 0
    info = probe_source(followed)
    assert (info.width, info.height, info.total_frames) == (1080, 1920, 100)
    assert "ball inside crop in 100/100 tracked frames, 0 frames on fallback" in out
    assert main([*window, "--output", str(centred)]) == 0
    assert _sha(followed) != _sha(centred)


def test_cli_window_inside_a_run_without_ball_still_renders(
    source_video: Path, tracking_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_file = tmp_path / "clip.mp4"
    argv = ["--input", str(source_video), "--tracking", str(tracking_file)]
    code = main([*argv, "--window", "364-366", "--output", str(out_file)])
    out = capsys.readouterr().out
    assert code == 0
    assert probe_source(out_file).total_frames == 100
    assert "ball inside crop in 0/0 tracked frames, 100 frames on fallback" in out
