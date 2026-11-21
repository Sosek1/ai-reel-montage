<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Ball-Following Crop (S-02) Implementation Plan

- **Plan**: `context/changes/ball-following-crop/plan.md` (with `plan-brief.md`, checked against `research.md`)
- **Mode**: Deep
- **Date**: 2026-11-21
- **Verdict**: REVISE
- **Findings**: 0 critical, 6 warnings, 3 observations
- **Triage**: complete on 2026-11-21 — 9 fixed, 0 skipped, 0 accepted, 0 dismissed
- **Verdict after fixes**: SOUND

The plan is sound in approach and faithful to the research. Nothing in it has to be rethought.
Six small gaps should be closed in the plan text before the implementation sessions start; each is
a sentence or a named test, and none changes the architecture, the phases or the scope.

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | WARNING (F1, F6) |
| Lean Execution | PASS |
| Architectural Fitness | WARNING (F4) |
| Blind Spots | WARNING (F2, F3, F5) |
| Plan Completeness | PASS (F7 is a wording error in the brief) |

## Grounding

Grounding: 7/7 paths ✓ (`cli.py`, `core/window.py`, `core/framing.py`, `shell/video.py`,
`shell/__init__.py`, `tests/integration/conftest.py`, `pyproject.toml`), 6/6 symbols ✓
(`FrameRange`, `CropBox`, `centre_crop`, `seek_time`, `_render_command`, `_unavailable`),
brief↔plan ✓ except one figure (F7). Progress↔Phase ✓: one `## Progress`, three phases, 6 + 7 + 11
rows matching the Success Criteria bullets one to one, no checkboxes inside phase blocks.
`context/foundation/lessons.md` and `docs/reference/contract-surfaces.md` do not exist; both
checks skipped.

## What was verified by measurement

Run in this session against `transfer-01a1f923/`, one streaming pass of the tracking file and
2 s ffmpeg runs only. The deep-mode verification was done inline rather than by a sub-agent,
because every risky claim was a number that one script could re-measure.

| Plan claim | Result |
| --- | --- |
| 99 157 samples, 94 415 positioned, grid of 3 from 0 to 297 468 | reproduced |
| `FrameRange(19000, 500)`: `frame_idx` 18 999 to 19 500, no NaN, 200 distinct crop positions | reproduced |
| `FrameRange(18200, 750)`: 252 samples, 18 198 to 18 951, 108 NaN (18 201 to 18 522) | reproduced |
| Window `364-366`: every output frame a fallback frame | reproduced (frames 18 200–18 299 lie between 18 198 and 18 525) |
| Frames 19 300–19 349: 50 distinct positions, 796 to 1306; `386-388` reaches the clamp at 1312 | reproduced |
| Expression sizes 6 235 / 5 001 / 28 406 characters, 484 / – / 2 070 terms | reproduced exactly |
| About 9.5 characters per output frame | 9.59 over the whole match |
| Whole match: ball inside the crop at every positioned sample, every x even, 0–1312 | 94 415 / 94 415, all even |
| First sample of the file is positioned, last is not (only the final run is one-sided) | reproduced |
| ijson yields `Decimal("50.0")` for `metadata.video_fps` | reproduced |
| ffmpeg accepts an expression near the 100 000-character guard | **new**: accepted at 82 896 and 124 896 characters (6 000 and 9 000 terms); 153 897 characters fails in `exec` with `Argument list too long`; 438 897 characters accepted from a file via `-/filter:v`. Evaluation cost: about 0.1 s per 100 frames at 9 000 terms. |
| Phase 1 and 2 `grep` criteria | run against the current tree: all three exit as the plan expects (`json.loads(` in `shell/video.py` does not match `json\.load\(`) |
| Gates on the current tree | 52 unit tests pass, mypy, ruff check and ruff format clean |

All arithmetic in the named unit cases was checked by hand (696; 706 and 716; 658; 0 and 1312;
900 at frame 3; 1000 at frame 4) and is right under the rule as written.

## Answers to the review brief

- **Does the plan follow from the research, without distortion?** Yes. Every figure the plan
  takes from `research.md` matches it, the planning-time measurements reproduce, and the plan
  keeps the research's own caveats (check holds by construction, cold cache not measured,
  time-varying crop size not measured). One figure in the brief is wrong (F7).
