"""ffprobe and ffmpeg behind two typed functions.

ffmpeg exits 0 on a window it cannot honour, so ``render_clip`` renders to ``<output>.partial``,
counts the frames of the result itself and only then renames it over the output. The source may be
neither the output nor that temporary file: both are written or removed here. Both tools get
argument lists, never a shell string: the recording's file name holds spaces, brackets and
non-ASCII characters.
"""

import contextlib
import json
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from ai_reel_montage.core.framing import OUTPUT_HEIGHT, OUTPUT_WIDTH, CropBox
from ai_reel_montage.core.window import FrameRange, duration_time, seek_time


class VideoError(RuntimeError):
    """A probe or render failure; the message includes the tool's stderr."""


@dataclass(frozen=True)
class SourceInfo:
    """Properties of the first video stream of a recording."""

    width: int
    height: int
    fps: Fraction
    total_frames: int


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise VideoError(f"cannot run {args[0]}: {exc}") from exc
    if result.returncode != 0:
        raise VideoError(
            f"{args[0]} failed with status {result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout


def _probe_streams(args: list[str], what: str) -> dict[str, str]:
    try:
        data = json.loads(_run(args))
        streams = data["streams"]
        if not streams:
            raise VideoError(f"{what}: no video stream")
        return {str(k): str(v) for k, v in streams[0].items()}
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise VideoError(f"{what}: unexpected ffprobe output") from exc


def probe_source(path: Path) -> SourceInfo:
    """Read size, frame rate and frame count from the container, without scanning frames."""
    info = _probe_streams(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,nb_frames",
            "-of",
            "json",
            str(path),
        ],
        f"cannot probe {path}",
    )
    try:
        nb_frames = info["nb_frames"]
        if not nb_frames.isdigit():
            raise VideoError(f"{path} does not report a frame count")
        return SourceInfo(
            width=int(info["width"]),
            height=int(info["height"]),
            fps=Fraction(info["r_frame_rate"]),
            total_frames=int(nb_frames),
        )
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        raise VideoError(f"{path} lacks usable video stream properties") from exc


def _count_frames(path: Path) -> int:
    info = _probe_streams(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "json",
            str(path),
        ],
        f"cannot count frames of {path}",
    )
    value = info.get("nb_read_frames", "")
    if not value.isdigit():
        raise VideoError(f"cannot count frames of {path}")
    return int(value)


def partial_path(output: Path) -> Path:
    """The temporary file ``render_clip`` writes before renaming it over ``output``."""
    return output.with_name(output.name + ".partial")


def render_clip(
    source: Path, frames: FrameRange, fps: Fraction, crop: CropBox, output: Path
) -> None:
    """Render ``frames`` of ``source`` as a 1080x1920 clip at ``output``, atomically."""
    partial = partial_path(output)
    # Checked before anything is created: the output is renamed over and the partial file is
    # removed on failure, so a source in either place would be destroyed.
    if source.resolve() in (output.resolve(), partial.resolve()):
        raise VideoError(f"refusing to render: {source} is the output or its temporary file")
    command = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-y",
        "-ss",
        seek_time(frames.start_frame, fps),
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-frames:v",
        str(frames.n_frames),
        "-t",
        duration_time(frames.n_frames, fps),
        "-vf",
        f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y},"
        f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},setsar=1",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-threads",
        "1",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-bitexact",
        "-f",
        "mp4",
        str(partial),
    ]
    published = False
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        _run(command)
        produced = _count_frames(partial)
        if produced != frames.n_frames:
            raise VideoError(
                f"render produced {produced} frames instead of {frames.n_frames}"
                f" (start frame {frames.start_frame})"
            )
        partial.replace(output)
        published = True
    except OSError as exc:
        raise VideoError(f"render failed: {exc}") from exc
    finally:
        if not published:
            # Clean-up must not replace the error being reported.
            with contextlib.suppress(OSError):
                partial.unlink(missing_ok=True)
