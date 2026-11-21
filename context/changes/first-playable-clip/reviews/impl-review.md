<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: First Playable Clip (S-01) Implementation Plan

- **Plan**: context/changes/first-playable-clip/plan.md
- **Scope**: Full plan
- **Reviewed phases**: 1, 2, 3
- **Date**: 2026-11-21
- **Verdict**: NEEDS ATTENTION (all six findings fixed in triage, 2026-11-21)
- **Findings**: 0 critical, 2 warnings, 4 observations

Reviewed commits: `b65638f` (phase 1), `2eff593` (phase 2), `0d07d52` (phase 3). The review read
every changed source and test file directly (about 750 lines) instead of delegating to sub-agents,
ran every automated criterion, and tested the error paths of `render_clip` and the CLI on a
synthetic 2 s 1920x1080 50 fps clip generated outside the repository. The real recording was only
touched by the existing 2 s integration tests.

**What to fix now, what can wait**

| | Finding | When |
| --- | --- | --- |
| F1 | `--input <output>.partial` deletes the input | **Now**, before S-01 is closed |
| F2 | Clean-up can raise and escape as a traceback | **Now**, same edit as F1 |
| F3 | Error-path guarantees have no test | With F1/F2 (tests for the two fixes); the rest can wait |
| F4 | Probe runs before the window is parsed | Can wait (S-05 touches this code anyway) |
| F5 | Integration tier can pass by skipping | Can wait |
| F6 | Notes for the S-02 move to piped frames | No action in S-01; input to S-02 research |

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Evidence

**Automated criteria, run in this session**

| Criterion | Result |
| --- | --- |
| `uv run pytest` | 52 passed, **0 skipped**, 28.6 s (10 integration, 42 unit) |
| `uv run mypy` | no issues in 13 files |
| `uv run ruff check` / `ruff format --check src tests` | clean |
| 1.5 `core/` imports none of subprocess, os, pathlib, json, time, random | holds; `core/` imports only `re`, `dataclasses`, `fractions` |
| 2.6 `core/` does not import `shell` or `cli` (the corrected grep) | holds |
| 3.5 help lists `--window` | holds |

**Plan contracts** — all match: signatures and frozen dataclasses of `core/window.py` and
`core/framing.py`; `WindowError(ValueError)`, `FramingError(ValueError)`,
`VideoError(RuntimeError)`; the render command, element for element and in the planned order;
exit codes 0 / 1 / 2; usage errors through `parser.error` (`SystemExit(2)`), engine errors
returned with one `error: ` line; the success line with path, frame count and length. All eleven
named unit cases of phase 1, all eight named integration cases of phase 2, all nine named CLI unit
cases and both e2e cases of phase 3 exist and assert what their names promise. Extra tests beyond
the plan (`test_parsing_is_exact_not_floating_point`, three more crop cases, exact seek/duration at
50 fps) only tighten the contract.

**Five fixes from the plan review** — all landed in code:

| Plan-review finding | In code |
| --- | --- |
| F1 output equal to input | `cli.py:77`, resolved paths compared before the probe; test at `tests/unit/test_cli.py:115` uses `in.mp4` against `./in.mp4`, so it proves resolution, not string equality, and asserts no probe and no render |
| F2 CLI contract | `action="append"` + `parser.error` (`cli.py:31`, `cli.py:68`); `_input_exists` as a replaceable module-level name (`cli.py:39`); the unit tier opens no file and starts no subprocess |
| F3 criterion 2.6 | the corrected grep is in the plan and passes |
| F4 message wording | `core/window.py:96`, asserted verbatim in `tests/unit/test_window.py:75`; `Window` has two fields |
| F5 start frame pinned | `tests/integration/test_video.py:100`, asserts pts 30239 |

**Determinism** — `-threads 1` sits after `-i` (`shell/video.py:144`), so the encoder is
single-threaded and the AV1 decoder keeps its threads; `-bitexact` is an output option
(`shell/video.py:150`). Nothing in the render path reads a clock, an environment variable, a
random source or an unordered collection; the command is a fixed list. Byte identity holds on the
real source (integration test) and held on the synthetic clip here.

**The two named traps**

- *ffmpeg exits 0 on a short render.* Holds. A `FrameRange` past the end produced
  `render produced 50 frames instead of 100`; with a pre-existing output of known content, the
  content was unchanged afterwards and no `.partial` remained. Same after a hard ffmpeg failure
  (missing source).
- *Output equal to input.* Holds for the named case, including a symlink to the input (exit 2,
  nothing probed). A hard link to the input as output is harmless: the rename replaces the name,
  the recording survives under its own name (measured: source size and frame count unchanged).
  One adjacent hole remains — F1.

**Scope** — nothing from S-02 (no tracking data, no moving crop, no zoom) and nothing from S-05
(one window, a repeat is a usage error). No new dependency; numpy, scipy and ijson are untouched.

