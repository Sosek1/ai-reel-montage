# Ball-Following Crop (S-02) Implementation Plan

## Overview

The caller adds the tracking file to the S-01 command and gets a clip whose 608x1080 crop follows
the ball instead of sitting in the centre of the picture. This is roadmap slice S-02 (FR-001,
FR-002, FR-005, US-01), the milestone's north star: the first clip framed by the real tracking
data. The slice introduces the tracking reader, the first camera-path function and a crop that
moves per frame. Smoothing, zoom and multi-window assembly are later slices.

## Current State Analysis

- The CLI takes `--input`, `--window`, `--output` and renders one window with a fixed centre crop
  (`src/ai_reel_montage/cli.py:28-35`, `:74-97`). There is no argument for the tracking file.
- `core/window.py` already yields the window as `FrameRange(start_frame, n_frames)` in source
  frames (`src/ai_reel_montage/core/window.py:40-45`, `:90-101`).
- `core/framing.py` computes one `CropBox` per clip (`src/ai_reel_montage/core/framing.py:20-39`).
- The crop enters ffmpeg in one place, the filter string of `_render_command`
  (`src/ai_reel_montage/shell/video.py:172-173`). `_publishing` (`:118-147`) does not depend on
  how frames are produced.
- No module reads the tracking file. numpy and ijson are declared dependencies and unused
  (`pyproject.toml:8-10`); ijson has no type stubs (`pyproject.toml:41`).
- The tracking file is 398 MB, one sample every third source frame, `frame_idx` being the
  zero-based source frame number with no gap and no drift (`research.md`, findings 1 and 2).
- 73.9% of samples are detected, 21.3% predicted and 4.8% carry no ball. Predicted samples are
  already straight lines between detections. The samples without a ball form 45 runs of 2.82 s to
  25.74 s (`research.md`, finding 3).

## Desired End State

Running

```
uv run ai-reel-montage --input <recording.mp4> --tracking <full_match_tracks.json> \
  --window 6:20-6:30 --output out/clip.mp4
```

writes a 1080x1920 clip of exactly 500 frames in which the crop is centred on the ball in every
frame, as far as the picture edge allows. The command prints in how many of the frames with a
recorded ball position around them the ball is inside the crop, and how many frames were framed
by the fallback. Running it twice gives byte-identical files. Without `--tracking` the command
renders exactly as in S-01; only its success line gains the suffix `, centre crop`.

Verify with `REEL_REQUIRE_SOURCE=1 uv run pytest` and the manual steps in Phase 3.

### Key Discoveries:

- Samples of a window are the elements with `frame_idx` inside its `FrameRange`; an output frame
  has its own sample exactly when its source frame number is a multiple of 3
  (`research.md`, finding 2).
- A crop centred on the ball and clamped to the picture contains the ball centre by construction;
  the ball's x never leaves 3.51–1917.05 (`research.md`, finding 4).
- Crop x must be even: with `yuv420p` an odd x is rounded down by the filter
  (`research.md`, finding 4).
- A flat sum over `n` in the `crop` filter, `sendcmd` and numpy slicing produce the same pixels;
  nested conditionals fail near 100 levels (`research.md`, finding 5).
- Inside the `crop` filter `n` is 0 at the first frame after the input seek
  (`research.md`, finding 5), so the index into the crop path is `n` itself.
- No test stores an output hash (`tests/integration/test_video.py:87-91`).
- Measured during planning, on the real file and recording:
  - a per-frame, linearly interpolated crop path gives an expression of 6 235 characters
    (484 terms) for a 15 s window at 364 s, 5 001 characters for 15 s at 5400 s and 28 406
    characters (2 070 terms) for a 60 s window at 1115 s; ffmpeg accepted the 15 s expression as
    one argument and produced 750 frames;
  - streaming `frames.item`, keeping the last positioned sample before the window and stopping at
    the first positioned sample after it, took 0.45 s at 364 s and 5.93 s at 5400 s;
  - the window starting at frame 18 200 (364.00 s) begins inside a run without a ball: the read
    for 750 frames returns 252 samples, `frame_idx` 18 198 to 18 951, of which 108 (18 201 to
    18 522) have no ball; for the 100 frames of `364-366` every output frame is a fallback frame;
  - frames 19 000 to 19 499 (`6:20-6:30`) have a position in every sample and give 200 distinct
    crop positions; frames 19 300 to 19 399 (`386-388`) move from 796 to the clamp at 1312;
  - ijson returns non-integer numbers as `decimal.Decimal`; `metadata.video_fps` is
    `Decimal("50.0")` and `metadata.stride` is 3.

## What We're NOT Doing

- No smoothing, damping or filtering of the path, and no different treatment of predicted
  samples — S-03. The path here is the raw track, deliberately jittery.
- No zoom and no vertical motion: the crop stays 608x1080 at `y = 0` — S-04.
- No more than one window per run, and no single pass serving several windows — S-05.
- No watchability judgement and no evaluation set — S-06.
- No "hold last known position" inside a run without a ball, and no rejection of a window that
  contains one (user decision; rejection would contradict FR-002).
