# First Playable Clip (S-01) Implementation Plan

## Overview

The caller names one window of the match recording on the command line and gets a playable
1080x1920 (9:16) H.264 clip with the match audio, trimmed to that window and framed by a fixed
centre crop. This is roadmap slice S-01 (FR-001a, US-01): the cheapest proof that video can be cut
and rendered at all, and the place where window handling, determinism and the pure-core / IO-shell
split are established for every later slice.

## Current State Analysis

- The CLI has only `--version` (`src/ai_reel_montage/cli.py:10-25`); there is no input, window or
  output argument.
- `src/ai_reel_montage/core/__init__.py` and `src/ai_reel_montage/shell/__init__.py` are empty.
- One unit test exists (`tests/unit/test_cli.py:6-8`). `tests/integration/` has no tests yet; the
  `integration` pytest marker is already declared in `pyproject.toml`.
- `transfer-*/`, `out/` and `*.mp4` are git-ignored, so rendered clips cannot be committed.
- ffmpeg 8.0.1 with libdav1d, libx264 and aac is installed. The source is AV1 1920x1080, 50 fps
  constant, 297 469 frames (5949.38 s), Opus audio (`research.md`, finding 1).
- The decode-cost risk S-01 was sequenced first to expose does not materialise: with the seek
  before the input, a 10 s window decodes in about 1 s anywhere in the recording
  (`research.md`, finding 2).

## Desired End State

Running

```
uv run ai-reel-montage --input <recording.mp4> --window 10:04.78-10:14.78 --output out/clip.mp4
```

writes `out/clip.mp4`: 1080x1920, square pixels, display aspect 9:16, 50 fps, exactly 500 frames,
H.264 `yuv420p`, AAC audio starting at 0 and as long as the video. Running it twice produces
byte-identical files. A window that cannot be honoured exactly writes no file, prints a message
naming the window and the recording length, and exits non-zero.

Verify with `uv run pytest` (unit and integration tiers) and the manual steps in Phase 3.

### Key Discoveries:

- Seek before the input is frame-exact and offset-independent (`research.md`, findings 2 and 3).
- `-t` alone is not a frame count; `-frames:v` is (`research.md`, finding 3).
- Single encoder thread plus `-bitexact` is byte-identical across runs, also with AAC audio; the
  decoder may keep its default threads (`research.md`, finding 4).
- ffmpeg exits 0 on a window past the end, after the end, or with a negative start
  (`research.md`, finding 7). Validation and the frame-count check are the engine's own.
- Without `setsar=1` the output is flagged 76:135, not 9:16 (`research.md`, finding 6).
- Filter rendering and piped rendering produce different bytes for the same window
  (`research.md`, finding 8), so no test may pin a stored output hash.
- Measured during planning, 2 s windows at 604.78 s on the real source:
  - with `-frames:v 100` alone the audio is 1.984 s against 2.000 s of video; adding `-t 2`
    alongside it gives 2.000 s for both streams;
  - writing to `<name>.partial` with `-f mp4` gives the same bytes as writing to the final name;
  - a window covering the last 100 frames of the file (start 5947.38 s) renders all 100.

## What We're NOT Doing

- No tracking data, no ball-following crop, no camera path, no zoom — S-02 to S-04.
- No more than one window per run; a second `--window` is a usage error. Repeating the flag,
  ordering and joining are S-05.
- No clamping of a window that runs past the end of the recording: it is rejected (user decision).
- No `--preset`, `--crf` or other encoder options: preset `veryfast` and CRF 20 are fixed
  (user decision).
- No piped-frame rendering: the crop is done by ffmpeg filters in one process (user decision).
  Whether S-02 needs pipes is S-02's research.
- No stored output hash in the repository: determinism is tested by rendering twice and comparing.
- No `+faststart`, no upload or platform-acceptance test, no check of byte identity across
  machines or ffmpeg builds.
- No full-file keyframe scan and no run over the recording that is not bounded by a window.
- No new dependency: numpy, scipy and ijson are not needed in this slice.

## Implementation Approach

The slice splits where numbers end and pixels begin.

1. **Pure core.** Parsing the window text, converting it to whole source frames, validating it
   against the recording and computing the centre-crop rectangle are arithmetic. They live in
   `core/`, take scalars and dataclasses, and are built test-first with `/10x-tdd`.
