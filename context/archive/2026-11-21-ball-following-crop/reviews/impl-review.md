<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Ball-Following Crop (S-02)

- **Plan**: `context/changes/ball-following-crop/plan.md` (with `plan-brief.md`, `research.md`, `reviews/plan-review.md`)
- **Scope**: Full plan
- **Reviewed phases**: 1, 2, 3
- **Reviewed commits**: `b075a2e` (p1), `ea16f4c` (p2), `e7deb75` (p3)
- **Date**: 2026-11-22
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 1 warning, 6 observations
- **Triage**: complete on 2026-11-22 — 5 fixed (F5 in part), 1 accepted, 1 confirmed by the user (F2)
- **Verdict after fixes**: APPROVED

The implementation matches the plan closely, the two tests that carry the slice's thesis are
strong and were shown able to fail, and every gate is green. One thing has to be fixed before the
slice is closed: `--output` may name the tracking file, and the run then replaces the 398 MB
tracking file with the clip (F1, reproduced on a scratch copy). It is a few lines and one test.
Everything else can wait for the plans of S-03 and S-05.

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING (F1) |
| Architecture | PASS (F4, F5 are notes for S-03 and S-05) |
| Pattern Consistency | PASS |
| Success Criteria | WARNING (F2: manual items ticked without a recorded observation) |

## Fix now / can wait