- No holding of a sample for three frames (user decision): the crop is interpolated per frame.
- No piped-frame rendering and no `sendcmd` file (user decision): the crop path travels as one
  filter expression.
- No reading by byte offset and no side index of the tracking file.
- No use of `y`, `bbox`, `confidence`, `source` or the `players` list.
- No change to the behaviour of a run without `--tracking`.
- No stored output hash; no check of byte identity across machines or ffmpeg builds.
- No whole-file `json.load` anywhere, including tests.

## Implementation Approach

The slice splits where numbers end and bytes begin, as S-01 did.

1. **Pure core** (`core/camera.py`, new). A function from a ball track and a frame range to one
   crop x per output frame, the check that the ball is inside the crop, and the text of the
   filter expression. Arrays and dataclasses in, arrays and strings out. Built with `/10x-tdd`.
2. **IO shell, reading** (`shell/tracking.py`, new). Streams the tracking file with ijson and
   returns the part of the ball track the window needs. Built with `/10x-implement`.
3. **IO shell, rendering, and CLI.** `render_clip` accepts a crop path; `cli.py` gains
   `--tracking` and prints the check result. Built with `/10x-implement`.

Decisions taken in planning:

| Decision | Choice | Why |
| --- | --- | --- |
| Run without a ball (user) | cross it in a straight line between the positions on either side | No frozen crop and no jump; it is the rule the data supplier already applies to gaps under 2.64 s |
| Position missing on one side | hold the nearest known position | Only the last run of the recording has no position after it |
| No position anywhere in the track | the S-01 centre crop | FR-002: produce the clip rather than refuse |
| Frames between samples (user) | linear interpolation, crop moves every frame | Same function as the gap rule; the ball is inside the crop in every frame by construction |
| Predicted samples | used as positions, same as detected | They are already interpolation between detections (6 210 of 6 211) |
| Smoothing | none; named "piecewise-linear follow" | S-03 owns it and replaces this one function |
| Tracking read | ijson stream over `frames.item`, `frame_idx` taken from the file | 35 MB of memory, tolerant of any valid JSON, and the sample before the window comes for free |
| Tracking argument (user) | optional `--tracking`; without it the centre crop | S-01 tests stay as they are; the centre clip stays available for comparison |
| Render route (user) | flat-sum expression in `n` for `crop`'s x | One process, the S-01 command unchanged, the text is a pure function of the path |
| Run without a path | the S-01 filter string, untouched | Keeps S-01's bytes without relying on an equivalence |
| Check | computed on every run over the frames that are not fallback frames; a failure writes no clip | "Verified automatically" becomes a property of the command, not only of the tests, and the count never includes a position the fallback assumed |
| Gap in the records (review) | a step between records different from `metadata.stride` is rejected | A missing record is a broken file, not a stretch without a ball; crossing it silently would not be counted as fallback |
| Even, in-range x (review) | a property of `CropPath`, checked on construction and in the check | S-03 replaces `crop_path`; a path ffmpeg would silently round or clamp must not reach it |

**On the render route.** The three routes cost the same and give the same pictures, so the choice
is about code, not output. That a constant crop written as an expression reproduces S-01's bytes
is a weak argument on its own, because no test pins a hash. It matters as a consequence: the
moving crop is an extension of the existing command rather than a second render path, and the
equivalence is cheap to pin with one test (Phase 3). The cost of this choice is that a
time-varying crop size, which S-04 needs, was not measured for the `crop` filter. If S-04 has to
move to pipes, every output changes once in container bytes; no stored hash exists to break.

**On the tracking read.** A window in minute 90 costs about 5 s of reading next to about 13 s of
encoding. The first run pays the same as every later run, since there is no index to build; a
cold-cache read was not measured. For S-05 the same streaming loop can serve several windows in
one pass, bounded by the 5.4 s full pass (`research.md`, finding 1), so several windows are an
extension of this reader. The reader takes an open stream, not a path, to keep that extension and
its unit tests simple.

**Pure core / IO shell boundary.** Two types cross it, both defined in `core/camera.py`:

- `BallTrack` goes from the shell into the core: source frame numbers and the ball's x, with NaN
  where there is no ball.
- `CropPath` goes from the core into the shell: one even crop x per output frame, and a flag per
  frame saying whether the fallback framed it.

`core/` receives no file, path, stream or JSON object, and returns no ffmpeg argument list. The
filter expression is plain text derived from the path; it lives in the core by the precedent of
`seek_time` (`src/ai_reel_montage/core/window.py:109-114`), so it is unit-tested without ffmpeg.

## Critical Implementation Details

**The rule, stated once.** For an output frame with source frame number `f`:

1. Take the samples that have a position. The ball centre at `f` is the linear interpolation
   between the nearest such sample at or before `f` and the nearest at or after `f`. Where only
   one side exists, it is that side's position. The neighbours may lie outside the window.
   The arithmetic is fixed: `numpy.interp(frame, positioned_frame_idx, positioned_x)` in float64,
   which also holds the nearest known position at both ends.
2. Crop x is `centre - crop_width / 2`, rounded to the nearest even integer with ties upward
   (`2 * floor(v / 2 + 1/2)`), then clamped to `0 … source_width - crop_width` (0 to 1312).