**Manual items 2.7 and 3.6–3.9** are checked in Progress. They leave no trace in the diff by
design (`out/` is git-ignored). This session saw supporting evidence for three of them: zero skips,
byte identity, and exit 2 with no file for `5945-5955` (e2e test). The player check (3.7) is taken
on the user's word.

## Findings

### F1 — An input named `<output>.partial` is deleted

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: src/ai_reel_montage/shell/video.py:114, src/ai_reel_montage/shell/video.py:166, src/ai_reel_montage/cli.py:77
- **Detail**: The overwrite guard compares the input with the output, but the file `render_clip` actually writes and deletes is `<output>.partial`. Reproduced on a synthetic clip: `--input x.mp4.partial --output x.mp4` → ffmpeg refuses (`Output … same as Input #0 - exiting`), the `except` branch runs `partial.unlink()`, and the input no longer exists; exit code 1. The trigger needs an unusual file name, which is why this is not rated critical, but the loss is the same one the guard exists to prevent: the recording is git-ignored and has no local copy. The guard also lives only in `cli.py`, while `render_clip` is the function S-05 will call once per window.
- **Fix**: At the top of `render_clip`, before anything is created, raise `VideoError` when `source.resolve()` equals `output.resolve()` or `partial.resolve()`. Keep the CLI check (it gives exit 2 for the common case) and extend it to the partial path. Add an integration-free unit test for the CLI branch and one test of `render_clip` with a throwaway file as "source".
- **Decision**: FIXED — guard at the top of `render_clip` (source may be neither the output nor `<output>.partial`), CLI check extended to the partial path (exit 2); tests in `tests/unit/test_render_guard.py`, `tests/unit/test_cli.py` and `tests/integration/test_video.py`. Reproduction replayed: exit 2, input intact.

### F2 — Clean-up after a failure can raise and escape as a traceback

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: src/ai_reel_montage/shell/video.py:165
- **Detail**: The contract says that on any failure `render_clip` raises `VideoError`. `partial.unlink(missing_ok=True)` runs inside the `except` block unprotected; `missing_ok` covers only `FileNotFoundError`. Reproduced: `--output <regular file>/clip.mp4` → `mkdir` fails, then `unlink` raises `NotADirectoryError`, which leaves `main` as an uncaught traceback instead of `error: …` with exit 1. A permission error on the unlink does the same. Separately, the block catches `BaseException` and rewraps everything except `VideoError` and `KeyboardInterrupt` as `VideoError`, so a `SystemExit` or `MemoryError` would be reported as "render failed".
- **Fix**: Suppress `OSError` around the unlink (`contextlib.suppress(OSError)`), and split the handler: `except OSError` → `VideoError`; clean-up for everything else in a `finally` guarded by a "published" flag, re-raising unchanged. Add a unit-level case for the output-under-a-file path.
- **Decision**: FIXED — `except OSError` → `VideoError`, clean-up moved to `finally` behind a `published` flag with `OSError` suppressed; other exceptions propagate unchanged. Test `test_output_under_a_regular_file_raises_video_error`. Reproduction replayed: `error: render failed: …`, exit 1.

### F3 — The error-path guarantees of `render_clip` are only partly tested

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: tests/integration/test_video.py:117, tests/unit/test_cli.py:81
- **Detail**: (a) "Leaves any existing output untouched" is in the contract and holds (verified by hand here), but no test pre-creates an output; `test_failed_render_leaves_no_file` starts from an empty directory. (b) The same test accepts any `VideoError`; it would also pass if the render failed for an unrelated reason (for example ffmpeg missing a codec), so it does not prove that the frame count check is what fired. (c) The mappings `FramingError` → 2 and a probe `VideoError` → 1 have no unit test; only the render `VideoError` is covered. None of these are named cases in the plan, so this is not drift.
- **Fix**: In `test_failed_render_leaves_no_file` write known bytes to the output first and assert they are unchanged, and add `match="produced 50 frames instead of 100"`. Add two three-line CLI unit tests for the missing mappings.
- **Decision**: FIXED — `test_failed_render_leaves_no_file` now matches `produced 50 frames instead of 100`; new `test_failed_render_leaves_existing_output_untouched` pre-creates the output and asserts its bytes; new CLI unit tests `test_probe_failure_exits_1_and_does_not_render` and `test_source_narrower_than_9_16_exits_2_and_does_not_render`.