- **Is "piecewise-linear follow" defined unambiguously?** Almost. First and last sample, a run
  reaching the window edge, a window with no detection and a sample exactly on the window edge
  are all decided and have named tests. Three things are left to the implementation: the
  floating-point form of the interpolation, which decides 5 411 frames (F3); who owns the
  even-and-in-range guarantee once S-03 replaces `crop_path` (F4); and what a missing record,
  as opposed to a null ball, means for the fallback flag (F5).
- **Does the flat-sum expression scale?** Yes, and the plan knows its limit. The guard at
  100 000 characters sits below both the kernel limit and what ffmpeg was measured to accept.
  Each window is its own ffmpeg run with its own `n`, so S-05 multiplies runs, not expression
  length. What the plan lacks is one sentence naming the way out (F8).
- **Are parity and clamping consistent?** The rule is stated once and applied in one function,
  and `ball_inside` and `crop_x_expression` read the same `path.x`, so the check uses the integers
  ffmpeg receives. The gap is that nothing but `crop_path` enforces it (F4).
- **Does the verification prove the slice's thesis?** In three links, two of them strong. The
  whole-match test compares the path with the file's own values (independent of `ball_centre`);
  the pixel test compares ffmpeg's crop with numpy slicing at `path.x`. The per-run check is the
  weak link: it compares the path with centres computed by the same code and counts assumed
  positions as passes (F1). The pixel test also bypasses the real render command (F6).
- **Determinism.** Covered: same flags, a two-render byte test, a constant-path-equals-fixed-crop
  test, no dependence on serialisation, backend or iteration order (`Decimal` to `float` is
  correctly rounded in every ijson backend). F3 is the one place where an unstated choice changes
  bytes.
- **Pure core / IO shell.** Holds. ijson only in `shell/tracking.py`, the path in `core/camera.py`,
  the expression text in the core by the `seek_time` precedent. The CLI is asked to count and
  decide the check result, which is a small piece of logic on the wrong side (folded into F1).
- **Phases.** The split matches the `10x-chain` rule (numbers in, numbers out → `/10x-tdd`; files
  and ffmpeg → `/10x-implement`), the order is executable, and every criterion is a command. One
  path through Phase 2's own module is not exercised until Phase 3 (F2).
- **Scope.** No smoothing, zoom, multi-window or watchability work appears in any phase. Without
  `--tracking` the render call and filter string are S-01's; the existing unit and e2e tests do
  not pin the full success line, so the `, centre crop` suffix breaks none of them.

## Fix before implementation / can wait