2. **IO shell.** One `ffprobe` call reads the recording's properties; one `ffmpeg` call renders.
   The shell checks the produced frame count and writes atomically. It is verified by integration
   tests on 2 s windows of the real source and built with `/10x-implement`.
3. **CLI.** `cli.py` parses arguments, calls core then shell, and maps errors to messages and exit
   codes. Built with `/10x-implement`.

Decisions taken in planning:

| Decision | Choice |
| --- | --- |
| Audio | keep the match audio, transcoded to AAC 128k |
| Encoder | libx264, preset `veryfast`, CRF 20, fixed |
| Rendering | ffmpeg `crop`, `scale`, `setsar` filters in one process |
| Window form | `--window A-B`, each side seconds or `[h:]mm:ss[.fff]` |
| Window past the end | rejected, no file, non-zero exit |
| Rounding | each boundary to the nearest source frame, ties upward (at most 10 ms at 50 fps) |
| Recording properties | probed with `ffprobe`, never hardcoded |
| Existing output file | overwritten; a missing output directory is created |
| Exit codes | 0 success, 2 bad arguments or window, 1 render or probe failure |

## Critical Implementation Details

**Seek time formatting.** ffmpeg snaps a start time that falls between two frames upward to the
later frame (`research.md`, finding 3). The seek value is `start_frame / fps`; when that is not
exactly representable in the printed decimal, it must be rounded **down**, never to nearest, so
the snap lands on the intended frame. At 50 fps every frame time is exact in two decimals, so the
real source does not exercise this; a unit test with a 30000/1001 rate does.

**Both length limits are needed.** `-frames:v <n>` guarantees the video frame count and
`-t <n / fps>` bounds the audio to the same length. Dropping either one reintroduces a measured
defect: a 499-frame clip, or audio shorter than the video.

**Thread flag placement.** `-threads 1` is an output option, placed after `-i`. Before `-i` it
would also single-thread the AV1 decoder and triple the decode time for no determinism gain.

## Phase 1: Window maths in the pure core

### Overview

Everything in S-01 that is numbers in, numbers out, built test-first: the window grammar, the
frame conversion and validation, and the crop geometry. Driven by `/10x-tdd`.

### Changes Required:

#### 1. Window parsing and frame conversion

**File**: `src/ai_reel_montage/core/window.py` (new)

**Intent**: Turn the caller's window text into an exact time interval, then into a whole-frame
range validated against the recording, so the shell never receives a window ffmpeg would silently
shorten.

**Contract**:

- `WindowError(ValueError)` — raised for every malformed or out-of-range window; its message is
  shown to the caller verbatim.
- `Window` — frozen dataclass, `start: Fraction`, `end: Fraction`, in seconds from the start of
  the recording.
- `parse_window(text: str) -> Window`. Grammar: `<time>-<time>` with exactly one `-`. A `<time>`
  is `S[.f]` (seconds, any magnitude), `M:SS[.f]` or `H:MM:SS[.f]`; in the clock forms the seconds
  field is below 60, and the minutes field is below 60 when hours are present. No sign, no
  internal whitespace. Values are parsed exactly (decimal text to `Fraction`), never through
  `float`.
- `FrameRange` — frozen dataclass, `start_frame: int`, `n_frames: int`.
- `to_frame_range(window: Window, fps: Fraction, total_frames: int) -> FrameRange`. Each boundary
  maps to `floor(seconds * fps + 1/2)` (nearest frame, ties upward). Raises `WindowError` when the
  rounded range has fewer than 1 frame, when `start_frame >= total_frames`, or when
  `start_frame + n_frames > total_frames`. The out-of-range message states the window boundaries
  in seconds and the recording length in seconds, both formatted from the exact values (for
  example `window 5945-5955 s is outside the recording (5949.38 s)`). `Window` does not carry the
  caller's text.
- `seek_time(start_frame: int, fps: Fraction) -> str` and
  `duration_time(n_frames: int, fps: Fraction) -> str` — decimal strings with six fractional
  digits for the ffmpeg command line, rounded down (see Critical Implementation Details).

#### 2. Centre-crop geometry

**File**: `src/ai_reel_montage/core/framing.py` (new)