| Finding | When |
| --- | --- |
| F1 `--output` equal to `--tracking` destroys the tracking file | **now, before `/10x-archive`** |
| F2 Manual items 3.8, 3.9, 3.11 have no recorded human observation | now, by the user (two minutes of watching; no code) |
| F3 Whole-match test proves containment, not centring; no real-file anchor for `x` | can wait (optional one-line anchor) |
| F4 Right-edge guard is on the `check_follow` route only | can wait — S-03 plan |
| F5 Read → path → check → verdict is composed inside `cli.py` | can wait — S-05 plan |
| F6 What helps and what hinders a later move to `sendcmd` | can wait — S-05 plan |
| F7 Small notes | can wait (implementer's discretion) |

## What was verified, and how

Read in full: the four source modules, all eight test files, `README.md`. Run in this session
against `transfer-01a1f923/`; renders of 2 s and one of 10 s, never the whole recording.

| Check | Result |
| --- | --- |
| `REEL_REQUIRE_SOURCE=1 uv run pytest` | 134 passed, 74 s |
| `uv run mypy`, `uv run ruff check`, `uv run ruff format --check src tests` | clean |
| Criteria 1.5, 1.6, 2.7 (greps) and "ijson only in `shell/tracking.py`" | no match, as required |
| S-01 command without a path | `_render_command` of `c5e7e6b` and of HEAD return the same argument list; the diff of `shell/video.py` touches only the filter string and the new guards |
| Reader against an independent parse | a separate plain ijson loop over the whole file gives the same 99 157 `frame_idx` and the same `x` (NaN-aware) as `read_ball_track` |
| Whole match | ball inside the crop at 94 415 / 94 415 positioned samples; at unclamped samples the ball is at most 1.0 px from the crop centre; `check_follow` gives `tracked=283155, inside=283155, fallback=14314` |
| Frames 19 300–19 349 | path from 796 to 1306, 50 distinct values (the plan's figures) |
| Criterion 3.7 | `out/s02.mp4` and `out/s02-b.mp4` have the same SHA-256 |
| Manual item 3.10 | `90:00-90:10` with `--tracking`: 18.8 s wall, `500/500 tracked frames` |

**Mutation checks of the two thesis tests** (the test function called with one name replaced; the
repository was not modified):

| Test | Mutant | Outcome |
| --- | --- | --- |
| `test_ball_is_inside_the_crop_over_the_whole_match` | path shifted by 1 frame / by 30 frames | fails |
| | path offset by +100 px | fails |
| | constant centre crop | fails |
| | no clamp at the right edge | fails |
| | sample held for three frames (no interpolation) | **passes** — caught by unit test `test_frames_between_samples_are_interpolated_linearly` |
| | even rounding downward instead of ties upward | **passes** — caught by unit tests `test_crop_x_is_even_with_ties_upward`, `test_interpolated_tie_rounds_upward` |
| `test_moving_crop_pixels_match_numpy_slicing` | `crop_filter` ignores the path | fails at frame 0 |
| | expression late by one frame | fails at frame 1 |
| | still path | fails on the `>= 40` distinct-values assertion |

## Answers to the review brief

- **Do the tests prove the thesis or only self-consistency?** They prove it, in the three links the
  plan designed. `test_ball_is_inside_the_crop_over_the_whole_match`
  (`tests/integration/test_tracking.py:96`) compares `path.x` from `crop_path` with `track.x` as
  read from the file; `ball_centre` is not imported by that module at all. The between-sample
  assertion is there (`:117-124`). `test_moving_crop_pixels_match_numpy_slicing`
  (`tests/integration/test_video.py:191`) passes exactly `crop_filter(crop, path)` to ffmpeg,
  asserts at least 40 distinct values first, and compares the luma plane of all 50 frames with a
  numpy slice at `path.x[k]`. The real command is tied to that text by
  `test_render_command_carries_the_crop_filter_of_the_path`. The limits of the whole-match test
  are in F3.
- **Piecewise-linear follow.** `core/camera.py:80-121` is the rule of Critical Implementation
  Details: `numpy.interp` over positioned samples in float64, `2 * floor(v / 2 + 1/2)`, clamp to
  `0 … source_width - width`, centre crop when no position exists. Edges checked by reading
  `_fallback_flags` (`:91-106`) case by case: a frame on a positioned sample is tracked; on a
  sample without a ball it is fallback; before the first or after the last sample of the track it
  is fallback; between two samples it is tracked only when both are positioned; an empty track is
  all fallback. A window off the sample grid, a run reaching the track edge and a window wholly
  without a position each have a named test.
- **Parity and clamping.** One place (`_even_round_up` and `np.clip` in `crop_path`), guarded by
  the type (`CropPath` refuses odd or negative x) and by `check_follow` (right edge). The check
  and ffmpeg read the same array: `check_follow(path, …)` uses `path.x`, and the expression is
  `crop_x_expression(path.x)`. See F4 for the one route that bypasses the right-edge guard.
- **Tracking reader.** Stops at the first positioned sample at or after the window's last frame
  (`shell/tracking.py:105`); `test_stops_reading_after_the_track_is_complete` puts invalid JSON
  right after that sample and would fail without the `break`. The rewind to byte 0 is in place
  with its reason in a comment (`:140-142`) and is exercised by
  `test_load_ball_track_returns_the_window_track`. Memory is bounded by window plus one run
  without a ball; the child-process test holds the peak under 200 MB for a window at frame
  270 000. A `frame_idx` that is not exactly one stride above the previous one raises
  `TrackingError` (`:79-83`); nothing is repaired.
- **Determinism.** No clock, no unseeded randomness, no set or dict iteration in the new code.
  `Decimal` to `float` is correctly rounded, so the path does not depend on how the file is
  serialised. The three byte tests exist and pass (no path = S-01 text, constant path = fixed crop
  bytes, two ball-following renders equal).
- **Pure core / IO shell.** `core/camera.py` imports numpy, `dataclasses` and the two core
  modules only. ijson appears only in `shell/tracking.py`. The numbers in the success line come
  from `FollowCheck`; the one subtraction in `cli.py:103` builds the error message. See F5.
- **Dangerous decisions.** Both `render_clip` guards run before `_publishing`, which is the first
  thing to create a directory; both tests assert the parent directory does not exist afterwards.
  `_publishing` is untouched. `inside < tracked` raises before `render_clip` is called
  (`cli.py:101-105`, `test_ball_outside_the_crop_exits_1_and_does_not_render`). The S-01 refusal
  of `--output` equal to `--input` is intact. The same protection was not extended to the new
  input file: F1.
- **Scope.** No smoothing, zoom, multi-window or watchability code. A second `--window` is still
  rejected. Without `--tracking` no reader is called, the render receives no path, and all S-01
  tests pass unchanged.
- **Plan-review fixes.** All nine landed: `FollowCheck`/`check_follow` in the core and the
  `tracked frames` wording (F1); `seek(0)` and its test (F2); `numpy.interp` and
  `test_interpolated_tie_rounds_upward` (F3); `CropPath` guards and the right-edge check (F4);
  `read_metadata` with stride and `test_gap_in_frame_idx_is_rejected` (F5); the `-vf` unit test
  and the pixel test using `crop_filter` (F6); the brief's 12.7 s figure (F7); the two ways out
  after the size limit (F8); `eq=False`, read-only arrays, `CameraPathError`, the end-state
  wording and the between-sample assertion (F9).

## Findings

### F1 — `--output` equal to `--tracking` replaces the tracking file with the clip

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: `src/ai_reel_montage/cli.py:113-123` (`_path_problem`)
- **Detail**: `_path_problem` refuses an output that is the input recording or whose `.partial`
  file is the input, and then only checks that the tracking file exists. Nothing compares the
  output with the tracking file. Reproduced on a scratch copy: a small valid tracking JSON passed
  as both `--tracking` and `--output` with window `0-2` exits 0, prints the normal success line,
  and the file then starts with `ftypisom` — the JSON is gone. The same holds when the tracking
  file is named `<output>.partial` (it is overwritten by ffmpeg, then renamed or deleted). The
  delivered tracking file is 398 MB, not in git, and S-01's review treated the same hazard for
  the recording as worth two findings. S-02 added a second input and did not extend the guard to
  it; the plan did not ask for it.
- **Fix**: In `_path_problem`, when `tracking` is given, refuse with exit 2 when
  `output.resolve()` or `partial_path(output).resolve()` equals `tracking.resolve()` (message in
  the style of the existing two, e.g. `output would overwrite the tracking file`). Add a unit case
  next to `test_output_equal_to_input_exits_2_and_does_not_render` asserting exit 2, the message,
  and `shell.probed == [] and shell.rendered == []`, for both the output and its `.partial` name.
  Add "the output may not be the tracking file" to the README sentence that already says it for
  the input.
- **Decision**: FIXED — `_path_problem` refuses an output, or an output temporary file, that is the tracking file (exit 2, before the probe); two unit cases added; README updated.

### F2 — Manual items 3.8, 3.9 and 3.11 are ticked without a recorded observation

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: `plan.md`, Progress, rows 3.8–3.11
- **Detail**: The four manual rows carry `[x]` and the Phase 3 commit SHA. The files exist
  (`out/s02.mp4`, `s02-b.mp4`, `s02-centre.mp4`, `s02-gap.mp4`, `s02-late.mp4`), all written
  between 11:21 and 11:23 by the implementation session, and neither the commit message nor the
  plan says who watched them or what was seen. Row 3.10 is confirmed here by measurement (18.8 s
  against a 45 s limit). Rows 3.8, 3.9 and 3.11 are judgements by eye — the ball stays in the
  picture, the centre render looks different, no freeze or jump across the stretch without a
  ball — and this slice is the roadmap's north star precisely because of what those rows show.
- **Fix**: The user plays `out/s02.mp4`, `out/s02-centre.mp4` and `out/s02-gap.mp4` once and says
  so; no file changes unless something looks wrong.
- **Decision**: CONFIRMED by the user on 2026-11-22 after watching the three clips. 3.8: the ball stays in the picture throughout, as described. 3.9: with the fixed centre crop about half of the action is out of the picture, and the difference from the tracked clip is large, most of all at its end. 3.11: the ball is not visible (a player picks it up and carries it), the crop moves steadily towards the corner with no freeze and no jump, and reads as if the camera anticipated where he goes.

### F3 — The whole-match test proves containment, not centring, and no test anchors a real `x`

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: `tests/integration/test_tracking.py:96-124`
- **Detail**: Two limits, both acceptable today. (a) "Inside the crop" leaves 304 px of slack on
  each side, so two wrong paths pass the test: a sample held for three frames, and rounding down
  instead of ties upward. Both are caught by named unit tests, so nothing is unguarded. This is
  the right form to keep: after S-03 the crop is no longer centred by construction, and
  containment over the whole match becomes the assertion that can really fail. (b) The values the
  path is compared with come through `read_ball_track`, the code under test. The integration
  tests pin sample counts, `frame_idx` and the number of NaN, but no real `x`; the plan's figures
  796 and 1306 are not asserted either. A reader that returned the right records with a wrong
  field would pass the real-file tier (the in-memory unit tests, which use different `x` and `y`,
  would catch it). Checked in this review: the reader's output equals an independent parse of the
  whole file.
- **Fix**: Optional. In `test_window_samples_lie_on_the_three_frame_grid` add
  `assert track.x[0] == 310.05 and track.x[-1] == 1495.79` (samples 18 999 and 19 500, read in
  this review). The reader's output does not change in S-03, so the anchor survives it.
- **Decision**: FIXED — `test_window_samples_lie_on_the_three_frame_grid` pins `x` of samples 18 999 and 19 500.

### F4 — The right-edge guard exists only on the `check_follow` route

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architecture
- **Location**: `src/ai_reel_montage/core/camera.py:135-136`; `src/ai_reel_montage/shell/video.py:223-230`
- **Detail**: As decided in plan review, `CropPath` refuses odd and negative x, and an x above
  `source_width - crop_width` is refused by `check_follow`. `render_clip` checks length and
  expression size only, so a path that never went through `check_follow` reaches ffmpeg, which
  clamps silently. In S-02 the only production caller is `cli._follow`, which always checks. The
  integration tests already call `render_clip` with paths that skipped the check, which shows how
  natural that route is. S-03 replaces `crop_path` with a smoothed function whose overshoot at
  the touchline is exactly the case this guard is for; S-05 adds a second caller.
- **Fix A ⭐ Recommended**: Record in the S-03 plan that every path goes through `check_follow`
  before `render_clip`, and add there a named test of the smoothed path at the right edge.
  - Strength: no change now; the guard is already tested (`test_check_rejects_a_path_beyond_the_right_edge`).
  - Tradeoff: stays a convention between two modules.
  - Confidence: HIGH — one production call site today.
  - Blind spot: S-04 makes the crop width vary per frame, so the bound becomes per-frame.
- **Fix B**: Make the bound structural: `CropPath` carries `max_x` (set by `crop_path`) and
  refuses a larger x on construction.
  - Strength: no route to ffmpeg bypasses it.
  - Tradeoff: changes the type S-03 builds on, and S-04 has to change it again.
  - Confidence: MEDIUM — cleaner, but pays twice.
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A — recorded for the S-03 plan in `follow-ups/review-fixes.md`.

### F5 — Read → path → check → verdict is composed inside `cli.py`

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Architecture
- **Location**: `src/ai_reel_montage/cli.py:94-110` (`_follow`)
- **Detail**: `_follow` calls the reader, `crop_path`, `ball_centre` and `check_follow`, decides
  `inside < tracked`, raises the core's `CameraPathError` itself and formats the summary. This is
  what the plan specified, the counting is the core's, and for one window it is wiring. It is
  also the one sequence S-05 must run once per window, and the pass/fail rule
  (`inside == tracked`) is stated in the `check_follow` docstring but decided in the CLI.
- **Fix**: None now. In the S-05 plan, move the sequence out of `cli.py` (a shell-level function
  per window) and give `FollowCheck` a `passed` property so the rule lives with the counts.
- **Decision**: FIXED in part — `FollowCheck.passed` added and used by the CLI; moving the sequence out of `cli.py` is recorded for S-05 in `follow-ups/review-fixes.md`.

### F6 — What helps and what hinders a later move to `sendcmd`

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architecture
- **Location**: `src/ai_reel_montage/core/camera.py:144-152`; `src/ai_reel_montage/shell/video.py:22-23`, `:154-159`, `:223-232`
- **Detail**: The flat-sum expression grows with the window: about 9.6 characters per output
  frame, refused above 100 000 characters (about 3.5 minutes at 50 fps). ffmpeg also evaluates
  every term for every frame, so the cost is quadratic in window length (measured in plan review:
  about 0.1 s per 100 frames at 9 000 terms). For S-02 windows neither matters. For S-05 it
  matters only if several windows are put into one ffmpeg run; one run per window keeps each
  expression at window size.
  - **Helps**: the crop path crosses the boundary as data (`CropPath`), never as text —
    `render_clip` receives the array and builds the text itself. The text is built in exactly one
    place (`crop_filter`), reached by one line of `_render_command`. `crop_x_expression` already
    reduces the path to its change points, which is the list a `sendcmd` script needs (one
    `crop x <value>` line per change). `fps` is already an argument of `render_clip`, and
    `sendcmd` is keyed by time, not by `n`. The pixel test compares against `path.x`, not against
    the text, so it stays valid for any route.
  - **Hinders**: `crop_filter` returns one self-contained string and three tests pin that shape
    (the two `crop_filter` text tests and the `-vf` equality test); `sendcmd` needs a script file
    beside the filter text, so the function's return type changes. That file is a second
    temporary file, and `_publishing` cleans up exactly one. The size guard is expressed in
    characters of the expression (`MAX_EXPRESSION_CHARS`) and would have to go rather than be
    adjusted. `_raw_frames` in the pixel test takes filter text only. `crop_x_expression` lives
    in the core as ffmpeg syntax; a `sendcmd` writer would be a second such function or move to
    the shell. Change times must be exact frame times (`k / fps` formatted like `seek_time`),
    which nothing does yet.
  - The cheaper way out keeps everything above: the same expression read from a file
    (`-/filter:v`, accepted at 438 897 characters in plan review) changes only how the text
    reaches ffmpeg.
- **Fix**: None now. Carry this list into the S-05 research; if S-05 renders one window per
  ffmpeg run, no change is needed at all.
- **Decision**: ACCEPTED — no change in S-02; the list is recorded for the S-05 research in `follow-ups/review-fixes.md`.

### F7 — Small notes

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: `src/ai_reel_montage/shell/tracking.py:99-106`; `src/ai_reel_montage/core/camera.py:120`; `src/ai_reel_montage/shell/video.py:226`
- **Detail**: Three points, none affecting a result.
  (a) The stop condition is tested only for samples after the window's first frame. A one-frame
  window lying on a positioned sample therefore reads on to the next positioned sample
  (`FrameRange(6, 1)` returns samples 6 and 9; the contract says the track ends at 6). The path
  and the flags are the same; the cost is one extra sample, or one run without a ball.
  (b) The clamp's upper bound `source_width - width` is not forced even. For a source whose
  width is odd the clamp would produce an odd x and `CropPath` would refuse it with
  `CameraPathError` (exit 1) instead of framing the clip. Not reachable with the delivered
  recording, and odd widths do not occur with 4:2:0 video.
  (c) `render_clip` builds the expression once for the size guard and `crop_filter` builds it
  again for the command; harmless at these sizes.
- **Fix**: (a) test the stop condition for every kept sample, or state "at least" in the
  docstring; (b) clamp to `2 * ((source_width - width) // 2)`; (c) leave.
- **Decision**: FIXED — (a) the stop condition is tested for every kept sample, with a unit case for a one-frame window; (b) the clamp's upper bound is rounded down to even, with a unit case; (c) left as it is.