| Finding | When |
| --- | --- |
| F1 Success line counts assumed positions as "ball inside crop" | before Phase 1 (changes a core contract and two named tests) |
| F2 Two ijson reads on one stream fail without a rewind | before Phase 2 |
| F3 Interpolation arithmetic not pinned; 5 411 frames sit on a rounding tie | before Phase 1 |
| F4 Even-and-in-range guarantee lives only inside the function S-03 replaces | before Phase 1 |
| F5 Fallback flag undefined for a missing record | before Phase 1 |
| F6 No test ties the real render command to the path | before Phase 3 |
| F7 Brief: "1876 px in 25 s" joins two different runs | can wait (wording) |
| F8 No named way out when the expression outgrows the limit | can wait (S-05 at the earliest) |
| F9 Small implementation notes | can wait (implementer's discretion) |

## Findings

### F1 — The success line reports assumed positions as "ball inside crop"

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: End-State Alignment
- **Location**: Phase 3, section 3 (CLI contract); Phase 1 `ball_inside`; "What the check proves"
- **Detail**: The per-run check feeds `ball_inside` with `ball_centre`, the same interpolation the
  path was built from, and the plan defines the first count as "frames passing the check over
  frames that have a centre". Every frame has a centre whenever the track holds one position
  anywhere, so the window `364-366`, where the file has no ball for any of the 100 frames, prints
  `ball inside crop in 100/100 frames, 100 frames on fallback`. The first half states something
  nobody measured. A track with no position at all prints `0/0` instead, so the two fallbacks
  report differently. The plan's own text says the check in fallback frames "concerns the
  position the fallback assumes"; the output line does not say that. The counting and the
  pass/fail decision are also placed in `cli.py`, which is documented as wiring only.
- **Fix A ⭐ Recommended**: Count only frames that are not fallback frames, in the core. Add to
  `core/camera.py` a function returning a frozen result (`tracked`, `inside`, `fallback`), where
  `tracked = n_frames - fallback` and `inside` is counted over tracked frames; the CLI formats it
  as `ball inside crop in 0/0 tracked frames, 100 frames on fallback` (and `500/500 tracked
  frames, 0 frames on fallback`) and fails when `inside < tracked`. Update
  `test_success_line_reports_check_and_fallback_counts`, the two e2e assertions and criterion 3.6
  to the new text.
  - Strength: the line states only what the data supports, both fallbacks report alike, and the
    CLI stays free of arithmetic. S-03 inherits a check whose denominator already means "frames
    with a recorded neighbourhood".
  - Tradeoff: interpolated frames between two neighbouring samples still count as tracked, on the
    strength of research finding 3 (predicted samples are themselves straight lines).
  - Confidence: HIGH — the numbers for both test windows were re-measured in this review.
  - Blind spot: None significant.
- **Fix B**: Keep the counts, change only the wording to `crop contains the followed position in
  500/500 frames`.
  - Strength: one-line change, no new core function.
  - Tradeoff: the line stops making the claim the slice is about, and the CLI keeps the counting.
  - Confidence: MEDIUM — honest, but weaker as evidence for the slice.
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A — `FollowCheck` and `check_follow` in `core/camera.py`; success line and error line count tracked frames only; tests, criterion 3.6 and the brief updated.

### F2 — `load_ball_track` runs two ijson reads on one stream, and the second fails without a rewind

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 2, section 1 (`read_video_fps`, `read_ball_track`, `load_ball_track`)
- **Detail**: Measured on the real file: after `next(ijson.items(f, "metadata.video_fps"))` the
  stream is at byte 65 536 (ijson reads ahead in blocks), and a second `ijson.items(f,
  "frames.item")` on the same handle raises `IncompleteJSONError: lexical error`. The plan says
  `load_ball_track` "opens the file", checks the fps, "then returns `read_ball_track`", without a
  rewind. No Phase 2 test runs the successful path of `load_ball_track`: `test_fps_mismatch_is_rejected`
  raises before the second read, and the other tests call the two readers separately. The defect
  would first show in Phase 3's e2e test, one session later, in a module Phase 2 declared done.
- **Fix**: State in the `load_ball_track` contract that the stream is rewound (`seek(0)`) between
  the two reads (or the file opened twice), and add to `tests/integration/test_tracking.py` a
  named case `test_load_ball_track_returns_the_window_track` asserting that
  `load_ball_track(path, FrameRange(19000, 500), Fraction(50))` returns 168 samples from 18 999 to
  19 500.
- **Decision**: FIXED — `load_ball_track` rewinds the stream between the two reads; `test_load_ball_track_returns_the_window_track` added to Phase 2.

### F3 — The interpolation arithmetic is not pinned, and 5 411 frames sit on a rounding tie

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Critical Implementation Details ("The rule, stated once", "Rounding must be spelled out")
- **Detail**: The plan spells out the rounding (`2 * floor(v / 2 + 1/2)`) but not the
  floating-point form of the interpolation that produces `v`. Measured over the whole match with
  `numpy.interp`: 5 411 of 297 469 frames have `centre - 304` within 1e-9 of an odd integer, the
  exact tie. Positions in the file have two decimals and interpolation divides by three, so ties
  are common, and `a + (b - a) * t`, `a * (1 - t) + b * t` and `numpy.interp` can land on
  different sides of one. The result is deterministic for any one formula, so the byte-identity
  tests pass either way; but "ties upward" then means "upward for the value this formula
  happened to produce", and a later refactor of the formula moves the crop by 2 px in up to 1.8%
  of frames without failing a named test.
- **Fix**: Add one sentence to the rule: the centre is `numpy.interp(frame, positioned_frame_idx,
  positioned_x)` in float64 (it also gives "hold the nearest known" at both ends for free), and
  the tie rule applies to that value as computed. Add a named unit case with an interpolated
  frame whose exact centre is an odd integer in thirds (for example samples at frames 0 and 3
  with x 1000.0 and 1003.0: frame 1 gives centre 1001, crop x 698).
- **Decision**: FIXED — `numpy.interp` in float64 named in step 1 of the rule; `test_interpolated_tie_rounds_upward` added.

### F4 — The even-and-in-range guarantee lives only inside the function S-03 replaces

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architectural Fitness
- **Location**: Phase 1 (`CropPath`, `crop_path`); Phase 3 (`render_clip` guards)
- **Detail**: `BallTrack` validates itself on construction; `CropPath` does not. Evenness and the
  0–1312 clamp are applied in `crop_path`, the one function the plan says S-03 will replace, and
  `render_clip` checks only the length of the path and the size of the expression. A path with an
  odd or out-of-range x — from S-03's smoothed function, or built by hand in a test — reaches
  ffmpeg, which rounds an odd x down and clamps an out-of-range one, both silently
  (`research.md`, finding 4). The picture then differs by a pixel or more from what the core
  computed and from what `ball_inside` checked, which is the failure the parity rule exists to
  prevent.
- **Fix A ⭐ Recommended**: Make the guarantee a property of the type. `CropPath` raises
  `TrackError` on construction when any x is odd or negative or when the two arrays differ in
  length; `render_clip` additionally refuses a path with any `x > source_width - crop.width`
  (or `crop_path` exposes the quantisation as its own small function, `even_clamped_x`, that S-03
  reuses). Add the named unit cases `test_crop_path_with_odd_x_is_rejected` and
  `test_crop_path_with_negative_x_is_rejected`.
  - Strength: S-03 cannot produce a path ffmpeg will silently alter; the rule stays in one place
    after the replacement.
  - Tradeoff: one more validation and two more tests in Phase 1; the upper bound needs the source
    width, which `CropPath` does not carry, so that part is checked where the width is known.
  - Confidence: HIGH — same pattern as `BallTrack` in this plan.
  - Blind spot: S-04 changes the crop width per frame, so the upper bound will need revisiting there.
- **Fix B**: Leave the type as it is and record in the plan that S-03 must re-apply step 2 of the
  rule.
  - Strength: no change to Phase 1.
  - Tradeoff: relies on the next plan reading this one; the silent off-by-one stays possible.
  - Confidence: MEDIUM — cheap now, and exactly the kind of loose boundary that returns in S-03.
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A, with one change — `CropPath` refuses odd or negative x and unequal lengths on construction; the right-edge bound is refused by `check_follow` in the core (which receives the source width) instead of by `render_clip`, which does not know it.

### F5 — The fallback flag is undefined for a missing record, as opposed to a null ball

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Critical Implementation Details (definition of a fallback frame); Phase 2 reader contract
- **Detail**: A frame is a fallback frame "unless it … lies between two positioned samples that
  are neighbours in the track". Whether two samples are neighbours depends on whether the stretch
  between them is written as records with `ball: null` or not written at all. In the delivered
  file every third frame has a record, so the question never arises; in a file with a different
  stride or with records left out, the crop would cross an arbitrarily long stretch on a straight
  line and report `0 frames on fallback`. The reader checks only that `frame_idx` increases, and
  reads `metadata.video_fps` but not `metadata.stride`. The research recommended reading
  `frame_idx` precisely so that "a different stride or a gap [is] visible instead of silently
  shifting the crop"; as planned, it is tolerated but not visible.
- **Fix**: Decide it in one sentence and pin it with a named test. Recommended: the reader also
  reads `metadata.stride`, and a step between consecutive records different from the stride
  raises `TrackingError` naming the frame (a gap in the records is a broken file, not a stretch
  without a ball); `test_gap_in_frame_idx_is_rejected` covers it. If tolerance is preferred
  instead, say so explicitly and add a core test showing that such frames are not counted as
  fallback.
- **Decision**: FIXED — reject: `read_metadata` replaces `read_video_fps` and returns fps and stride; a step different from the stride raises `TrackingError`; `test_gap_in_frame_idx_is_rejected` and `test_missing_stride_is_rejected` added.

### F6 — No test ties the real render command to the crop path

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: End-State Alignment
- **Location**: Phase 3, section 2 (render tests) and section 4 (CLI tests)
- **Detail**: `test_moving_crop_pixels_match_numpy_slicing` runs "one ffmpeg run [that] applies
  `crop_filter` alone" — a command the test builds itself, not `_render_command`. The path
  through `render_clip` is covered by the two unit tests of `crop_filter`'s text, by
  `test_constant_path_gives_the_same_bytes_as_the_fixed_crop` and by the e2e assertion that the
  SHA-256 differs from the centre-crop render. A `render_clip` that put a wrong but non-constant
  x into the command (for instance the expression of a path offset by one frame) would pass all
  of them. The chain "file → path → ffmpeg" has its last link checked on a side command.
- **Fix**: Add a unit case `test_render_command_carries_the_crop_filter_of_the_path` asserting
  that the `-vf` argument of `_render_command(..., path)` is exactly
  `crop_filter(crop, path) + ",scale=1080:1920,setsar=1"`, and have the pixel test obtain its
  filter text from the same `crop_filter` call. Together with the existing
  `test_seek_time_lands_on_requested_source_frame` this closes the chain without a lossy
  comparison of encoded frames.
- **Decision**: FIXED — `test_render_command_carries_the_crop_filter_of_the_path` added; the pixel test takes its filter text from `crop_filter`.

### F7 — The brief's "up to 1876 px in 25 s" joins two different runs

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: `plan-brief.md`, Open Risks & Assumptions, second bullet
- **Detail**: Re-measured: the run with the 1876.13 px distance starts at 1972.1 s and lasts
  12.72 s. The 25.74 s run is the last one of the recording (5923.7 s to the end); it has no
  position after it, so the crop is held there, not moved. The fastest crossing of any run is
  7.65 source px per output frame (the 2.94 s run at 2109.9 s, 1147.5 px). `research.md` states
  both facts separately and correctly; only the brief merges them.
- **Fix**: Replace with "up to 1876 px in 12.7 s (at most 7.7 px per output frame); the longest
  stretch, 25.7 s at the end of the recording, is held, not crossed."
- **Decision**: FIXED — brief corrected to 1876 px in 12.7 s; the 25.7 s run is held.

### F8 — No named way out when the expression outgrows the limit

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Critical Implementation Details ("The expression has a size limit")
- **Detail**: The limit itself is right and now measured: ffmpeg took 124 896 characters
  (9 000 terms) as one argument, and 153 897 characters failed in `exec` before ffmpeg started.
  The guard at 100 000 characters therefore refuses nothing ffmpeg could not have run by a wide
  margin, and S-05 is unaffected as long as each window is its own ffmpeg run. The plan says what
  happens at the limit (a `VideoError`) but not what the next step would be. Two routes are
  already measured to give the same pixels: the same expression read from a file (`-/filter:v`
  accepted 438 897 characters in this review; `research.md` measured `-/vf` at 28 414) and
  `sendcmd`, whose output file was byte-identical to the expression route.
- **Fix**: Add one sentence after the limit: "If a later slice needs longer single renders, the
  same expression read from a file (`-/filter:v`) or `sendcmd` removes the limit without changing
  pixels (`research.md`, finding 5); neither is built here."
- **Decision**: FIXED — the measured limits and the two ways out are stated after the size limit.

### F9 — Small notes for the implementer

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 contract; Desired End State; Phase 2 whole-match test
- **Detail**: Four points, none blocking.
  (a) A frozen dataclass holding numpy arrays still generates `__eq__`, and comparing two
  instances raises "truth value of an array is ambiguous"; `BallTrack` and `CropPath` should be
  declared with `eq=False` (and ideally hold read-only arrays), and tests should compare the
  arrays.
  (b) `TrackError` (core) and `TrackingError` (shell) differ by three letters and both reach the
  CLI; `BallTrackError` or similar for the core one would be harder to confuse.
  (c) Desired End State says a run without `--tracking` "behaves exactly as in S-01", while the
  success line gains `, centre crop`. Migration Notes says so; the End State should too. No
  existing test pins the full line.
  (d) The whole-match test checks sample frames against the file. Frames between samples are
  covered only by construction; one extra assertion makes them independent of `ball_centre` at
  no cost: for every frame between two neighbouring positioned samples, `path.x` lies between
  the two samples' own crop x values (inclusive).
- **Fix**: Fold (a)–(d) into the Phase 1 and Phase 2 contracts as one line each.
- **Decision**: FIXED — (a) `eq=False` and read-only arrays, (b) core error renamed `CameraPathError`, (c) Desired End State names the success-line suffix, (d) between-sample assertion added to the whole-match test.