3. With no positioned sample at all, crop x is the centre crop's x for every frame.

A frame is a **fallback frame** unless it coincides with a positioned sample or lies between two
positioned samples that are neighbours in the track. Frames between samples in a normal stretch
are therefore not fallback frames; frames inside a run without a ball are. "Neighbours" means
consecutive elements of the track. The core takes the track as given; that consecutive records
are exactly one stride apart is enforced by the reader (Phase 2), so a stretch without a ball
always arrives as samples with NaN, never as absent samples.

**Rounding must be spelled out.** `numpy.round` rounds ties to even, which is a different rule.
The even rounding uses `floor` as written above, so the same track gives the same integers on
every run. Ties are common, not a corner case: positions have two decimals and interpolation
divides by three, and over the whole match 5 411 of 297 469 frames have `centre - 304` on an odd
integer (measured in review). The tie rule applies to the float64 value `numpy.interp` returns;
another form of the interpolation can land on the other side of a tie, which is why the form is
fixed in step 1.

**The path's guarantees belong to the type.** ffmpeg rounds an odd x down and clamps an
out-of-range x, both silently. `CropPath` therefore refuses an odd or negative x on construction,
and the check refuses an x above `source_width - crop_width`. S-03 replaces `crop_path`, not
these two guards.

**Numbers from ijson are `Decimal`.** They are converted to `float` and `int` inside the reader;
no `Decimal` and no untyped value leaves `shell/tracking.py`.

**The expression has a size limit.** Linux limits a single command-line argument to 131 072
bytes. Measured expressions run at about 9.5 characters per output frame (28 406 for 3 000
frames). `render_clip` refuses an expression above 100 000 characters with a `VideoError` naming
the limit, before any file is created. That is roughly three minutes of footage; the product's
windows are seconds long. Measured in review: ffmpeg accepted one argument of 124 896 characters
(9 000 terms) and the operating system refused 153 897, so the guard refuses nothing that would
have run by a wide margin. Each window is its own ffmpeg run with its own `n`, so several windows
(S-05) multiply runs, not expression length. If a later slice needs longer single renders, the
same expression read from a file (`-/filter:v`, accepted at 438 897 characters) or `sendcmd`
removes the limit without changing pixels (`research.md`, finding 5); neither is built here.

## Phase 1: Crop path in the pure core

### Overview

Everything in S-02 that is numbers in, numbers out, built test-first: the ball track and crop path
types, the piecewise-linear follow rule, the ball-inside-crop check and the filter expression.
Driven by `/10x-tdd`.

### Changes Required:

#### 1. Camera path module

**File**: `src/ai_reel_montage/core/camera.py` (new)

**Intent**: Turn a ball track into one crop position per output frame by the rule in Critical
Implementation Details, and provide the check that proves the ball is inside that crop. This is
the function S-03 replaces with a smoothed one; its inputs and outputs are meant to survive that.

**Contract**:

