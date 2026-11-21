---
date: 2026-11-21T15:44:30+01:00
researcher: Claude Fable 5.2 (session run for Bartosz Sosin)
git_commit: 0c6b53084c8c3d744d6a7773987e9518885081a4
branch: main
repository: ai-reel-montage
topic: "S-01 first-playable-clip: what does trimming a ~10 s window from the AV1 source cost, and what must the trim command look like to be exact, byte-identical and 9:16?"
tags: [research, ffmpeg, av1, trim, determinism, first-playable-clip]
status: complete
last_updated: 2026-11-21
last_updated_by: Claude Fable 5.2
---

# Research: S-01 first-playable-clip — trim cost, exactness and determinism on the real source

**Date**: 2026-11-21T15:44:30+01:00
**Researcher**: Claude Fable 5.2 (session run for Bartosz Sosin)
**Git Commit**: 0c6b53084c8c3d744d6a7773987e9518885081a4
**Branch**: main
**Repository**: ai-reel-montage

## Research Question

From `context/changes/first-playable-clip/change.md:16`: how long does trimming a ~10 s window
take on the AV1 source when the cut is made before decoding rather than after? The reel must come
out in minutes, so the trim has to bound decode work to the window.

Method, per `CLAUDE.md` rule 6 and the `10x-chain` skill: S-01 is an empirical slice, so every
answer below is a measurement against `transfer-01a1f923/`, not reading. All runs were bounded
windows of at most 10 s of output; the largest decode was 130 s of source (the output-seek
comparison). Measurements were run sequentially in one session, not delegated — parallel workers
would have shared the CPU and corrupted the timings.

## Summary

**The risk S-01 was sequenced first to expose does not materialise.** With the seek placed before
the input (`-ss T -i src`), decoding a 10 s window took 0.76–1.08 s at the four offsets tested
(600 s, 604.78 s, 3002.4 s, 5900 s), independent of how deep into the recording the window sits.
With the seek placed after the input, the same decode took 2.6 s at 30 s, 4.4 s at 60 s and 8.2 s
at 120 s — it grows by about 0.063 s per second of offset, which extrapolates (not measured) to
roughly 6 minutes for a window at 5900 s.

The decoder is not where the time goes. For a 10 s window the full job — seek, decode, centre
crop, scale to 1080x1920, single-threaded H.264 encode — took 12.2 s at preset `veryfast` and
30.7 s at preset `medium`; decode plus crop plus scale alone was 1.4 s of that. A 30 s reel is
therefore on the order of 40–90 s of encoding on this machine: minutes, not hours. The bootstrap
log's prediction that "AV1 decode will be the dominant render cost"
(`context/changes/bootstrap-verification/verification.md:65`) is contradicted for input-seek
trims: single-threaded x264 is the dominant cost.

Four further facts the plan must build on, all measured:

1. **Input seek is frame-exact here.** The 100 frames of a 2 s window at 62.4 s hashed identically
   whether sought before or after the input.
2. **Frame count needs `-frames:v`, not `-t`.** A start time that is not on the 20 ms frame grid
   is rounded up to the next frame, and `-t 10` then yields 499 frames in three of the six start
   values tried. `-frames:v 500` yielded 500 in both off-grid cases tried.
3. **Single-threaded encode with `-bitexact` is byte-identical across runs** in every pair tried,
   including with AAC audio and with `+faststart`. Byte identity also held at 16 threads, but the
   bytes differ from the 1-thread output, so a thread count that follows the machine is unusable.
4. **ffmpeg does not report a bad window.** A window past the end of the recording, one starting
   after the end, and a negative start all exit with status 0 and a short, empty or shifted file.
   Window validation has to be the engine's own.

Two things need fixing relative to the bootstrap smoke-test command: it leaves a non-square pixel
aspect on the output (displayed as 76:135, not 9:16) until `setsar=1` is added, and it uses `-t`.

## Environment

| Item | Value | Source |
| --- | --- | --- |
| CPU | AMD Ryzen 7 6800HS, 16 logical cores | `/proc/cpuinfo`, `nproc` |
| ffmpeg | 8.0.1-3ubuntu2 | `ffmpeg -version` |
| AV1 decoder picked by default | libdav1d (package 1.5.3-1) | ffmpeg stream-mapping line |
| H.264 encoder | libx264 (package 0.165.3222) | `dpkg -l` |
| Load during runs | 1.5 before the first run; up to 9 during, caused by the runs themselves | `uptime` |

Each timing below is wall-clock seconds, three consecutive runs, quoted as the three values or
their median. File cache was warm after the first run of each series.

## Detailed Findings

### 1. The source

Measured with `ffprobe` on the `.mp4` in `transfer-01a1f923/`:

- Video: AV1 Main, 1920x1080, `yuv420p` 8-bit, bt709 limited range, 50 fps constant
  (`r_frame_rate` and `avg_frame_rate` both 50/1), time base 1/12800, 297 469 frames,
  5949.38 s. Sample aspect ratio is not signalled.
- Audio: Opus, 48 kHz stereo, 5949.421 s.
- Container: MP4, `start_time` 0 for both streams, 2 711 873 324 bytes, 3.65 Mbit/s overall.
- **Keyframes sit every 4.8 s (240 frames)** in all four 40 s stretches sampled (from 0 s, 600 s,
  3000 s and 5899.2 s). Not verified for the whole file — a full packet scan was not run. Under
  that spacing an input seek decodes at most 239 frames before the window starts.
- Probing a 40 s stretch of packets anywhere in the file took 0.09–0.10 s, so the container index
  is usable for seeking and reading the duration is effectively free.

"Match time" in the delivered materials is seconds from the start of the recording, not football
clock time: the tracking report labels a clip `06:10–07:10 (370s–430s)`
(`transfer-01a1f923/match_tracking_report.md:63`). A window in S-01 can therefore be taken as
recording seconds with no offset. That the tracking file uses the same origin is S-02's question.

### 2. Trim cost: seek before the input versus after

Decode only, 10 s window (500 frames), default decoder threading, output discarded
(`-an -f null -`):

| Seek placement | Window start | Runs (s) |
| --- | --- | --- |
| before input (`-ss T -i`) | 600 s (on a keyframe) | 0.82, 0.79, 0.81 |
| before input | 604.78 s (one frame before a keyframe — worst pre-roll) | 1.08, 1.10, 1.07 |
| before input | 3002.4 s (mid-GOP) | 1.00, 1.01, 1.02 |
| before input | 5900 s (near the end) | 0.73, 0.76, 0.76 |
| after input (`-i … -ss T`) | 30 s | 2.56, 2.62, 2.64 |
| after input | 60 s | 4.42, 4.46, 4.33 |
| after input | 120 s | 7.55, 8.21, 8.81 |

- Input seek cost does not depend on the offset across the four offsets tested; the only
  variation is the pre-roll from the previous keyframe (0.8 s on a keyframe, 1.1 s at the worst
  position).
- Output seek cost rises with the offset: (8.21 − 4.42) / 60 ≈ 0.063 s per second of recording,
  i.e. the decoder runs at about 16x real time with all cores. Extrapolated to 5900 s this is
  about 370 s per window. This number is an inference from three points up to 120 s; it was
  deliberately not measured, because that would decode the whole recording.
- With the decoder forced to one thread (`-threads 1` before `-i`), the same input-seek decode
  took 3.0 s at 600 s and 4.2 s at 604.78 s. Decoder threading does not change the decoded
  pixels (finding 4), so there is no determinism reason to pay this.

### 3. Exactness of the cut

- **Same frames either way.** `-ss 62.4 -i src -t 2` and `-i src -ss 62.4 -t 2` both produced 100
  frames whose per-frame MD5 lists are identical (same SHA-256 over the list). 62.4 s is mid-GOP,
  so this exercises the decode-and-discard path. Tested at this one position.
- **Start time snaps upward to the frame grid.** With `-copyts`, the first frame kept was the
  source frame at 604.78 s for `-ss 604.78`, at 604.80 s for 604.785, 604.79, 604.799 and 604.80,
  and at 604.82 s for 604.801. A start between two frames selects the later one.
- **`-t` is not a frame count.** `-t 10` produced 500 frames for starts 604.78, 604.799 and 604.80
  but 499 for 604.785, 604.79 and 604.801. Replacing it with `-frames:v 500` produced 500 frames
  at 604.785 and 604.801 (the two off-grid starts retried).

Consequence for the plan: convert the window to integer frames in the pure core
(`start_frame = round(start_s * 50)`, `n_frames = round(duration_s * 50)`), pass `-ss` as
`start_frame / 50` and the length as `-frames:v n_frames`. This is plain arithmetic with no IO,
so it is unit-testable, and it is the same frame index S-02 will need to line up with the
tracking file (`stride` 3 over 50 fps per the tracking metadata block).

### 4. Byte-identical output

2 s window at 604.78 s, `crop=608:1080,scale=1080:1920`, libx264 `veryfast` CRF 20 `yuv420p`,
each variant encoded twice and compared by SHA-256:

| Variant | Two runs identical? | Same bytes as `-threads 1 -bitexact`? |
| --- | --- | --- |
| `-threads 1 -bitexact` | yes | — |
| `-threads 1 -bitexact`, decoder also `-threads 1` | (one run) | yes |
| `-threads 1 -bitexact -movflags +faststart` | yes | no (file layout differs) |
| `-threads 16 -bitexact` | yes | no |
| encoder threads left automatic, `-bitexact` | yes | no, and differs from the 16-thread file |
| `-threads 1` without `-bitexact` | yes | no (encoder tag written) |
| `-threads 1 -bitexact` plus AAC audio (10 s window) | yes | n/a |

