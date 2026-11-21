<!-- PLAN-REVIEW-REPORT -->
# Plan Review: First Playable Clip (S-01) Implementation Plan

- **Plan**: context/changes/first-playable-clip/plan.md
- **Mode**: Deep
- **Date**: 2026-11-21
- **Verdict**: SOUND (all five findings fixed in triage, 2026-11-21)
- **Findings**: 0 critical, 3 warnings, 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | WARNING |
| Plan Completeness | WARNING |

## Grounding

Grounding: 7/7 paths ✓ (2 to modify exist, 5 new ones sit in existing directories), 4/4 symbols ✓
(`--version`, `integration` marker, `.gitignore` entries, one `.mp4` under `transfer-*/`),
brief↔plan ✓, Progress↔Phase ✓ (3 phases, 16 + 5 rows match the criteria one to one).

Deep verification was done by measurement in this session instead of a sub-agent, because the
codebase is empty and the plan's risky claims are about ffmpeg, not about code. The plan's exact
render command was run on 2 s windows of the real source:

| Claim in the plan | Measured |
| --- | --- |
| Window `604.78-606.78` gives 100 frames, 1080x1920, SAR 1:1, DAR 9:16, h264 `yuv420p`, 50 fps | confirmed |
| AAC audio starts at 0 and is as long as the video with `-frames:v` plus `-t` | confirmed: both 2.000000 s |
| Two renders are byte-identical; `.partial` name with `-f mp4` gives the same bytes | confirmed: same SHA-256 for `a.partial` and `b.mp4` |
| Last 100 frames of the recording (start 5947.38 s) render in full | confirmed: 100 frames |
| A frame range past the last frame exits 0 with a short file, so the count check is what catches it | confirmed: exit 0, 50 frames for 100 requested |
| Probe returns 1920x1080, 50/1, 297 469 frames from the container | confirmed (`avg_frame_rate` also 50/1) |
| Seek value `604.780000` starts on source frame 30239 | confirmed with `-copyts -f framecrc`: first pts 30239 |
| One 2 s render costs about 2.5 s | 3.3 s wall here; the tier of eight is about 25–30 s |

All worked arithmetic in the named test cases was rechecked and holds: frames 30239 and 30240,
500 frames for both off-grid starts, 297 369 + 100 = 297 469 accepted, `5945-5955` rejected,
crop 608 wide at x = 656.

## Findings

### F1 — An output path equal to the input replaces the recording

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 2 — `render_clip` contract; Phase 3 — exit codes; decision "Existing output file: overwritten"
- **Detail**: `render_clip` writes `<output>.partial`, checks the frame count and renames over `output`. With `--output` pointing at the same file as `--input` the render succeeds, the count matches, and the rename replaces the 2.7 GB recording with a 10 s clip. The recording is git-ignored and delivered out of band, so there is no local way back. Nothing in the plan rejects this case.
- **Fix**: In `cli.py`, compare the resolved input and output paths before probing; when they are the same file, print `error: output would overwrite the input` and exit 2. Add `test_output_equal_to_input_exits_2_and_does_not_render` to `tests/unit/test_cli.py`.
- **Decision**: FIXED — Fix in plan