- `CameraPathError(ValueError)` — a track or a crop path is inconsistent. (Named apart from the
  shell's `TrackingError` on purpose.)
- `BallTrack` — frozen dataclass, `frame_idx: NDArray[np.int64]`, `x: NDArray[np.float64]`.
  Both one-dimensional and of equal length; `frame_idx` strictly increasing; NaN in `x` means no
  ball in that sample. Construction raises `CameraPathError` otherwise. An empty track is valid.
- `CropPath` — frozen dataclass, `x: NDArray[np.int64]`, `fallback: NDArray[np.bool_]`, both of
  length `n_frames`; element `k` belongs to source frame `start_frame + k`. Construction raises
  `CameraPathError` when the two arrays differ in length or any `x` is odd or negative.
- Both dataclasses are declared `frozen=True, eq=False` and store read-only copies of their
  arrays: the generated `__eq__` would raise on arrays, so tests compare the arrays themselves.
- `ball_centre(frames: FrameRange, track: BallTrack) -> NDArray[np.float64]` — the ball centre
  per output frame by step 1 of the rule; all NaN when the track has no positioned sample.
- `crop_path(frames: FrameRange, track: BallTrack, source_width: int, centre: CropBox) -> CropPath`
  — steps 2 and 3 of the rule and the fallback flags. `centre` is the result of `centre_crop`; it
  supplies the crop width and the x used when no position exists.
- `ball_inside(path: CropPath, centres: NDArray[np.float64], crop_width: int) -> NDArray[np.bool_]`
  — per output frame, `path.x <= centre < path.x + crop_width`. A NaN centre gives `False`.
- `FollowCheck` — frozen dataclass of three integers: `tracked` (frames that are not fallback
  frames), `inside` (tracked frames where `ball_inside` is true) and `fallback` (fallback
  frames); `tracked + fallback` is the number of output frames.
- `check_follow(path: CropPath, centres: NDArray[np.float64], source_width: int, crop_width: int) -> FollowCheck`
  — the counts above. Raises `CameraPathError` when any `path.x` exceeds
  `source_width - crop_width` or when `centres` and the path differ in length. Fallback frames
  are never counted as inside, whatever position the fallback assumed for them; the check passes
  when `inside == tracked`.
- `crop_x_expression(x: NDArray[np.int64]) -> str` — the first value as a decimal integer,
  followed by one term per index `k >= 1` where the value changes: `+<d>*gte(n,<k>)` for a
  positive step `d`, `-<d>*gte(n,<k>)` for a negative one. A constant path gives the number
  alone. No whitespace, no nesting.
- The module imports only `numpy`, `dataclasses` and the two existing core modules.

#### 2. Unit tests

**File**: `tests/unit/test_camera.py` (new)

**Intent**: Pin the rule's boundaries by name, so S-03 replaces the path knowingly and nothing
else changes by accident. All tracks are written by hand in the test; none is read from disk.

**Contract**: the tests include at least these named cases, with source width 1920 and the
608-wide centre crop at x 656.

- `test_crop_is_centred_on_the_ball_at_a_sample_frame` — ball x 1000 gives crop x 696.
- `test_frames_between_samples_are_interpolated_linearly` — samples at frames 0 (x 1000) and
  3 (x 1030): frames 1 and 2 give crop x 706 and 716.
- `test_crop_x_is_even_with_ties_upward` — ball x 961 gives crop x 658, not 656.
- `test_interpolated_tie_rounds_upward` — samples at frames 0 (x 1000.0) and 3 (x 1003.0):
  frame 1 has centre 1001 and crop x 698.
- `test_crop_is_clamped_at_both_picture_edges` — ball x 3.51 gives 0, ball x 1917.05 gives 1312,
  and `ball_inside` is true for both.
- `test_run_without_ball_is_crossed_in_a_straight_line` — samples at frames 0 (x 600), 3 and 6
  (no ball), 9 (x 1500): the centre at frame 3 is 900; frames 1 to 8 are fallback frames,
  frames 0 and 9 are not.
- `test_window_starting_inside_a_run_uses_the_sample_before_it` — the window starts at frame 4
  of the track above; frame 4 has centre 1000.
- `test_no_position_after_the_window_holds_the_last_known` and
  `test_no_position_before_the_window_holds_the_first_known` — the held frames are fallback
  frames.
- `test_track_without_any_position_gives_the_centre_crop` — every x is 656, every frame is a
  fallback frame; also for an empty track.
- `test_window_not_starting_on_the_sample_grid` — start frame 19 001 with samples at 18 999 and
  19 002.
- `test_ball_is_inside_the_crop_in_every_frame_across_a_large_jump` — two neighbouring samples
  595 px apart (the largest step in the recording).
- `test_ball_inside_reports_a_ball_outside_the_crop` — a hand-made path away from the ball gives
  `False`, so the check is shown able to fail.
- `test_check_counts_only_frames_that_are_not_fallback` — the run-without-ball track above over
  frames 0 to 9 gives `tracked` 2, `inside` 2, `fallback` 8.
- `test_check_of_a_track_without_any_position_counts_nothing_as_tracked` — `tracked` 0,
  `inside` 0, `fallback` equal to the number of frames.
- `test_check_reports_a_tracked_frame_outside_the_crop` — a hand-made path gives
  `inside < tracked`.
- `test_check_rejects_a_path_beyond_the_right_edge` — x 1314 with source width 1920.
- `test_crop_path_with_odd_x_is_rejected`, `test_crop_path_with_negative_x_is_rejected`,
  `test_crop_path_with_unequal_array_lengths_is_rejected`.
- `test_expression_of_a_constant_path_is_a_single_number`,
  `test_expression_has_one_term_per_change`, and
  `test_expression_evaluates_back_to_the_path` — the sum evaluated in Python for every `n` equals
  the path.
- `test_track_with_non_increasing_frames_is_rejected`,
  `test_track_with_unequal_array_lengths_is_rejected`.

### Success Criteria:

#### Automated Verification:

- Unit tests pass: `uv run pytest -m "not integration"`
- Type checking passes: `uv run mypy`
- Linting passes: `uv run ruff check`
- Formatting is clean: `uv run ruff format --check src tests`
- `core/` imports none of `subprocess`, `os`, `pathlib`, `json`, `ijson`, `time`, `random`:
  `! grep -rnE "^\s*(import|from) (subprocess|os|pathlib|json|ijson|time|random)\b" src/ai_reel_montage/core`
- `core/` does not import `shell` or `cli`:
  `! grep -rnE --include='*.py' "^\s*(import|from) .*\b(shell|cli)\b" src/ai_reel_montage/core`

**Implementation Note**: This phase has no manual verification. After the automated checks pass,
commit and stop; Phase 2 is a separate session. Phase blocks use plain bullets — the corresponding
`- [ ]` checkboxes live in the `## Progress` section at the bottom of the plan.

---

## Phase 2: Tracking reader in the IO shell

### Overview

Read from the 398 MB file the part of the ball track one window needs, in bounded memory, and
prove on the whole match that the Phase 1 path keeps every recorded ball position inside the crop.
Driven by `/10x-implement`.

### Changes Required:

#### 1. Tracking reader

**File**: `src/ai_reel_montage/shell/tracking.py` (new)

**Intent**: Stream the tracking JSON and hand the core a typed `BallTrack`. The reader reaches
beyond the window on both sides as far as the nearest positioned sample, because the gap rule
needs them; it never holds more than the window plus one run without a ball.

**Contract**:

- `TrackingError(RuntimeError)` — the file cannot be opened, is not the expected JSON, or
  contradicts the recording.
- `TrackingMetadata` — frozen dataclass, `video_fps: Fraction`, `stride: int`.
- `read_ball_track(stream: BinaryIO, frames: FrameRange, stride: int) -> BallTrack` — iterates
  `frames.item` with ijson and stops reading as soon as the track is complete. The returned
  track starts at the last positioned sample with `frame_idx <= frames.start_frame` (at the
  file's first sample when there is none) and ends at the first positioned sample with
  `frame_idx >=` the window's last frame (at the file's last sample when there is none). Samples
  without a ball in between are kept, with NaN.
- A sample contributes `frame_idx` (integer) and `ball.x` (number) or a null `ball`. A record
  lacking `frame_idx`, a `ball` that is neither null nor an object with a numeric `x`, or a
  `frame_idx` that is not exactly `stride` above the previous record's raises `TrackingError`
  naming the frame. This covers a repeated or decreasing `frame_idx` and a gap in the records
  alike. Truncated or invalid JSON raises `TrackingError`.
- `read_metadata(stream: BinaryIO) -> TrackingMetadata` — `metadata.video_fps`, converted
  exactly, and `metadata.stride`. Raises `TrackingError` when either is absent or `stride` is not
  a positive integer.
- `load_ball_track(path: Path, frames: FrameRange, fps: Fraction) -> BallTrack` — opens the file,
  raises `TrackingError` when the metadata's `video_fps` differs from `fps` (the message gives
  both values), **rewinds the stream to byte 0**, then returns `read_ball_track` with the
  metadata's stride. An `OSError` becomes a `TrackingError`. The rewind is required: ijson reads
  ahead in blocks, so after the metadata read the handle is at byte 65 536 and a second ijson
  call on it fails with a lexical error (measured in review).