- Decoded frames are identical across decoder threading: per-frame MD5s of 50 frames at 604.78 s
  matched between default threading, `-threads 1` and `libdav1d -threads 4`.
- Every variant was repeatable on this machine in the pairs tried; what changes the bytes is the
  encoder thread count, `-bitexact`, and container flags. The project rule "ffmpeg runs
  single-threaded with bit-exact flags" (`CLAUDE.md`, Pure core / IO shell rule) is the variant
  that does not depend on the core count, so it stands. The single thread needs to apply to the
  encoder only; the decoder may keep its default threads.
- Not tested: identity across machines, ffmpeg builds or library versions. The measurements only
  establish same-machine, same-build repeatability.

### 5. Full pipeline time and where it goes

10 s window at 604.78 s (worst pre-roll), `crop=608:1080,scale=1080:1920`, CRF 20, no audio:

| Configuration | Runs (s) | Output size |
| --- | --- | --- |
| decode + crop + scale, no encode | 1.42, 1.43, 1.44 | — |
| x264 `ultrafast`, 1 thread | 4.60, 4.71, 4.78 | 26.3 MB |
| x264 `veryfast`, 1 thread | 12.28, 12.18, 12.10 | 6.4 MB |
| x264 `medium`, 1 thread | 30.56, 30.65, 30.81 | 8.2 MB |
| x264 `veryfast`, automatic threads | 3.61, 3.64, 3.62 | 6.9 MB |
| x264 `medium`, automatic threads | 6.31, 6.75, 6.96 | 8.3 MB |
| x264 `veryfast`, 1 thread, plus AAC 128k audio | 12.24, 12.21, 12.28 | — |

- Per second of output at 1080x1920/50 fps with one encoder thread: about 1.2 s (`veryfast`) or
  3.1 s (`medium`). The bootstrap smoke test's "~6 s for a 2 s cut"
  (`verification.md:63`) is consistent with the `medium` default (3.1 s x 2).
- The determinism rule costs a factor of about 3.4 (`veryfast`) to 4.6 (`medium`) in wall time
  against automatic threading on this 16-core machine. For a 30 s reel that is roughly 37 s
  versus 11 s at `veryfast` — still inside the "minutes" guardrail, so there is no pressure to
  relax it.
- Transcoding the Opus audio to AAC added no measurable time.

### 6. Output geometry and playability

- An exact 9:16 crop of a 1080-high frame would be 607.5 px wide; with even dimensions required
  by `yuv420p`, 608x1080 is the nearest. Scaling it to 1080x1920 stretches the picture
  horizontally by 0.08% (607.5/608).
- **Without `setsar=1` the output is not flagged 9:16.** The smoke-test filter chain produced
  `sample_aspect_ratio=1216:1215`, `display_aspect_ratio=76:135`. Appending `setsar=1` gave
  `1:1` and `9:16`.
- Output of the measured command: H.264 High, level 4.2, `yuv420p`, bt709 limited range, 50 fps,
  500 frames, duration 10.000000 s, `start_time` 0. The source is already 8-bit bt709, so no
  colour conversion is involved.
- With audio: AAC stream starts at 0 and lasts 10.000000 s (470 AAC frames).
- Whether the short-form platforms accept 50 fps and level 4.2 without re-encoding was not
  tested; no upload was made.

### 7. Bad windows are silent

| Command window | Exit status | Result |
| --- | --- | --- |
| start 5945 s, 10 s (recording ends at 5949.38 s) | 0 | 219 frames (4.38 s), no warning at `-v error` |
| start 6000 s (after the end) | 0 | a 261-byte file with no frames |
| start −5 s, 10 s | 0 | 250 frames (5 s), not 500 |

ffmpeg's exit status cannot be used to detect any of these three. The engine has to read the
duration (5949.38 s for this file) and validate the window itself before calling ffmpeg, and
check the produced frame count afterwards. Validation of a window against a duration is pure
arithmetic and belongs in `core/`.

### 8. Crop inside ffmpeg versus frames piped through Python

`tech-stack.md` describes the eventual design as frames piped out of ffmpeg, cropped in numpy and
piped back (`context/foundation/tech-stack.md:32`). S-01's fixed centre crop does not need that,
but S-02's moving crop might, so both were timed on the same 10 s window, `veryfast`, CRF 20:

| Architecture | 1 encoder thread (s) | 16 encoder threads (s) |
| --- | --- | --- |
| one ffmpeg process, `crop` + `scale` filters | 12.25, 12.07, 12.33 | not run in this form |
| ffmpeg decode → raw `yuv420p` pipe → numpy slice → ffmpeg scale + encode | 11.75, 11.89, 12.07 | 4.16, 4.25, 4.25 |

- The pipe costs nothing measurable: 1.5 GB of raw frames through two pipes and a Python loop was
  not slower than the single process.
- The piped variant produced 500 frames and was byte-identical across two runs.
- **The two architectures do not produce the same bytes** for the same window (different
  SHA-256). The cause was not investigated. If S-01 pins an output hash in a test and S-02 later
  moves to pipes, that hash changes.

## Code References

- `src/ai_reel_montage/cli.py:10-25` — the CLI has only `--version`; there is no window, input
  or output argument yet.
- `src/ai_reel_montage/core/__init__.py`, `src/ai_reel_montage/shell/__init__.py` — both empty.
- `tests/unit/test_cli.py:6-8` — the single existing test.
- `pyproject.toml`, `[tool.pytest.ini_options]` — the `integration` marker for tests that need ffmpeg or the transfer
  folder already exists.
- `.gitignore` — `transfer-*/`, `out/` and `*.mp4` are ignored, so rendered clips cannot be
  committed by accident.

## Architecture Insights

- The window-to-frames conversion and window validation are the only logic in S-01 that is
  numbers in, numbers out. Everything else is a subprocess call. That gives the slice a natural
  split: a small pure function in `core/` (unit-tested) and one ffmpeg invocation in `shell/`
  (integration-tested against a bounded window).
- The command shape the measurements support:
  `ffmpeg -nostdin -ss <start_frame/50> -i <src> -frames:v <n> -vf "crop=608:1080,scale=1080:1920,setsar=1" -c:v libx264 -preset <p> -crf <q> -pix_fmt yuv420p -threads 1 -bitexact <out>`.
  Each element is backed by a finding above: seek before input (2), `-frames:v` (3), `setsar=1`
  (6), `-threads 1 -bitexact` (4).
- Byte identity makes a cheap integration test possible: render the same short window twice and
  compare hashes. Comparing against a hash stored in the repository would additionally tie the
  test to this ffmpeg build (finding 4, not tested across builds).

## Historical Context (from prior changes)

- `context/changes/bootstrap-verification/verification.md:63` — smoke test, "2 s cut at 600 s …
  ~6 s wall time". Supported: consistent with 3.1 s per output second at the default preset.
- `context/changes/bootstrap-verification/verification.md:65` — "AV1 decode will be the dominant
  render cost". Contradicted for input-seek trims: decode is about 1 s of a 12–31 s job. It would
  be true for output-seek trims deep in the recording.
- `context/changes/bootstrap-verification/verification.md:61` — ffmpeg 8.0.1 installed with
  libx264, aac and crop/scale. Supported: observed in this session.
- `.claude/skills/10x-chain/SKILL.md`, state section — "ffmpeg is not installed on this machine".
  Contradicted: stale, superseded by the bootstrap log and by this session.
- `context/foundation/roadmap.md:63` — "AV1, 1920x1080, 50 fps, 99 minutes". Supported
  (5949.38 s = 99.2 min).

## Related Research

None. This is the first research document in the repository; `context/archive/` is empty and
there is no `context/foundation/lessons.md`. The product scope is not mapped in
`~/sosek-workflow/context/registry.md`, so no stack assessment was loaded.

## Open Questions

These are choices for `/10x-plan`, not missing evidence. None blocks planning.

1. **Does the clip keep the match audio?** The PRD rules out a soundtrack and beat-syncing
   (`prd.md`, Non-Goals) but does not say whether the stadium and commentary audio stays. Keeping
   it costs nothing in time and stays byte-identical (findings 4 and 5). Product decision.
2. **Preset and CRF.** `veryfast` is 2.5x faster than `medium` single-threaded and produced a
   smaller file at the same CRF here; visual quality was not compared. A first choice can be
   revised later at no structural cost, but it changes output bytes.
3. **Filter-only or piped rendering for S-01.** Both cost the same; they do not produce the same
   bytes (finding 8). Starting with filters is simpler; starting with pipes avoids a later change
   of output bytes when S-02 needs a per-frame crop. Whether S-02 needs pipes at all (a
   time-varying `crop` filter is an alternative) is S-02's research.
4. **How the caller writes a window.** Seconds, `mm:ss`, or frames; start plus end or start plus
   length. The measurements only require that it resolves to integer frames before ffmpeg is
   called (finding 3).
5. **Not measured:** keyframe spacing over the whole file, platform acceptance of 50 fps
   level 4.2 output, and byte identity across machines or ffmpeg builds.