### F2 — The CLI contract leaves three behaviours to the implementer

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Completeness
- **Location**: Phase 3 — Arguments and wiring, CLI unit tests
- **Detail**: (a) The contract says exit code 2 for missing or conflicting arguments and that errors are "one line starting `error: `". argparse does neither by itself: measured on Python 3.14.4, a usage error raises `SystemExit(2)` instead of returning, and prints a usage line followed by `prog: error: …`. `test_missing_argument_exits_2` and `test_second_window_exits_2` cannot be written without deciding whether `main` returns 2 or raises. (b) "`--window` given more than once is a usage error" is not argparse's default: measured, a repeated `--window` is accepted and the last value wins silently. The plan does not say how the repeat is detected. (c) "An input path that does not exist" exits 2, so `cli.py` checks the file system before the probe. `test_valid_invocation_renders_expected_frame_range` replaces only `probe_source` and `render_clip`, so it needs a real existing file to get past that check, while `CLAUDE.md` says unit tests use no real files.
- **Fix A ⭐ Recommended**: Keep argparse's native behaviour for usage errors and state it in the contract: usage errors raise `SystemExit(2)` with argparse's own two-line message; engine errors (missing input, `WindowError`, `FramingError`, `VideoError`) are returned codes with one `error: ` line. Declare `--window` with `action="append"` and call `parser.error` when more than one is given. Do the input-existence check through a module-level name that the unit tests replace, like the two shell functions.
  - Strength: No custom parser code; the tests assert `pytest.raises(SystemExit)` with code 2 for usage errors and a returned code for engine errors; the unit tier stays free of real files.
  - Tradeoff: Two error formats on stderr (argparse's and the engine's).
  - Confidence: HIGH — the argparse behaviour was measured on this interpreter.
  - Blind spot: None significant.
- **Fix B**: Make `main` own every exit: subclass `ArgumentParser`, override `error` to raise an internal exception, and print a single `error: ` line and return 2 for usage errors too.
  - Strength: One error format and `main` always returns; the plan's sentence stays literally true.
  - Tradeoff: Custom parser code, and `--help` still exits through `SystemExit(0)`, so `main` is not uniform anyway.
  - Confidence: MEDIUM — works, but adds code S-05 will have to carry when the flag becomes repeatable.
  - Blind spot: Whether any later caller wants `main` as a library function was not asked.
- **Decision**: FIXED — Fixed via Fix A

### F3 — Criterion 2.6 fails on the word "shell" in a comment

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 2 — Automated Verification, last bullet
- **Detail**: `! grep -rn "shell" src/ai_reel_montage/core` fails on any occurrence of the word, not only on imports. The plan's own intent sentence for `core/window.py` reads "so the shell never receives a window ffmpeg would silently shorten"; measured, a docstring with that sentence makes the criterion exit 1. The recursive grep also reads `__pycache__/*.pyc`. The check also does not cover `cli`, which `CLAUDE.md` forbids `core/` to import as well.
- **Fix**: Replace the command with `! grep -rnE --include='*.py' "^\s*(import|from) .*\b(shell|cli)\b" src/ai_reel_montage/core`. The Progress row title 2.6 stays as it is.
- **Decision**: FIXED — Fix in plan

### F4 — "The window as written" is not available where the message is built

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 — `to_frame_range` contract
- **Detail**: The out-of-range message "states the window as written", but `to_frame_range` receives a `Window` holding two `Fraction`s; the caller's text is gone by then. The implementer has to choose between adding the text to `Window` (which then needs to be excluded from equality, or `test_parses_seconds_and_clock_forms_to_the_same_window` fails) and rewording the message.
- **Fix**: Change the contract to "states the window boundaries in seconds and the recording length in seconds", both formatted from the exact values (for example `window 5945-5955 s is outside the recording (5949.38 s)`). `Window` stays two fields.
- **Decision**: FIXED — Fix in plan

### F5 — No test proves the clip starts on the requested frame

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: End-State Alignment
- **Location**: Phase 2 — Integration tests
- **Detail**: Every integration test checks the frame count, size and length. A clip that starts one frame late would pass all of them, while FR-001a says "trims exactly those windows" and S-02 will line frames up with the tracking file by index. The mapping does hold today: measured in this review, `-ss 604.780000` with `-copyts -f framecrc` reports first pts 30239. It is just not pinned by a test.
- **Fix**: Add `test_seek_time_lands_on_requested_source_frame` to `tests/integration/test_video.py`: run `ffmpeg -ss <seek_time(30239, 50)> -i <source> -map 0:v:0 -frames:v 1 -copyts -f framecrc -` and assert the reported pts is 30239. It decodes one frame, well under a second.
- **Decision**: FIXED — Fix in plan