**Intent**: Compute the fixed 9:16 crop rectangle from the source size, so the filter string is
derived rather than hardcoded for a 1920x1080 recording. S-02 replaces the fixed `x` with a moving
one; the rectangle type stays.

**Contract**:

- `OUTPUT_WIDTH = 1080`, `OUTPUT_HEIGHT = 1920`.
- `FramingError(ValueError)`.
- `CropBox` — frozen dataclass, `width`, `height`, `x`, `y`, all `int`.
- `centre_crop(source_width: int, source_height: int) -> CropBox`. `height` is the source height;
  `width` is the even integer nearest to `source_height * 9 / 16`, ties upward (608 for 1080);
  `x` is the largest even integer not above `(source_width - width) / 2` (656 for 1920); `y` is 0.
  Raises `FramingError` when `width > source_width` (the source is narrower than 9:16).

#### 3. Unit tests

**Files**: `tests/unit/test_window.py`, `tests/unit/test_framing.py` (new)

**Intent**: Pin every boundary decided in planning by name, so a later slice cannot change one by
accident.

**Contract**: the tests include at least these named cases.

- `test_parses_seconds_and_clock_forms_to_the_same_window` — `604.78-614.78`,
  `10:04.78-10:14.78` and `0:10:04.78-0:10:14.78` are equal.
- `test_rejects_malformed_window_text` — parametrised: empty, one side missing, two separators,
  a sign, seconds field of 60 or more in a clock form, letters.
- `test_boundary_rounds_to_nearest_frame_ties_upward` — at 50 fps, 604.785 s maps to frame 30239
  and 604.79 s maps to frame 30240.
- `test_ten_second_window_is_500_frames_for_off_grid_starts` — starts 604.785 and 604.801.
- `test_window_past_end_is_rejected` — `5945-5955` against 297 469 frames at 50 fps.
- `test_window_ending_on_last_frame_is_accepted` — `5947.38-5949.38` gives 100 frames.
- `test_window_starting_after_end_is_rejected`, `test_empty_or_reversed_window_is_rejected`.
- `test_seek_time_rounds_down_for_non_decimal_rates` — fps 30000/1001.
- `test_centre_crop_of_1920x1080_is_608_wide_at_x_656`,
  `test_source_narrower_than_9_16_is_rejected`.

### Success Criteria:

#### Automated Verification:

- Unit tests pass: `uv run pytest -m "not integration"`
- Type checking passes: `uv run mypy`
- Linting passes: `uv run ruff check`
- Formatting is clean: `uv run ruff format --check src tests`
- `core/` imports none of `subprocess`, `os`, `pathlib`, `json`, `time`, `random`:
  `! grep -rnE "^(import|from) (subprocess|os|pathlib|json|time|random)" src/ai_reel_montage/core`

**Implementation Note**: This phase has no manual verification. After the automated checks pass,
commit and stop; Phase 2 is a separate session. Phase blocks use plain bullets — the corresponding
`- [ ]` checkboxes live in the `## Progress` section at the bottom of the plan.

---

## Phase 2: Probe and render in the IO shell

### Overview

The two subprocess calls: read the recording's properties, and render one frame range to a file.
Verified against bounded 2 s windows of the real source. Driven by `/10x-implement`.

### Changes Required:

#### 1. Probe and render

**File**: `src/ai_reel_montage/shell/video.py` (new)

**Intent**: Wrap `ffprobe` and `ffmpeg` behind two typed functions, with the engine's own checks
around a tool that reports success on wrong output.

**Contract**:

- `VideoError(RuntimeError)` — probe or render failure; the message includes the tool's stderr.
- `SourceInfo` — frozen dataclass, `width: int`, `height: int`, `fps: Fraction`,
  `total_frames: int`.
- `probe_source(path: Path) -> SourceInfo`. Reads the first video stream's `width`, `height`,
  `r_frame_rate` and `nb_frames` from the container (no packet or frame scan). Raises `VideoError`
  when the file is unreadable, has no video stream, or does not report a frame count.
- `render_clip(source: Path, frames: FrameRange, fps: Fraction, crop: CropBox, output: Path) -> None`.
  Creates the output's parent directory, renders to `<output>.partial`, counts the video frames
  of the result, and renames it over `output` only when the count equals `frames.n_frames`. On any
  failure it removes the partial file, leaves any existing `output` untouched, and raises
  `VideoError`.