- The two ijson calls are wrapped so that only `int`, `float` and `None` leave them; nothing
  typed `Any` is returned from a public function.
- `src/ai_reel_montage/shell/__init__.py` docstring stays accurate (it already names
  tracking-JSON streaming).

#### 2. Reader unit tests

**File**: `tests/unit/test_tracking.py` (new)

**Intent**: Cover the windowing and error contract on small JSON documents held in memory
(`io.BytesIO`), with no file on disk.

**Contract**: the tests include at least these named cases.

- `test_returns_samples_from_the_position_before_to_the_position_after_the_window`.
- `test_null_ball_becomes_nan`.
- `test_window_inside_a_run_reaches_back_and_forward_to_positions`.
- `test_file_without_a_position_before_the_window_starts_at_its_first_sample`.
- `test_file_ending_before_the_window_end_stops_at_its_last_sample`.
- `test_stops_reading_after_the_track_is_complete` — the document is invalid JSON after the last
  needed sample, and the read still succeeds.
- `test_non_increasing_frame_idx_is_rejected`, `test_gap_in_frame_idx_is_rejected` (records at
  0, 3 and 9 with stride 3), `test_ball_without_x_is_rejected`,
  `test_invalid_json_is_rejected`, `test_missing_video_fps_is_rejected`,
  `test_missing_stride_is_rejected`.

#### 3. Integration fixture

**File**: `tests/integration/conftest.py`

**Intent**: Locate the real tracking file the same way the recording is located, with the same
skip-or-fail rule.

**Contract**: a session-scoped `tracking_file` fixture returning the single
`transfer-*/full_match_tracks.json`; it goes through `_unavailable` when none is found, so
`REEL_REQUIRE_SOURCE=1` turns a missing file into a failure.

#### 4. Integration tests on the real file

**File**: `tests/integration/test_tracking.py` (new)

**Intent**: Prove on the delivered file that the reader returns what research measured, in
bounded memory, and that the path keeps the ball inside the crop over the whole match. All tests
carry `@pytest.mark.integration`. None calls `json.load` on the file.

**Contract**: the tests include at least these named cases.

- `test_metadata_fps_matches_the_recording` — `read_metadata` gives fps 50 and stride 3.
- `test_window_samples_lie_on_the_three_frame_grid` — `FrameRange(19000, 500)`: `frame_idx` runs
  from 18 999 to 19 500 in steps of 3, with no NaN.
- `test_load_ball_track_returns_the_window_track` —
  `load_ball_track(path, FrameRange(19000, 500), Fraction(50))` returns 168 samples from 18 999
  to 19 500. This is the only test of the successful path through both reads on one handle.
- `test_window_starting_inside_a_run_without_ball` — `FrameRange(18200, 750)`: 252 samples,
  first `frame_idx` 18 198, last 18 951, 108 NaN.
- `test_fps_mismatch_is_rejected` — `load_ball_track` with fps 25 raises `TrackingError`.
- `test_late_window_is_read_in_bounded_memory` — a child interpreter reads
  `FrameRange(270000, 750)`; its peak resident set size is below 200 MB (measured: about 35 MB
  streamed, 2 589 MB for a whole-file load).
