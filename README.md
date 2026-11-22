# AI Reel Montage

CLI montage engine: match recording + ball tracking + 3-5 named timestamp windows -> one
vertical 9:16 reel. See `context/foundation/` for shape notes, PRD and stack.

    uv sync
    uv run pytest

The integration tests need ffmpeg and the recording under `transfer-*/` and skip without them.
Where both are present, run `REEL_REQUIRE_SOURCE=1 uv run pytest` so that a missing input fails
the run instead of skipping it.

## Usage

Cut one window of a recording into a vertical 1080x1920 H.264 clip with the match audio:

    uv run ai-reel-montage --input match.mp4 --window 10:04.78-10:14.78 --output out/clip.mp4

`--window A-B` takes each side as seconds (`604.78`), `mm:ss[.fff]` (`10:04.78`) or
`h:mm:ss[.fff]`. Boundaries snap to the nearest source frame. Exactly one window per run.

A window that is empty, reversed or reaches outside the recording is rejected: nothing is written,
the message names the window and the recording length, and the exit status is 2. A render or probe
failure exits with status 1. The same inputs give a byte-identical clip. An existing output file is
overwritten; the output may be neither the input file nor the tracking file.

### Following the ball

Add the tracking file and the crop follows the ball instead of sitting in the centre:

    uv run ai-reel-montage --input match.mp4 --tracking full_match_tracks.json \
      --window 6:20-6:30 --output out/clip.mp4

The crop is 608x1080 and moves sideways only, centred on the ball in every frame as far as the
picture edge allows. It follows the raw track with no smoothing, so the framing is jittery.
Without `--tracking` the crop stays fixed in the centre of the picture and the success line ends
with `centre crop`.

The tracking file holds a position every third frame and some stretches without a ball. The clip
is always produced; where the file has no position the crop is decided by three rules:

- across a stretch without a ball the crop moves in a straight line from the last known position
  to the next known one;
- when a position is known on one side only (the window touches the start or end of the track),
  the nearest known position is held;
- when the track holds no position at all, the crop stays in the centre.

The success line reports `ball inside crop in A/B tracked frames, C frames on fallback`. `B` counts
the frames for which the file gives a position (at the frame or on both sides of it) and `A` how
many of them have the ball inside the crop; `C` counts the frames framed by the rules above, which
are not checked against any ball. If `A` is less than `B` nothing is written and the exit status
is 1. A window entirely inside a stretch without a ball prints `0/0`.