- The render command, each element backed by a measurement (`research.md` findings 2, 3, 4, 6 and
  the planning measurements above):

  ```
  ffmpeg -nostdin -v error -y
    -ss <seek_time> -i <source>
    -map 0:v:0 -map 0:a:0?
    -frames:v <n_frames> -t <duration_time>
    -vf crop=<w>:<h>:<x>:<y>,scale=1080:1920,setsar=1
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -threads 1
    -c:a aac -b:a 128k
    -bitexact -f mp4 <output>.partial
  ```

- Both subprocesses receive argument lists, never a shell string: the real source's file name
  contains spaces, brackets and non-ASCII characters.

#### 2. Integration fixtures

**File**: `tests/integration/conftest.py` (new)

**Intent**: Locate the real recording once and skip cleanly where it or ffmpeg is absent, so the
integration tier never fails for a missing input.

**Contract**: a session-scoped `source_video` fixture returning the single `.mp4` under
`transfer-*/` at the repository root; it calls `pytest.skip` when none is found or when `ffmpeg`
or `ffprobe` is not on `PATH`.

#### 3. Integration tests

**File**: `tests/integration/test_video.py` (new)

**Intent**: Prove on the real AV1 source that the rendered file has the promised properties and
that the engine's checks hold. Every render is a 2 s window; all tests carry
`@pytest.mark.integration`.

**Contract**: the tests include at least these named cases.

- `test_probe_reports_source_properties` — 1920x1080, fps 50, 297 469 frames.
- `test_clip_is_9_16_with_exact_frame_count` — window `604.78-606.78`: 1080x1920, sample aspect
  1:1, display aspect 9:16, 100 frames, 50 fps, video codec h264, pixel format yuv420p.
- `test_audio_matches_video_length` — AAC stream present, start 0, duration equal to the video
  duration.
- `test_off_grid_start_still_gives_exact_frame_count` — window `604.785-606.785` gives 100 frames.
- `test_two_renders_are_byte_identical` — same window rendered to two paths, equal SHA-256.
- `test_last_frames_of_recording_render` — window `5947.38-5949.38` gives 100 frames.
- `test_seek_time_lands_on_requested_source_frame` — one frame decoded with
  `ffmpeg -ss <seek_time(30239, 50)> -i <source> -map 0:v:0 -frames:v 1 -copyts -f framecrc -`
  reports pts 30239 (measured in plan review). This pins the start frame itself, which the
  frame-count tests do not.
- `test_failed_render_leaves_no_file` — a `FrameRange` reaching past the last frame, passed
  straight to `render_clip` (bypassing core validation), raises `VideoError`; neither the output
  nor the `.partial` file exists afterwards.

### Success Criteria:

#### Automated Verification:

- Integration tests pass: `uv run pytest -m integration`
- Unit tests still pass: `uv run pytest -m "not integration"`
- Type checking passes: `uv run mypy`
- Linting passes: `uv run ruff check`
- Formatting is clean: `uv run ruff format --check src tests`
- `core/` does not import `shell` or `cli`:
  `! grep -rnE --include='*.py' "^\s*(import|from) .*\b(shell|cli)\b" src/ai_reel_montage/core`
  (import lines only — the word "shell" in a docstring must not fail the check)

#### Manual Verification:

- The integration tier reports passes, not skips, on this machine (a skip means the source or
  ffmpeg was not found and nothing was verified)

**Implementation Note**: After the automated checks pass, pause for the human to confirm the
manual item before Phase 3.

---

## Phase 3: CLI wiring and end-to-end check

### Overview

Expose the capability on the command line with the agreed window form, messages and exit codes,
then confirm on a 10 s clip that it is fast, vertical, audible and repeatable. Driven by
`/10x-implement`.

### Changes Required:

#### 1. Arguments and wiring

**File**: `src/ai_reel_montage/cli.py`

**Intent**: Add the three arguments and the call sequence parse → probe → validate → crop →
render. The CLI holds no montage logic; it converts exceptions into messages and exit codes.

**Contract**:

- New arguments: `--input PATH`, `--window A-B`, `--output PATH`. `--version` and the no-argument
  help behaviour stay as they are. When any of the three is given, all three are required.
  `--window` given more than once is a usage error.
