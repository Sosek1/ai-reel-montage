from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from ai_reel_montage import cli
from ai_reel_montage.cli import main
from ai_reel_montage.core.camera import BallTrack, CropPath
from ai_reel_montage.core.framing import CropBox
from ai_reel_montage.core.window import FrameRange
from ai_reel_montage.shell.tracking import TrackingError
from ai_reel_montage.shell.video import SourceInfo, VideoError

INFO = SourceInfo(width=1920, height=1080, fps=Fraction(50), total_frames=297_469)


class Shell:
    """Replaces the three shell-facing names in ``cli``; records what reached the renderer."""

    def __init__(self) -> None:
        self.probed: list[Path] = []
        self.rendered: list[tuple[Path, FrameRange, Fraction, CropBox, Path]] = []
        self.paths: list[CropPath | None] = []
        self.track_reads: list[tuple[Path, FrameRange, Fraction]] = []
        self.track = BallTrack(
            frame_idx=np.arange(30_237, 30_741, 3, dtype=np.int64),
            x=np.full(168, 1000.0),
        )
        self.track_error: TrackingError | None = None
        self.render_error: VideoError | None = None
        self.probe_error: VideoError | None = None
        self.info = INFO


@pytest.fixture
def shell(monkeypatch: pytest.MonkeyPatch) -> Shell:
    fake = Shell()

    def probe(path: Path) -> SourceInfo:
        fake.probed.append(path)
        if fake.probe_error is not None:
            raise fake.probe_error
        return fake.info

    def render(  # noqa: PLR0913, PLR0917 - mirrors render_clip
        source: Path,
        frames: FrameRange,
        fps: Fraction,
        crop: CropBox,
        output: Path,
        path: CropPath | None = None,
    ) -> None:
        if fake.render_error is not None:
            raise fake.render_error
        fake.rendered.append((source, frames, fps, crop, output))
        fake.paths.append(path)

    def load(path: Path, frames: FrameRange, fps: Fraction) -> BallTrack:
        fake.track_reads.append((path, frames, fps))
        if fake.track_error is not None:
            raise fake.track_error
        return fake.track

    monkeypatch.setattr(cli, "_input_exists", lambda path: True)
    monkeypatch.setattr(cli, "probe_source", probe)
    monkeypatch.setattr(cli, "render_clip", render)
    monkeypatch.setattr(cli, "_tracking_exists", lambda path: True)
    monkeypatch.setattr(cli, "load_ball_track", load)
    return fake


def _args(window: str = "10:04.78-10:14.78", output: str = "out/clip.mp4") -> list[str]:
    return ["--input", "in.mp4", "--window", window, "--output", output]


def test_version_flag_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() != ""


def test_valid_invocation_renders_expected_frame_range(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_args()) == 0
    assert shell.rendered == [
        (
            Path("in.mp4"),
            FrameRange(30239, 500),
            Fraction(50),
            CropBox(608, 1080, 656, 0),
            Path("out/clip.mp4"),
        )
    ]
    out = capsys.readouterr().out
    assert "out/clip.mp4" in out and "500 frames" in out and "10.00 s" in out
    assert out.strip().endswith(", centre crop")


def test_window_past_end_exits_2_and_does_not_render(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_args("5945-5955")) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: ")
    assert "5945-5955" in err and "5949.38" in err
    assert shell.rendered == []


def test_malformed_window_exits_2(shell: Shell, capsys: pytest.CaptureFixture[str]) -> None:
    shell.probe_error = VideoError("ffprobe failed")  # must not be reached, let alone win
    assert main(_args("nonsense")) == 2
    assert capsys.readouterr().err.startswith("error: invalid window")
    assert shell.probed == [] and shell.rendered == []


def test_render_failure_exits_1(shell: Shell, capsys: pytest.CaptureFixture[str]) -> None:
    shell.render_error = VideoError("ffmpeg failed")
    assert main(_args()) == 1
    assert capsys.readouterr().err == "error: ffmpeg failed\n"


def test_missing_argument_exits_2(shell: Shell) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--input", "in.mp4", "--output", "out.mp4"])
    assert exc.value.code == 2


def test_second_window_exits_2(shell: Shell) -> None:
    with pytest.raises(SystemExit) as exc:
        main([*_args(), "--window", "20-30"])
    assert exc.value.code == 2
    assert shell.rendered == []