### F4 — The probe runs before the window text is parsed

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: src/ai_reel_montage/cli.py:81
- **Detail**: The plan's call sequence is parse → probe → validate → crop → render. The code probes first and parses on the next line. Effects: a malformed window costs an `ffprobe` call, and a malformed window together with an unreadable input reports the probe failure with exit 1 instead of the window error with exit 2 (reproduced). `test_malformed_window_exits_2` does not assert that nothing was probed, so the order is not pinned. One more leniency in the same area: the clock-form regexes accept a one-digit seconds field (`1:5-1:9`), where the plan writes `M:SS`.
- **Fix**: Call `parse_window` before `probe_source`, and assert `shell.probed == []` in `test_malformed_window_exits_2`. Either accept one-digit clock fields in the plan text or tighten the regex to `\d{2}`; with S-05 about to take windows from a list, decide it there.
- **Decision**: FIXED — `parse_window` runs before `probe_source` (`cli.py`); `test_malformed_window_exits_2` arms a probe failure and asserts nothing was probed. The clock-form regexes now require exactly two digits after each colon, as the plan's `M:SS` / `H:MM:SS` grammar says; `1:5-1:9` and two hour-form variants are added to the malformed cases.

### F5 — The integration tier can turn green by skipping

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: tests/integration/conftest.py:14
- **Detail**: The fixture skips exactly as the plan asks — only for a missing tool or a missing recording, nothing wider — and on this machine all ten integration tests ran. But "passes, not skips" is enforced only by the manual item 2.7: if the `transfer-*/` directory is moved or renamed, `uv run pytest` stays green with ten skips and nothing about video is verified. Also, with more than one `.mp4` under `transfer-*/` the fixture silently takes the first by name, while the contract says "the single `.mp4`"; `test_probe_reports_source_properties` would then fail on the frame count rather than say why.
- **Fix**: Make the fixture fail instead of skip when an environment variable such as `REEL_REQUIRE_SOURCE=1` is set, and use it for the pre-commit run on this machine; fail with a clear message when more than one recording is found.
- **Decision**: FIXED — with `REEL_REQUIRE_SOURCE=1` the `source_video` fixture fails instead of skipping (verified by simulating a missing ffmpeg: 2 skips without the variable, 2 errors with it); more than one recording under `transfer-*/` fails with a message naming them. README documents the variable. `CLAUDE.md` was not edited: adding the variable to its pre-commit line is the user's call.

### F6 — What the current shape means for a move to piped frames in S-02

- **Severity**: 👁 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architecture
- **Location**: src/ai_reel_montage/shell/video.py:110
- **Detail**: Research finding 8 measured that filter rendering and piped rendering give different bytes for the same window; the implementation uses filters, as decided. Read against a later switch:
  - *Helps.* The core hands the shell a `FrameRange` in whole source frames, which is the index the tracking data is keyed by. No test pins a stored hash, so changing the renderer changes no expected value; every property test (size, aspect, frame count, audio length, render-twice identity) stays valid as written. `test_seek_time_lands_on_requested_source_frame` pins the decode-side seek on its own, and a piped decoder uses the same seek. `CropBox` and `OUTPUT_WIDTH`/`OUTPUT_HEIGHT` are already core types.
  - *Hinders.* `render_clip` is one function holding three things: building the filter command, running it, and publishing (partial file, frame count check, rename). A piped renderer needs the third unchanged and the first two replaced, so the publish step has to be extracted first; F1 and F2 are fixes to exactly that step, which makes now the cheap moment to give it its own function. `_run` is `subprocess.run` with captured output and cannot feed or drain a pipe. The signature takes one static `CropBox` for the whole clip; a moving crop needs a per-frame sequence. The audio is mapped from the same single input; with pipes the encoder process must open the source a second time for audio with the same `-ss`/`-t`, and the audio-length test is what will catch a mistake there. The even-`x` rule in `centre_crop` mirrors what the `crop` filter does on 4:2:0 input; a numpy crop on RGB frames has no such constraint, so S-02 must decide whether the rule stays.
- **Fix A ⭐ Recommended**: Leave the structure as it is in S-01 and carry this list into S-02's research; when fixing F1/F2, put the guard and the clean-up in a small private publish helper so the step is already separate.
  - Strength: No speculative abstraction; S-02's own research decides between a time-varying `crop` filter and pipes, and only the second needs the split.
  - Tradeoff: If S-02 picks pipes, its first phase is a refactor of `render_clip`.
  - Confidence: HIGH — the tests survive the refactor unchanged, so it is mechanical.
  - Blind spot: Whether a `crop` filter driven by `sendcmd` or an expression can follow a smoothed path at 50 fps was not measured here.
- **Fix B**: Split `render_clip` now into command building, running and publishing as three functions.
  - Strength: S-02 starts from a clean seam.
  - Tradeoff: Structure built for a decision that has not been taken; contradicts the plan's "whether S-02 needs pipes is S-02's research".
  - Confidence: MEDIUM — the seam may land in the wrong place for a two-process pipeline.
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A — the publish step (source guard, partial file, frame count check, rename, clean-up) is the private context manager `_publishing` in `shell/video.py`; the filter command is built by `_render_command`; `render_clip` keeps its signature and is two lines. The frame-count message no longer carries the start frame. The helps/hinders list above stays as input to S-02's research; nothing else was restructured.
