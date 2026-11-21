# AI Reel Montage

CLI montage engine: match recording + ball tracking + 3-5 named timestamp windows -> one
vertical 9:16 reel. See `context/foundation/` for shape notes, PRD and stack.

    uv sync
    uv run pytest

## Usage

Cut one window of a recording into a vertical 1080x1920 H.264 clip with the match audio:

    uv run ai-reel-montage --input match.mp4 --window 10:04.78-10:14.78 --output out/clip.mp4

`--window A-B` takes each side as seconds (`604.78`), `mm:ss[.fff]` (`10:04.78`) or
`h:mm:ss[.fff]`. Boundaries snap to the nearest source frame. Exactly one window per run.

A window that is empty, reversed or reaches outside the recording is rejected: nothing is written,
the message names the window and the recording length, and the exit status is 2. A render or probe
failure exits with status 1. The same inputs give a byte-identical clip. An existing output file is
overwritten; the output may not be the input file.
