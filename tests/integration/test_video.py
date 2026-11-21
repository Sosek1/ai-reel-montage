"""Integration tests on 2 s windows of the real AV1 recording."""

import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from ai_reel_montage.core.framing import centre_crop
from ai_reel_montage.core.window import FrameRange, parse_window, seek_time, to_frame_range
from ai_reel_montage.shell.video import SourceInfo, VideoError, probe_source, render_clip

pytestmark = pytest.mark.integration

FPS = Fraction(50)


def _render(source: Path, window: str, output: Path) -> SourceInfo:
    info = probe_source(source)
    frames = to_frame_range(parse_window(window), info.fps, info.total_frames)
    render_clip(source, frames, info.fps, centre_crop(info.width, info.height), output)
    return info


def _ffprobe(path: Path, entries: str, stream: str, *extra: str) -> dict[str, str]:
    out = subprocess.run(
        [
            *["ffprobe", "-v", "error", "-select_streams", stream, *extra],
            *["-show_entries", entries, "-of", "json", str(path)],
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    result: dict[str, str] = json.loads(out)["streams"][0]
    return result


def _video(path: Path) -> dict[str, str]:
    return _ffprobe(
        path,
        "stream=width,height,sample_aspect_ratio,display_aspect_ratio,r_frame_rate,"
        "codec_name,pix_fmt,nb_read_frames",
        "v:0",
        "-count_frames",
    )


def test_probe_reports_source_properties(source_video: Path) -> None:
    info = probe_source(source_video)
    assert (info.width, info.height) == (1920, 1080)
    assert info.fps == 50
    assert info.total_frames == 297_469


def test_clip_is_9_16_with_exact_frame_count(source_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "clip.mp4"
    _render(source_video, "604.78-606.78", out)
    v = _video(out)
    assert (int(v["width"]), int(v["height"])) == (1080, 1920)
    assert v["sample_aspect_ratio"] == "1:1"
    assert v["display_aspect_ratio"] == "9:16"
    assert v["nb_read_frames"] == "100"
    assert Fraction(v["r_frame_rate"]) == 50
    assert v["codec_name"] == "h264"
    assert v["pix_fmt"] == "yuv420p"


def test_audio_matches_video_length(source_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "clip.mp4"
    _render(source_video, "604.78-606.78", out)
    audio = _ffprobe(out, "stream=codec_name,start_time,duration", "a:0")
    video = _ffprobe(out, "stream=start_time,duration", "v:0")
    assert audio["codec_name"] == "aac"
    assert float(audio["start_time"]) == 0
    assert float(audio["duration"]) == pytest.approx(float(video["duration"]), abs=0.001)


def test_off_grid_start_still_gives_exact_frame_count(source_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "clip.mp4"
    _render(source_video, "604.785-606.785", out)
    assert _video(out)["nb_read_frames"] == "100"


def test_two_renders_are_byte_identical(source_video: Path, tmp_path: Path) -> None:
    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    _render(source_video, "604.78-606.78", a)
    _render(source_video, "604.78-606.78", b)
    assert hashlib.sha256(a.read_bytes()).hexdigest() == hashlib.sha256(b.read_bytes()).hexdigest()


def test_last_frames_of_recording_render(source_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "clip.mp4"
    _render(source_video, "5947.38-5949.38", out)
    assert _video(out)["nb_read_frames"] == "100"


def test_seek_time_lands_on_requested_source_frame(source_video: Path) -> None:
    result = subprocess.run(
        [
            *["ffmpeg", "-nostdin", "-v", "error", "-ss", seek_time(30239, FPS)],
            *["-i", str(source_video), "-map", "0:v:0", "-frames:v", "1", "-copyts"],
            *["-f", "framecrc", "-"],
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = [ln for ln in result.stdout.splitlines() if ln and not ln.startswith("#")]
    assert len(rows) == 1
    pts = int(rows[0].split(",")[2].strip())
    assert pts == 30239


def test_failed_render_leaves_no_file(source_video: Path, tmp_path: Path) -> None:
    info = probe_source(source_video)
    out = tmp_path / "sub" / "clip.mp4"
    beyond = FrameRange(start_frame=info.total_frames - 50, n_frames=100)
    with pytest.raises(VideoError):
        render_clip(source_video, beyond, info.fps, centre_crop(info.width, info.height), out)
    assert not out.exists()
    assert not out.with_name("clip.mp4.partial").exists()


def test_source_named_as_the_partial_file_survives(tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4.partial"
    source.write_bytes(b"RECORDING")
    with pytest.raises(VideoError, match="refusing to render"):
        render_clip(source, FrameRange(0, 10), FPS, centre_crop(1920, 1080), tmp_path / "clip.mp4")
    assert source.read_bytes() == b"RECORDING"
    assert not (tmp_path / "clip.mp4").exists()


def test_output_under_a_regular_file_raises_video_error(source_video: Path, tmp_path: Path) -> None:
    blocker = tmp_path / "afile"
    blocker.write_text("x")
    with pytest.raises(VideoError, match="render failed"):
        render_clip(
            source_video, FrameRange(0, 10), FPS, centre_crop(1920, 1080), blocker / "clip.mp4"
        )
    assert blocker.read_text() == "x"