def test_missing_input_exits_2_and_does_not_probe(
    shell: Shell, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_input_exists", lambda path: False)
    assert main(_args()) == 2
    assert capsys.readouterr().err.startswith("error: ")
    assert shell.probed == []


def test_output_equal_to_input_exits_2_and_does_not_render(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--input", "in.mp4", "--window", "10-20", "--output", "./in.mp4"]) == 2
    assert capsys.readouterr().err == "error: output would overwrite the input\n"
    assert shell.probed == [] and shell.rendered == []


def test_input_named_as_the_partial_file_exits_2_and_does_not_render(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    # render_clip writes and removes <output>.partial; an input with that name would be destroyed.
    argv = ["--input", "out/clip.mp4.partial", "--window", "10-20", "--output", "out/clip.mp4"]
    assert main(argv) == 2
    assert capsys.readouterr().err.startswith("error: ")
    assert shell.probed == [] and shell.rendered == []


def test_probe_failure_exits_1_and_does_not_render(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    shell.probe_error = VideoError("ffprobe failed")
    assert main(_args()) == 1
    assert capsys.readouterr().err == "error: ffprobe failed\n"
    assert shell.rendered == []


def test_source_narrower_than_9_16_exits_2_and_does_not_render(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    shell.info = SourceInfo(width=600, height=1080, fps=Fraction(50), total_frames=297_469)
    assert main(_args()) == 2
    assert capsys.readouterr().err.startswith("error: source 600x1080 is narrower than 9:16")
    assert shell.rendered == []


def _tracked(*extra: str) -> list[str]:
    return [*_args(), "--tracking", "tracks.json", *extra]


def test_without_tracking_the_render_gets_no_path(shell: Shell) -> None:
    assert main(_args()) == 0
    assert shell.paths == [None] and shell.track_reads == []


def test_tracking_path_is_read_for_the_window_frame_range(shell: Shell) -> None:
    assert main(_tracked()) == 0
    assert shell.track_reads == [(Path("tracks.json"), FrameRange(30239, 500), Fraction(50))]
    (path,) = shell.paths
    assert path is not None and len(path.x) == 500


def test_missing_tracking_file_exits_2_and_does_not_probe(
    shell: Shell, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_tracking_exists", lambda path: False)
    assert main(_tracked()) == 2
    assert capsys.readouterr().err == "error: tracking file not found: tracks.json\n"
    assert shell.probed == [] and shell.rendered == []


def test_tracking_error_exits_1_and_does_not_render(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    shell.track_error = TrackingError("bad tracking")
    assert main(_tracked()) == 1
    assert capsys.readouterr().err == "error: bad tracking\n"
    assert shell.rendered == []


def test_tracking_alone_still_requires_the_other_arguments(shell: Shell) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--tracking", "tracks.json"])
    assert exc.value.code == 2


def test_success_line_reports_check_and_fallback_counts(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_tracked()) == 0
    assert capsys.readouterr().out == (
        "wrote out/clip.mp4: 500 frames, 10.00 s, "
        "ball inside crop in 500/500 tracked frames, 0 frames on fallback\n"
    )


def test_window_without_any_position_reports_zero_tracked_frames(
    shell: Shell, capsys: pytest.CaptureFixture[str]
) -> None:
    shell.track = BallTrack(
        frame_idx=np.arange(30_237, 30_741, 3, dtype=np.int64), x=np.full(168, np.nan)
    )
    assert main(_tracked()) == 0
    assert capsys.readouterr().out.endswith(
        "ball inside crop in 0/0 tracked frames, 500 frames on fallback\n"
    )


def test_ball_outside_the_crop_exits_1_and_does_not_render(
    shell: Shell, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken(
        frames: FrameRange, track: BallTrack, source_width: int, centre: CropBox
    ) -> CropPath:
        return CropPath(
            x=np.zeros(frames.n_frames, dtype=np.int64),
            fallback=np.zeros(frames.n_frames, dtype=np.bool_),
        )

    monkeypatch.setattr(cli, "crop_path", broken)  # ball at 1000, crop at 0..608
    assert main(_tracked()) == 1
    assert capsys.readouterr().err == "error: ball outside the crop in 500 of 500 tracked frames\n"
    assert shell.rendered == []