- `test_ball_is_inside_the_crop_over_the_whole_match` — the track for
  `FrameRange(0, 297469)` has 99 157 samples, 94 415 with a position; with `crop_path` for source
  width 1920, every positioned sample satisfies `path.x[f] <= x < path.x[f] + 608` at its own
  frame `f`, compared against the values read from the file, not against `ball_centre`. Every
  `path.x` is even and within 0 to 1312. For every frame between two neighbouring positioned
  samples, `path.x` lies between those two samples' own crop x values, inclusive, so the frames
  between samples are also checked without `ball_centre`.

### Success Criteria:

#### Automated Verification:

- Integration tests pass with the source required: `REEL_REQUIRE_SOURCE=1 uv run pytest -m integration`
- Unit tests pass: `uv run pytest -m "not integration"`
- Type checking passes: `uv run mypy`
- Linting passes: `uv run ruff check`
- Formatting is clean: `uv run ruff format --check src tests`
- The ball is inside the crop at every positioned sample of the match:
  `REEL_REQUIRE_SOURCE=1 uv run pytest tests/integration/test_tracking.py -k whole_match`
- No whole-file load of the tracking JSON exists:
  `! grep -rnE "json\.load\(" src tests/integration/test_tracking.py`

**Implementation Note**: This phase has no manual verification; `REEL_REQUIRE_SOURCE=1` makes a
missing tracking file a failure instead of a skip. After the automated checks pass, commit and
stop; Phase 3 is a separate session.

---

## Phase 3: Moving crop in the render, `--tracking` on the CLI, end-to-end check

### Overview

Give the render a crop that moves, expose the tracking file on the command line, and confirm on a
real clip that the picture follows the ball. Driven by `/10x-implement`.

### Changes Required:

#### 1. Render with a crop path

**File**: `src/ai_reel_montage/shell/video.py`

**Intent**: Let `render_clip` take an optional crop path and put it into the existing command as
the x of the `crop` filter. A render without a path keeps the S-01 command character for
character.

**Contract**:

- `crop_filter(crop: CropBox, path: CropPath | None) -> str` — the `crop=…` part of the filter
  chain. Without a path it is the S-01 text `crop=<w>:<h>:<x>:<y>`. With a path it is
  `crop=<w>:<h>:x='<crop_x_expression(path.x)>':y=<y>`; the single quotes keep the expression's
  commas from splitting the filter chain.
- `render_clip(source, frames, fps, crop, output, path: CropPath | None = None) -> None`. With a
  path, before any file or directory is created, it raises `VideoError` when `len(path.x)`
  differs from `frames.n_frames` or when the expression exceeds 100 000 characters (see Critical
  Implementation Details). Everything after the filter string — encoder, audio, `-bitexact`,
  the publish step — is unchanged.

#### 2. Render tests

**Files**: `tests/unit/test_render_guard.py`, `tests/integration/test_video.py`

**Intent**: Tie the rendered pixels to the crop path, and pin that the moving crop is an extension
of the S-01 render, not a second one. Renders are 2 s; the pixel comparison is 1 s.

**Contract**: the tests include at least these named cases.

- Unit: `test_crop_filter_without_path_is_the_fixed_crop_text`,
  `test_crop_filter_with_path_quotes_the_expression`,
  `test_render_command_carries_the_crop_filter_of_the_path` — the `-vf` argument of
  `_render_command(..., path)` is exactly `crop_filter(crop, path) + ",scale=1080:1920,setsar=1"`,
  which ties the real command to the filter text the pixel test checks,
  `test_path_of_wrong_length_is_refused`, `test_oversized_expression_is_refused` — the last two
  raise before anything is touched, like the existing guards.
- Integration: `test_moving_crop_pixels_match_numpy_slicing` — frames 19 300 to 19 349 with the
  path computed from the real tracking file (measured in planning: 50 distinct crop positions,
  from 796 to 1306). One ffmpeg run applies the text returned by `crop_filter(crop, path)` alone
  and writes raw frames; another
  decodes the same frames uncropped. The luma plane of every cropped frame equals the uncropped
  frame sliced at `path.x[k]` in numpy. The test first asserts that the path takes at least 40
  distinct values, so a still crop cannot pass it.
- Integration: `test_constant_path_gives_the_same_bytes_as_the_fixed_crop` — a 2 s render with
  no path and one with a path of constant x 656 have equal SHA-256.
- Integration: `test_two_ball_following_renders_are_byte_identical` — same window, same path,
  two outputs, equal SHA-256; 100 frames each.

#### 3. CLI argument and wiring

**File**: `src/ai_reel_montage/cli.py`

**Intent**: Add the tracking file to the call sequence: parse → probe → frame range → centre
crop → read track → crop path → check → render. The CLI still holds no montage logic.

**Contract**:

- New optional argument `--tracking PATH`. It counts with `--input`, `--window`, `--output` for
  "any given means the three are required", and is never itself required.
- A tracking path that is not a file ends the run with `error: tracking file not found: <path>`
  and exit code 2, before the probe. The existence check and `load_ball_track` are reached
  through module-level names, so unit tests replace them.