- Two kinds of error, kept apart (decided in plan review):
  - **Usage errors** — a missing argument, an unknown argument, a repeated `--window` — keep
    argparse's own behaviour: `parser.error`, which prints the usage line and
    `ai-reel-montage: error: …` to stderr and raises `SystemExit(2)`. No parser subclass.
    `--window` is declared with `action="append"`, because argparse otherwise accepts a repeat
    and silently keeps the last value; more than one value calls `parser.error`.
  - **Engine errors** are returned by `main`, with one stderr line starting `error: `: `2` for an
    input path that does not exist, an output path that is the same file as the input,
    `WindowError` and `FramingError`; `1` for `VideoError`.
- Exit code `0` on success, with one line on stdout naming the output path, the frame count and
  the clip length in seconds.
- The output path is compared with the input path, both resolved, before the probe. When they
  are the same file the run stops with `error: output would overwrite the input` and exit code 2:
  `render_clip` renames over the output, so without this check the recording itself would be
  replaced by the clip.
- `cli.py` refers to `probe_source`, `render_clip` and the input-existence check through
  module-level names so unit tests can replace them; the unit tier never starts a subprocess and
  never needs a real file.

#### 2. CLI unit tests

**File**: `tests/unit/test_cli.py`

**Intent**: Cover the argument and error mapping without video, with the two shell functions
replaced by fakes.

**Contract**: the tests include at least these named cases.

- `test_valid_invocation_renders_expected_frame_range` — with a fake probe reporting 1920x1080,
  fps 50, 297 469 frames, `--window 10:04.78-10:14.78` calls the fake render with
  `FrameRange(30239, 500)` and `CropBox(608, 1080, 656, 0)` and returns 0.
- `test_window_past_end_exits_2_and_does_not_render` — `--window 5945-5955`; stderr names the
  window and the recording length; the fake render is not called.
- `test_malformed_window_exits_2`, `test_render_failure_exits_1` — returned codes.
- `test_missing_argument_exits_2`, `test_second_window_exits_2` — usage errors, asserted as
  `SystemExit` with code 2.
- `test_missing_input_exits_2_and_does_not_probe` — the existence check replaced by a fake
  reporting the file absent.
- `test_output_equal_to_input_exits_2_and_does_not_render`.
- The existing `test_version_flag_exits_zero` stays.

#### 3. End-to-end integration test

**File**: `tests/integration/test_cli_e2e.py` (new)

**Intent**: One test through the real entry point, so the wiring between the three layers is
exercised on real video.

**Contract**: `test_cli_writes_playable_clip` — `main([...])` with the real source and a 2 s
window returns 0 and the output probes as 1080x1920 with 100 frames;
`test_cli_out_of_range_window_writes_nothing` — `--window 5945-5955` returns 2 and no output file
exists. Both carry `@pytest.mark.integration`.

#### 4. Usage note

**File**: `README.md`

**Intent**: Show the one working invocation, so the next session and the user do not have to read
the code to run it.

**Contract**: a short "Usage" section with the command, the accepted window forms and the
statement that a window outside the recording is rejected.

### Success Criteria:

#### Automated Verification:

- Full test suite passes: `uv run pytest`
- Type checking passes: `uv run mypy`
- Linting passes: `uv run ruff check`
- Formatting is clean: `uv run ruff format --check src tests`
- Help lists the new arguments: `uv run ai-reel-montage --help | grep -e --window`

#### Manual Verification:

- A 10 s clip renders in under 30 s on this machine:
  `time uv run ai-reel-montage --input transfer-01a1f923/*.mp4 --window 10:04.78-10:14.78 --output out/s01.mp4`
  (research measured about 12 s for this window)
- The clip plays in a desktop video player: vertical, no black bars, picture not visibly
  stretched, match audio audible and in sync, length 10 s
- A second run to `out/s01-b.mp4` gives the same `sha256sum` as `out/s01.mp4`
- `--window 5945-5955` prints an error naming the window and the recording length, exits with
  status 2 and writes no file

**Implementation Note**: After the automated checks pass, pause for the human to confirm the
manual items. This closes the slice's implementation; `/10x-impl-review` is a separate session.

---

## Testing Strategy

### Unit Tests:

- Window grammar: the three accepted forms, and every malformed shape.
- Frame conversion: nearest-frame rounding with ties upward, off-grid starts, the last frame of
  the recording, past-the-end, after-the-end, empty and reversed windows.
- Seek and duration strings: exact at 50 fps, rounded down at 30000/1001.
- Crop geometry: the 1920x1080 case and a source narrower than 9:16.
- CLI: argument errors, error-to-exit-code mapping, and the values handed to the shell, with the
  shell replaced by fakes.

No unit test reads `transfer-*/`, opens a video or starts a subprocess.

### Integration Tests:

- Probe of the real source.
- Rendered clip properties (size, aspect, frame count, codecs, audio length).
- Byte identity of two renders of the same window.
- Off-grid start and last-frames windows.
- Failed render leaves no file.
- CLI end to end, success and rejection.

Every render is 2 s (about 2.5 s of wall time each at `veryfast`, one encoder thread). Nothing
compares against a hash stored in the repository.

### Manual Testing Steps:

1. Render the 10 s window at 10:04.78 with `time` and note the wall time.
2. Open `out/s01.mp4` in a player; check orientation, bars, stretch, audio and length.
3. Render again to a second path and compare `sha256sum`.
4. Run with `--window 5945-5955`; check the message, `echo $?` and that no file appeared.

## Performance Considerations

Expected cost is about 1.2 s of wall time per second of output with one encoder thread, of which
decoding is about 0.1 s (`research.md`, finding 5). The single encoder thread costs a factor of
about 3.4 against automatic threading and is kept for determinism. The whole integration tier
renders roughly eight 2 s windows, about 20 s in total.

## Migration Notes

None. No data, no prior behaviour to preserve beyond `--version`.

## References

- Related research: `context/changes/first-playable-clip/research.md`
- Change identity: `context/changes/first-playable-clip/change.md`
- Roadmap item: `context/foundation/roadmap.md`, S-01
- Requirements: `context/foundation/prd.md`, FR-001a and US-01
- Existing entry point: `src/ai_reel_montage/cli.py:10-25`
- Existing test: `tests/unit/test_cli.py:6-8`
- Bootstrap smoke test: `context/changes/bootstrap-verification/verification.md:63`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Window maths in the pure core

#### Automated

- [x] 1.1 Unit tests pass: `uv run pytest -m "not integration"` — b65638f
- [x] 1.2 Type checking passes: `uv run mypy` — b65638f
- [x] 1.3 Linting passes: `uv run ruff check` — b65638f
- [x] 1.4 Formatting is clean: `uv run ruff format --check src tests` — b65638f
- [x] 1.5 `core/` imports none of `subprocess`, `os`, `pathlib`, `json`, `time`, `random` — b65638f

### Phase 2: Probe and render in the IO shell

#### Automated

- [x] 2.1 Integration tests pass: `uv run pytest -m integration` — 2eff593
- [x] 2.2 Unit tests still pass: `uv run pytest -m "not integration"` — 2eff593
- [x] 2.3 Type checking passes: `uv run mypy` — 2eff593
- [x] 2.4 Linting passes: `uv run ruff check` — 2eff593
- [x] 2.5 Formatting is clean: `uv run ruff format --check src tests` — 2eff593
- [x] 2.6 `core/` does not import `shell` — 2eff593

#### Manual

- [x] 2.7 The integration tier reports passes, not skips, on this machine — 2eff593

### Phase 3: CLI wiring and end-to-end check

#### Automated

- [x] 3.1 Full test suite passes: `uv run pytest` — 0d07d52
- [x] 3.2 Type checking passes: `uv run mypy` — 0d07d52
- [x] 3.3 Linting passes: `uv run ruff check` — 0d07d52
- [x] 3.4 Formatting is clean: `uv run ruff format --check src tests` — 0d07d52
- [x] 3.5 Help lists the new arguments — 0d07d52

#### Manual

- [x] 3.6 A 10 s clip renders in under 30 s on this machine — 0d07d52
- [x] 3.7 The clip plays in a desktop video player: vertical, no black bars, not stretched, audio in sync, length 10 s — 0d07d52
- [x] 3.8 A second run gives the same `sha256sum` — 0d07d52
- [x] 3.9 `--window 5945-5955` prints an error, exits with status 2 and writes no file — 0d07d52