- `TrackingError` maps to exit code 1, `CameraPathError` to exit code 1, each with one
  `error: ` line.
- With a track: the centres come from `ball_centre`, the path from `crop_path`, the counts from
  `check_follow`. The CLI does no counting of its own. When `inside < tracked`, the run ends with
  `error: ball outside the crop in <k> of <n> tracked frames`, exit code 1, and nothing is
  rendered.
- The success line on stdout keeps its S-01 beginning and gains a suffix:
  - without `--tracking`: `wrote <output>: 500 frames, 10.00 s, centre crop`
  - with it: `wrote <output>: 500 frames, 10.00 s, ball inside crop in 500/500 tracked frames, 0 frames on fallback`
  The first pair is `inside`/`tracked` of `FollowCheck`, the last number is `fallback`. A window
  entirely inside a run without a ball prints `ball inside crop in 0/0 tracked frames, 100 frames
  on fallback`: the line never claims a frame for which the file holds no position.

#### 4. CLI tests

**Files**: `tests/unit/test_cli.py`, `tests/integration/test_cli_e2e.py`

**Intent**: Cover the new argument and error mapping with fakes, and run the real entry point on
a normal window and on a window inside a run without a ball.

**Contract**: the tests include at least these named cases.

- Unit: `test_tracking_path_is_read_for_the_window_frame_range` — the fake reader is called with
  `FrameRange(30239, 500)` and fps 50, and the fake render receives a path of 500 values.
- Unit: `test_without_tracking_the_render_gets_no_path` and the existing
  `test_valid_invocation_renders_expected_frame_range` still passes.
- Unit: `test_missing_tracking_file_exits_2_and_does_not_probe`,
  `test_tracking_error_exits_1_and_does_not_render`,
  `test_success_line_reports_check_and_fallback_counts`.
- Integration: `test_cli_with_tracking_writes_a_ball_following_clip` — window `386-388`
  (frames 19 300 to 19 399, every sample positioned, the crop moving and reaching the right edge):
  returns 0, the output is 1080x1920 with 100 frames, stdout contains
  `ball inside crop in 100/100 tracked frames, 0 frames on fallback`, and the file's SHA-256
  differs from a centre-crop render of the same window.
- Integration: `test_cli_window_inside_a_run_without_ball_still_renders` — window `364-366`:
  returns 0, 100 frames, stdout contains
  `ball inside crop in 0/0 tracked frames, 100 frames on fallback`.

#### 5. Usage note

**File**: `README.md`

**Intent**: Document the fallback, as FR-002 requires, where a user of the command will read it.

**Contract**: the "Usage" section gains the `--tracking` invocation, the statement that the crop
follows the ball with no smoothing, the three fallback rules in plain words (straight line across
a stretch without a ball; nearest known position when one side is missing; centre crop when the
track has no position), and the meaning of the two counts in the output line.

### Success Criteria:

#### Automated Verification:

- Full test suite passes with the source required: `REEL_REQUIRE_SOURCE=1 uv run pytest`
- Type checking passes: `uv run mypy`
- Linting passes: `uv run ruff check`
- Formatting is clean: `uv run ruff format --check src tests`
- Help lists the new argument: `uv run ai-reel-montage --help | grep -e --tracking`
- The command verifies its own clip:
  `uv run ai-reel-montage --input transfer-01a1f923/*.mp4 --tracking transfer-01a1f923/full_match_tracks.json --window 6:20-6:30 --output out/s02.mp4 | grep "ball inside crop in 500/500 tracked frames"`
- Two runs give the same bytes: the command above written to `out/s02-b.mp4`, then
  `test "$(sha256sum < out/s02.mp4)" = "$(sha256sum < out/s02-b.mp4)"`

#### Manual Verification:

- `out/s02.mp4` plays in a desktop video player and the ball stays in the picture for the whole
  clip, near the horizontal middle except close to the touchlines; jitter is expected and is not
  a defect of this slice
- The same window rendered without `--tracking` shows a visibly different, fixed framing
- A 10 s window in minute 90 renders in under 45 s:
  `time uv run ai-reel-montage --input transfer-01a1f923/*.mp4 --tracking transfer-01a1f923/full_match_tracks.json --window 90:00-90:10 --output out/s02-late.mp4`
  (measured parts: about 6 s reading, about 13 s encoding)
- Window `6:02-6:12`, which crosses a stretch without a ball, plays with the crop moving steadily
  through that stretch: no freeze, no jump

**Implementation Note**: After the automated checks pass, pause for the human to confirm the
manual items. This closes the slice's implementation; `/10x-impl-review` is a separate session.

---

## Testing Strategy

### Unit Tests:

- The rule on hand-written tracks: centring, interpolation between samples, even rounding with
  ties upward, the clamp at both edges, a run without a ball, a window starting inside one,
  one-sided and absent positions, a window off the sample grid.
- The check itself, including a case where it reports a ball outside the crop.
- The filter expression: constant path, one term per change, evaluation back to the path.
- The reader on in-memory JSON: which samples are returned, early stop, every rejection.
- Render guards and the filter text; CLI argument and error mapping with fakes.

No unit test reads `transfer-*/`, opens a real file or starts a subprocess.

### Integration Tests:

- Reader against the delivered file: grid, a window inside a run without a ball, fps check,
  memory bound.
- **Ball inside the crop at every positioned sample of the whole match** — the slice's automatic
  verification, compared against the file's own values.
- Rendered pixels equal numpy slicing of the decoded frames at the path's positions.
- A constant path reproduces the fixed crop's bytes; two ball-following renders are identical.
- CLI end to end on a normal window and on a window inside a run without a ball.

Every render is 2 s or shorter. Nothing compares against a hash stored in the repository.

**What the check proves and what it does not.** A centred, clamped crop contains the ball centre
by construction, so the check cannot fail while the rule is implemented as written. It guards the
frame mapping, the clamp and the even rounding against regressions, on every run and over the
whole match. That the recorded positions match the visible ball is evidence from research
(finding 2), and that the rendered pixels are the crop the path describes is the numpy comparison
in Phase 3, tied to the real command by the unit test of its `-vf` argument. In fallback frames
there is no recorded position, so they are left out of the check and reported as a separate
count; what those frames show is not verified.

### Manual Testing Steps:

1. Render `6:20-6:30` with `--tracking`; watch it and read the output line.
2. Render the same window without `--tracking`; compare the framing.
3. Render `6:20-6:30` again to a second path; compare `sha256sum`.
4. Render `90:00-90:10` with `time`.
5. Render `6:02-6:12`; watch the stretch from 6:04 to 6:10, where the track has no ball.

## Performance Considerations

Reading costs about 0.83 ms per second of offset into the recording, at most about 5 s, at 35 MB
of memory (`research.md`, finding 1; 5.93 s was measured during planning for minute 90 on a
loaded machine). Encoding is unchanged from S-01 at about 13 s per 10 s of output; the moving crop
adds nothing measurable (`research.md`, finding 5). The whole-match integration test costs one
full streaming pass, about 5.4 s. The integration tier grows by roughly six 2 s renders and four
reads, about 35 s in total.

## Migration Notes

None. A run without `--tracking` produces the same command and the same bytes as before. The
success line on stdout gains a suffix; no caller depends on it and no existing test pins the
whole line.

## References

- Related research: `context/changes/ball-following-crop/research.md`
- Change identity: `context/changes/ball-following-crop/change.md`
- Roadmap item: `context/foundation/roadmap.md`, S-02
- Requirements: `context/foundation/prd.md`, FR-001, FR-002, FR-005 and US-01
- Plan this one follows in shape: `context/archive/2026-11-21-first-playable-clip/plan.md`
- Window as frame range: `src/ai_reel_montage/core/window.py:40-45`, `:90-101`
- Centre crop: `src/ai_reel_montage/core/framing.py:20-39`
- Render command and publish step: `src/ai_reel_montage/shell/video.py:118-192`
- CLI wiring: `src/ai_reel_montage/cli.py:74-97`
- Integration fixtures: `tests/integration/conftest.py:21-32`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Crop path in the pure core

#### Automated

- [x] 1.1 Unit tests pass: `uv run pytest -m "not integration"` — b075a2e
- [x] 1.2 Type checking passes: `uv run mypy` — b075a2e
- [x] 1.3 Linting passes: `uv run ruff check` — b075a2e
- [x] 1.4 Formatting is clean: `uv run ruff format --check src tests` — b075a2e
- [x] 1.5 `core/` imports none of `subprocess`, `os`, `pathlib`, `json`, `ijson`, `time`, `random` — b075a2e
- [x] 1.6 `core/` does not import `shell` or `cli` — b075a2e

### Phase 2: Tracking reader in the IO shell

#### Automated

- [x] 2.1 Integration tests pass with the source required: `REEL_REQUIRE_SOURCE=1 uv run pytest -m integration`
- [x] 2.2 Unit tests pass: `uv run pytest -m "not integration"`
- [x] 2.3 Type checking passes: `uv run mypy`
- [x] 2.4 Linting passes: `uv run ruff check`
- [x] 2.5 Formatting is clean: `uv run ruff format --check src tests`
- [x] 2.6 The ball is inside the crop at every positioned sample of the match
- [x] 2.7 No whole-file load of the tracking JSON exists

### Phase 3: Moving crop in the render, `--tracking` on the CLI, end-to-end check

#### Automated

- [ ] 3.1 Full test suite passes with the source required: `REEL_REQUIRE_SOURCE=1 uv run pytest`
- [ ] 3.2 Type checking passes: `uv run mypy`
- [ ] 3.3 Linting passes: `uv run ruff check`
- [ ] 3.4 Formatting is clean: `uv run ruff format --check src tests`
- [ ] 3.5 Help lists the new argument
- [ ] 3.6 The command verifies its own clip
- [ ] 3.7 Two runs give the same bytes

#### Manual

- [ ] 3.8 `out/s02.mp4` plays and the ball stays in the picture for the whole clip
- [ ] 3.9 The same window rendered without `--tracking` shows a visibly different, fixed framing
- [ ] 3.10 A 10 s window in minute 90 renders in under 45 s
- [ ] 3.11 Window `6:02-6:12` plays with the crop moving steadily through the stretch without a ball
