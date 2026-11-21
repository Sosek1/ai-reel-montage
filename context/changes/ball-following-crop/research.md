---
date: 2026-11-21T18:21:01+01:00
researcher: Claude Fable 5.2 (session run for Bartosz Sosin)
git_commit: 3eab915cbf601bc927c05268f99f014b9eed3fae
branch: main
repository: ai-reel-montage
topic: "S-02 ball-following-crop: what does reading a window of the 398 MB tracking file cost, how does the tracking grid map onto source frames, how good is the ball track in real windows, and how can ffmpeg be given a crop that moves?"
tags: [research, tracking, ijson, ffmpeg, crop, determinism, ball-following-crop]
status: complete
last_updated: 2026-11-21
last_updated_by: Claude Fable 5.2
---

# Research: S-02 ball-following-crop — tracking read cost, frame mapping, ball-track quality and a moving crop

**Date**: 2026-11-21T18:21:01+01:00
**Researcher**: Claude Fable 5.2 (session run for Bartosz Sosin)
**Git Commit**: 3eab915cbf601bc927c05268f99f014b9eed3fae
**Branch**: main
**Repository**: ai-reel-montage

## Research Question

From `context/changes/ball-following-crop/change.md` (Risk, Open unknown, Verification) and the
session brief, five things had to be measured before S-02 can be planned:

1. What reading the ball positions of a window of some fifteen seconds costs in time and memory,
   and how that depends on how deep in the match the window sits.
2. How the tracking grid (about 16.67 fps) maps onto the 50 fps source, to the frame.
3. How good the ball data is in real windows: detected, predicted, missing, gap lengths, jumps.
4. Whether a 608x1080 crop moved horizontally can always contain the ball, unsmoothed.
5. How ffmpeg can be given a crop that changes over time, what each route costs, and what a
   change of route does to output bytes.

Method, per `CLAUDE.md` rule 6: S-02 is an empirical slice, so every number below comes from a
command run against `transfer-01a1f923/` in this session, unless it is labelled **extrapolation**
or **read**. The three-stage technique research was not run (it is reserved for S-03). One
library-API lookup was made (ijson 3.6.0 README via Context7: `items` builds whole objects,
`parse` yields `(prefix, event, value)`, and the two can be chained). No ffmpeg run exceeded 60 s
of source; the tracking file was loaded whole into memory exactly once (finding 1). Measurements
ran sequentially in one session, not delegated, so that timings did not share the CPU.

Camera-path smoothing, zoom and multi-window assembly were not investigated.

## Summary

**The two risks S-02 was sequenced to expose are both small, and one assumption behind the
slice's open unknown is wrong.**

1. **Reading a window by streaming is linear in the offset, and cheap.** `ijson.items` over
   `frames.item`, stopping after the window, took 0.04 s for a 15 s window at 0 s, 0.33 s at
   370 s, 2.3 s at 3000 s and 4.5 s at 5400 s (minute 90) — about 0.83 ms per second of offset —
   at a constant 35 MB of process memory, which is the interpreter's own baseline. `json.load` of
   the whole file took 5.07 s and 2589 MB. Streaming therefore buys memory, not time. A window in
   minute 90 costs 4.5 s of reading next to 12.9 s of encoding per 10 s of output (finding 5), so
   it stays inside "a reel in minutes". Seeking by byte offset instead reads the same window in
   0.004–0.013 s at any offset.
2. **The grids map exactly.** The file holds 99 157 samples whose `frame_idx` is 0, 3, 6, …,
   297 468 with no gap and no drift, and `frame_idx` is the zero-based source frame number:
   sample JPEGs named after frame numbers match exactly that source frame, and the ball sits at
   the recorded position in that frame and not in its neighbours.
3. **"Predicted" already means "interpolated", and "missing" comes only in long runs.** Of the
   99 157 samples, 73 300 are detected (73.9%), 21 115 predicted (21.3%) and 4 742 have no ball
   (4.8%). Predicted runs are at most 44 samples (2.64 s) long, and 6 210 of the 6 211 that lie
   between two detections are a straight line between them to within 0.02 px. The missing
   samples form 45 runs; the shortest is 47 samples (2.82 s), the longest 429 (25.74 s). So the
   "about 26% missing or predicted" in `change.md` is two different things: 21.3% that already
   carry a usable position, and 4.8% where "hold last known" freezes the crop for at least
   2.82 s every time it applies, and then jumps by more than half a crop width in 28 of the 44
   runs that have a detection on both sides.
4. **The crop can always contain the ball centre where a position exists.** Ball x ranges from
   3.51 to 1917.05 over the whole match, never outside the frame; a centred, clamped 608-wide
   crop contains it by construction. Sample-to-sample motion exceeded half the crop width
   (304 px) in 1 of 94 370 sample pairs.
5. **All three render routes work and produce the same pixels.** A `crop` filter with an
   expression in `n`, a `crop` filter driven by `sendcmd`, and numpy slicing of piped frames gave
   byte-identical cropped frames for a 500-frame moving crop. The two filter routes give
   byte-identical output files. The pipe route gives the same decoded pictures but a different
   file; with colour tags declared on the pipe the H.264 stream becomes identical and only 26
   bytes of container metadata differ. All routes cost 12.7–13.8 s for a 10 s window. No test in
   the repository pins a hash, so no route breaks a test; a constant crop written as an
   expression reproduces S-01's bytes exactly.

## Environment

Same machine and builds as the S-01 research
(`context/archive/2026-11-21-first-playable-clip/research.md`, Environment): AMD Ryzen 7 6800HS,
16 logical cores, ffmpeg 8.0.1-3ubuntu2, libx264, libdav1d. Additionally measured here:

| Item | Value | Source |
| --- | --- | --- |
| Python | 3.14.4 | `uv run python -V` |
| ijson | 3.6.0, backend `yajl2_c` | `ijson.backend`, `ijson.__version__` |
| numpy | 2.5.5 | `uv pip list` |
| Memory | 30 GiB total, 17 GiB available before the runs | `free -g` |
| Load | 1.3–1.4 before the read benchmarks, 3.5 before the encode benchmark | `uptime` |

Times are wall-clock seconds measured inside the process (`time.perf_counter`), so they exclude
interpreter start-up. Memory is peak resident set size (`ru_maxrss`) of a fresh process per
measurement. The tracking file was in the page cache for every run; **a cold-cache read was not
measured**.

## Detailed Findings

### 1. Cost of reading one window from the tracking file

**Layout (measured).** `transfer-01a1f923/full_match_tracks.json` is 398 443 992 bytes on a single
line. Top-level keys in order: `metadata`, `players`, `frames`. The `frames` array starts at byte
1 052 778; everything before it is 1 MB of metadata and per-player summaries. Each element of
`frames` is `{"frame_idx", "timestamp_sec", "ball", "players"}` and is about 4 kB, almost all of
it the `players` list. `ball` is either `null` or
`{"x", "y", "bbox", "confidence", "source"}`; `source` takes exactly two values in this file,
`"detected"` (73 300 times, `bbox` and `confidence` set) and `"predicted"` (21 115 times, both
`null`).

**Five ways to read a 15 s window (250 samples).** Each row is a fresh process; all five returned
the same 250 `(frame_idx, x, y, source)` tuples at every offset (equal SHA-256 of the result).

| Window start | `ijson.items("frames.item")`, 3 runs (s) | `ijson.parse`, filtered (s) | `ijson.items("frames.item.ball")` (s) | byte seek + `json.loads` per record, 3 runs (s) | byte seek + regex (s) |
| --- | --- | --- | --- | --- | --- |
| 0 s | 0.040, 0.038, 0.040 | 0.070 | 0.037 | 0.012, 0.012, 0.012 | 0.001 |
| 370 s | 0.330, 0.323, 0.334 | 0.729 | 0.268 | 0.012, 0.013, 0.012 | 0.002 |
| 1115 s | 0.914, 0.930, 0.891 | 1.895 | 0.732 | 0.011, 0.011, 0.011 | 0.001 |
| 3000 s | 2.355, 2.270, 2.213 | 5.256 | 1.981 | 0.008, 0.008, 0.008 | 0.001 |
| 5400 s (minute 90) | 4.497, 4.484, 4.568 | 9.272 | 3.445 | 0.009, 0.008, 0.009 | 0.001 |
| 5930 s | 4.665, 4.788, 4.901 | 9.773 | 4.000 | 0.005, 0.004, 0.004 | 0.001 |

- **Memory was 34.2–36.3 MB in all 54 runs of the table**, and a process that only imports the
  same modules peaks at 35.4 MB. None of the five variants adds measurable memory.
- **Streaming cost is linear in the offset**: 4.5 s / 5400 s ≈ 0.83 ms per second of recording
  for `ijson.items`. The parser has to tokenise every earlier frame, players included.
- `ijson.parse` with prefix filtering is about twice as slow as `ijson.items`: every token
  crosses into Python, and discarding the `players` list in Python costs more than letting the
  C backend build and drop it.
- `ijson.items("frames.item.ball")` is about 20% faster than whole records but yields no
  `frame_idx`, so it relies on position in the array (valid here by finding 2, but unchecked at
  read time).
- **Byte seek** bisects the file on the literal `{"frame_idx":`, then either parses each record
  of the window with `json.loads` or matches the ball fields with a regular expression. It does
  not depend on the offset. It relies on that literal marking record starts, which holds for
  this file's key order; a file written with different key order or whitespace would defeat it.
- **One full streaming pass** over all 99 157 frames, keeping ball fields only, took 5.39 s and
  peaked at 53.8 MB.
- **Naive whole-file load, run once:** `json.load` took 5.07 s and the process peaked at
  **2588.7 MB**. This is the number the plan runs from: it is no faster than streaming to minute
  90 and costs more than six times the file's size in memory.

**Against "a reel in minutes".** Measured: at most 4.9 s per window read by streaming, anywhere
in the recording. Extrapolation: a reel of three 10 s windows read independently would spend at
most about 15 s reading against about 39 s encoding (3 x 12.9 s, finding 5), under a minute in
total. One streaming pass that serves several windows is bounded by the 5.39 s full pass.

### 2. Mapping the tracking grid onto source frames

All statements are over the full `frames` array (99 157 elements), from one streaming pass.

- `frame_idx` equals `3 * k` for every element `k`: first 0, last 297 468, the only difference
  between neighbours is 3. **No gaps, no drift, zero-based.**
- The source has 297 469 frames (S-01 research, finding 1), numbered 0–297 468, so the last
  source frame is itself a sample and the tracking covers the recording end to end.
- `timestamp_sec` equals `round(frame_idx / 50, 2)` for every element (maximum absolute
  difference 0.0). It carries no information beyond `frame_idx`; `frame_idx` is the exact field.
- `metadata` states `video_fps: 50.0`, `stride: 3`, `effective_fps: 16.667`,
  `frames_processed: 99157` — consistent with the array.

**That `frame_idx` is the source frame number was checked against pixels, two ways:**

- The transfer folder holds four annotated JPEGs named `…_tracked_frame_N.jpg` for N = 3000,
  75 000, 150 000, 225 000. Each was compared (mean absolute grey difference) with source frames
  N−6 … N+6 extracted by `-ss N/50`. The minimum was at offset 0 in all four: for N = 150 000,
  4.41 at offset 0 against 15.40–15.79 at ±1; for N = 225 000, 5.14 against 5.63–5.85.
- Six samples were drawn (seeded) from the 400 fastest-moving detected samples, and a 64x64
  patch centred on the recorded `(x, y)` was cut from source frames N−3 … N+3. In all six the
  ball is centred in the patch of frame N and visibly displaced in N−1 and N+1 (inspected by
  eye, one image).

**Consequence.** For a window `[start_frame, start_frame + n_frames)` in source frames — the
`FrameRange` S-01 already computes (`src/ai_reel_montage/core/window.py:40-45`, `:90-101`) — the samples are
the elements with `frame_idx` in that range, an output frame `f` has its own sample exactly when
`f % 3 == 0`, and the other two of every three output frames have none. A window whose first
frame is not a multiple of 3 starts one or two frames before its first sample, so any rule that
fills frames between samples needs the sample before the window and the one after it as well.

### 3. Ball-data quality in real windows

Counts are samples at 60 ms spacing. "Longest non-detected" counts predicted and null together.
`|dx|` is the horizontal distance between two consecutive positioned samples, in source pixels.

| Window (s) | Detected | Predicted | Null | Longest null run | Longest predicted run | `\|dx\|` p50 / p95 / p99 / max |
| --- | --- | --- | --- | --- | --- | --- |
| 370–430 (report: 06:10–07:10) | 837 (83.7%) | 155 (15.5%) | 8 (0.8%) | 8 samples, 0.48 s (see below) | 17, 1.02 s | 4.7 / 48.9 / 156.4 / 186.6 |
| 1115–1175 (report: 18:35–19:35) | 721 (72.1%) | 279 (27.9%) | 0 | — | 22, 1.32 s | 7.3 / 39.1 / 96.7 / 174.9 |
| 673–733 (blind) | 831 (83.1%) | 169 (16.9%) | 0 | — | 13, 0.78 s | 4.6 / 44.5 / 125.0 / 153.5 |
| 1430–1490 (blind) | 725 (72.5%) | 275 (27.5%) | 0 | — | 30, 1.80 s | 5.3 / 56.6 / 87.8 / 173.9 |
| 2301–2361 (blind) | 753 (75.3%) | 247 (24.7%) | 0 | — | 11, 0.66 s | 7.7 / 64.5 / 137.8 / 162.4 |
| 2855–2915 (blind) | 780 (78.0%) | 220 (22.0%) | 0 | — | 19, 1.14 s | 10.2 / 67.5 / 127.7 / 165.4 |
| 4315–4375 (blind) | 850 (85.0%) | 150 (15.0%) | 0 | — | 14, 0.84 s | 4.5 / 33.6 / 62.0 / 208.2 |
| 4990–5050 (blind) | 857 (85.7%) | 143 (14.3%) | 0 | — | 15, 0.90 s | 9.3 / 42.5 / 73.9 / 134.4 |
| whole recording | 73 300 (73.9%) | 21 115 (21.3%) | 4 742 (4.8%) | 429, 25.74 s | 44, 2.64 s | 5.6 / 47.4 / 114.6 / 595.0 |

The six blind starts were drawn with `random.Random(20261121).randrange(0, 5889)` before any
window was looked at; each window is 60 s (1000 samples).

- **The report's "good" windows are not as good in the delivered file as the report says.**
  `match_tracking_report.md:70-71` gives 90.2% and 82.5% direct detection, measured on separate
  60 s clips at 25 fps. The same windows in `full_match_tracks.json` (stride 3) are 83.7% and
  72.1% detected. Both report rows say 100% tracked; in the full-match file the first window
  begins with 8 null samples, the tail of a null run covering 364.02–370.44 s.
- **Predicted samples are linear interpolation.** There are 6 213 predicted runs; the median
  length is 2 samples, the 99th percentile 21, the maximum 44 (2.64 s). Of these, 6 211 lie
  between two detected samples, and 6 210 of those lie on the straight line between their
  neighbours to within 0.02 px. The one exception starts at 3968.46 s: the position steps by
  595.0 px from the last detection and the run deviates from the straight line by up to 500.6 px.
  It is the only sample pair in the recording with `|dx|` above 304 px.
- **Missing samples come only in long runs.** 45 null runs: 5 of 47–50 samples (2.82–3.00 s),
  34 of 51–166 samples (3.06–9.96 s), 6 of 167–429 samples (10.02–25.74 s). No null run is
  shorter than 47 samples and no predicted run longer than 44, so the upstream solver fills gaps
  up to about 2.6 s and leaves longer ones empty (no gap of 45 or 46 samples occurs to show the
  exact threshold). 44 runs have a detected sample on both sides; the 45th starts at 5923.7 s and
  runs to the end of the recording. The six longest start at 5923.7 s (25.7 s), 72.8 s (14.5 s),
  3125.8 s (13.0 s), 1972.1 s (12.7 s), 3807.1 s (10.7 s) and 1012.1 s (10.3 s).
- **How often a window meets a null run.** Cutting the recording into 396 consecutive 15 s
  windows: 339 contain no null sample, 57 contain some, 49 are more than 10% null, 13 more than
  half, 1 entirely. In 13.9% of the 396 windows the longest null run is at least 1 s; in 10.9%
  at least 3 s.
- **What "hold last known" does on a null run.** It holds the crop still for the run's length —
  at least 2.82 s, since no shorter run exists — and then moves it by the distance the ball
  travelled meanwhile: more than 304 px in 28 of the 44 two-sided runs, 1876.1 px at most.
  Predicted samples need no fallback to have a position; they already have one.
- **Jumps between consecutive samples**, whole recording, 94 370 positioned pairs: median
  5.6 px, 90th percentile 30.3, 99th 114.6, 99.9th 174.1, maximum 595.0 (the exception above).
  Between two detected samples the maximum is 226.9 px (67 044 pairs); pairs above 100 px:
  231 detected-to-detected, 224 detected-to-predicted, 223 predicted-to-detected, 507
  predicted-to-predicted.
- **Detected positions are not the raw box centre.** `x` equals the centre of `bbox` to within
  0.01 px in 21.2% of detected samples; the difference is 0.3 px at the median, 10.5 px at the
  99th percentile, 35.2 px at most, and `x` lies outside the box in 1.7% of them. The solver has
  already moved positions; `x`/`y`, not `bbox`, is the track.
- Detected `confidence` ranges from 0.14 upward, median 0.61. Ball box width: median 15 px,
  99th percentile 51 px, maximum 105 px.

### 4. Geometry of an unsmoothed moving crop

The crop is 608x1080 on a 1920x1080 source (`src/ai_reel_montage/core/framing.py:29-39`), so its
left edge `x` can take values 0–1312 and only horizontal motion is possible.

- **Ball centre never leaves the frame:** over the 94 415 positioned samples `x` ranges from
  3.51 to 1917.05 and `y` from 4.9 to 1074.0; no predicted sample is extrapolated outside.
- A crop centred on the ball and clamped to 0–1312 therefore contains the ball centre at every
  positioned sample. This follows from the arithmetic and the range above; it is not a separate
  measurement, and it means **the slice's automatic check ("ball inside the crop for every
  output frame") cannot fail at sample frames under that rule** — it guards the clamp and the
  frame mapping against regressions, it does not show the visible ball is in the picture. The
  evidence that recorded positions match the picture is finding 2.
- The clamp is active for 3.1% of positioned samples at the left edge and 4.6% at the right
  (ball within 304 px of a frame edge); there the ball is in the crop but not centred.
- Ball boxes reach from −0.19 to 1922.0 in x, so a check phrased as "the whole ball box is
  inside the crop" would fail at the frame edge for reasons no crop can fix.
- **Between samples.** If the crop holds each sample's position for three frames, the ball
  drifts from the crop centre by at most the next `|dx|` before the crop catches up: at most
  226.9 px between detected samples, under the 304 px half-width, with the single 595 px pair as
  the only case in the recording where the ball could leave the crop. If the crop is
  interpolated linearly between samples, the largest detected-to-detected step is 75.6 px per
  output frame in source pixels (226.9 / 3), which is 134 px per frame in the 1080-wide output
  (scale 1080/608).
- **How the raw path looks**, crop x per sample, centred and clamped, three windows: median step
  4–6 px, 95th percentile 38–48 px, maximum 154–186 px; 7.5%, 9.1% and 12.0% of consecutive
  moving steps reverse direction (windows 1115–1175, 673–733, 370–430). This is the jitter S-03
  exists to remove; it is recorded here only as the unsmoothed baseline.
- **Crop x must be even.** With `yuv420p`, the `crop` filter rounds an odd x down: `x=657` gave
  the same frames as `x=656` and not as `x=658`. With `exact=1` an odd x produced frames equal
  to neither. Slicing chroma planes in numpy has the same constraint. The crop position
  therefore has a resolution of 2 source pixels.

### 5. Giving ffmpeg a crop that moves

Test material: frames 19 000–19 499 (380–390 s, no null samples), crop x per output frame from
linear interpolation between samples, centred, clamped, rounded to even: 201 distinct values
from 6 to 1312, largest step 58 px per frame.

**Pixel exactness** — crop only, no scaling, raw `yuv420p` out, SHA-256 over all 500 frames,
compared with slicing the fully decoded frames in numpy:

| Route | Result |
| --- | --- |
| numpy slicing of decoded frames (reference) | 500 frames |
| `crop=608:1080:x='<x0>+d1*gte(n,k1)+d2*gte(n,k2)+…':y=0` (one term per change of x) | identical |
| the same with `exact=1` | identical |
| the same sum written over `t` instead of `n` (thresholds half a frame early) | identical |
| `sendcmd=f=<file>,crop=608:1080:<x0>:0`, file lines `<k/50> crop x <value>;` | identical |
| the same with every time half a frame early | identical |
| `x='if(eq(n,0),v0,if(eq(n,1),v1,…'` nested 499 deep | **fails**: filter init error |

- Inside the `crop` filter `n` counts from 0 at the first frame after the input seek, and
  `sendcmd` times are relative to that frame too; both follow from the identical hashes.
- The expression parser rejects deep nesting: `if(…)` nested 90 deep was accepted, 100 deep was
  rejected ("Missing ')' or too many args"). A flat sum has no such limit in the sizes tried:
  3 597 characters for this window, 28 414 characters (2 069 terms) for a 60 s window at
  1115–1175 s, accepted both as a command-line argument and from a file via `-/vf`.
- Decode plus moving crop of that 60 s window, two runs each: static crop 9.45, 9.49 s;
  expression as argument 9.43, 9.86 s; expression from file 10.85, 11.31 s; `sendcmd` 11.23,
  11.30 s. The three moving variants gave the same frame hash as each other. Run order and
  machine load were not controlled, so differences of this size are not attributed to the route.

**Full render** — the S-01 command (`src/ai_reel_montage/shell/video.py:150-192`: input seek,
`-frames:v`, `scale=1080:1920,setsar=1`, libx264 `veryfast` CRF 20, one thread, AAC, `-bitexact`)
on the same 10 s window, three runs each:

| Route | Runs (s) | 3 runs byte-identical | Output file | Decoded frames | H.264 stream |
| --- | --- | --- | --- | --- | --- |
| S-01 static `crop=608:1080:656:0` | 11.32, 12.10, 12.08 | yes | A (7 457 696 B) | a | a |
| static as expression `x='656+0*n'` | 12.24, 12.44, 12.30 | yes | **same as A** | a | a |
| moving, `crop` expression | 12.89, 12.88, 13.16 | yes | B (8 323 115 B) | b | b |
| moving, `sendcmd` | 12.85, 12.73, 12.90 | yes | **same as B** | b | b |
| moving, numpy through pipes | 13.80, 12.98, 13.28 | yes | differs (8 323 067 B) | **same as b** | differs |
| moving, numpy through pipes, colour tags on the pipe | 13.35, 13.65, 12.66 | yes | differs (8 323 089 B) | **same as b** | **same as b** |

- Every route is repeatable byte for byte on this machine, produced 500 frames, and carried an
  AAC stream starting at 0 and lasting 10.000 s (470 frames). In the pipe routes the second
  ffmpeg took the audio from the source as a second input with the same `-ss` and `-t`.
- **The two filter routes are interchangeable down to the file bytes.**
- **A constant crop written as an expression gives S-01's exact file.** Switching the filter
  from literal numbers to an expression does not by itself change output.
- **Why pipes gave different bytes in S-01's research (its finding 8), for this test:** raw
  video on a pipe carries no colour description, so the output is written with colour range,
  matrix, primaries and transfer "unknown" instead of `tv`/`bt709`, which changes the stream
  headers. With `-color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709`
  declared on the pipe input, the H.264 stream hash equals the filter route's. The file is then
  26 bytes shorter; in a 2 s render without audio the difference is also 26 bytes
  (780 432 against 780 458) and the differing bytes begin at offset 778 446, i.e. in the index
  written after the video data. Which field differs was not investigated.
- **Cost:** a moving crop adds no measurable time to the route it runs on; the moving renders
  are about 0.7 s slower than the static ones on the same window, with a 12% larger file, which
  fits the encoder working on more motion rather than the crop mechanism. The three routes are
  within 1 s of each other.

**What this means for tests that pin hashes.** No test in the repository stores a hash:
`tests/integration/test_video.py:87-91` renders twice and compares the two files with each
other, and `grep` for `sha`, `hash`, `md5` over `src/` and `tests/` finds nothing else. So no
route breaks an existing test. A ball-following clip necessarily differs from S-01's centre-crop
clip of the same window, whatever the route. Staying on filters keeps one property that pipes
lose: the fixed-crop output of the current command stays reproducible bit for bit (row 2). If a
later slice moves to pipes, every output file changes once (at least in container bytes), and
any hash stored by then must be re-recorded; declaring the colour tags keeps the pictures and
the video stream unchanged across that move.

## Code References

- `src/ai_reel_montage/cli.py:28-35` — the CLI takes `--input`, `--window`, `--output`; there is
  no argument for the tracking file yet.
- `src/ai_reel_montage/cli.py:74-97` — wiring: parse window, probe, `to_frame_range`,
  `centre_crop`, `render_clip`. S-02's read of the tracking file and its crop path slot in here.
- `src/ai_reel_montage/core/window.py:40-45`, `:90-101` — `FrameRange(start_frame, n_frames)` in
  source frames; the same indices select tracking samples (finding 2).
- `src/ai_reel_montage/core/framing.py:20-39` — `CropBox` and `centre_crop`; one fixed box per
  clip, even width and even `x`.
- `src/ai_reel_montage/shell/video.py:150-192` — `_render_command`; the filter string at
  `:172-173` is the only place the crop enters ffmpeg.
- `src/ai_reel_montage/shell/video.py:118-147` — `_publishing`: partial file, frame count check,
  rename. Its docstring states it does not depend on how frames are produced, so it serves a
  piped render as well.
- `src/ai_reel_montage/shell/__init__.py` — docstring already names "tracking-JSON streaming" as
  shell work; no such module exists yet.
- `pyproject.toml:8-10` — numpy, scipy and ijson are already dependencies; `:41` ignores missing
  stubs for `ijson`, so its results must be given types at the boundary.
- `tests/integration/test_video.py:87-91` — the only byte-identity test; compares two renders,
  stores no hash.

## Architecture Insights

- **The pure part of S-02 is a function from samples to crop positions.** Input: the window's
  frame range and an array of `(frame_idx, x or missing)`; output: one even crop x per output
  frame. Sample selection, filling the two frames between samples, the null-run fallback, the
  clamp and the "ball inside crop" predicate are all arithmetic on arrays and belong in `core/`.
  Reading the JSON and building the ffmpeg argument belong in `shell/`.
- **The reader should take `frame_idx` from the file rather than assume position.** The exact
  3-frame grid is a property of this file; reading the field costs 20% more than position-based
  reading (finding 1) and makes a different stride or a gap visible instead of silently
  shifting the crop. `metadata.stride` and `metadata.video_fps` are in the first megabyte and
  can be compared with the probed source.
- **Both filter routes take the crop path as plain text** — a sum expression or a `sendcmd`
  file — and that text is a pure function of the crop array, so it can be built and unit-tested
  without ffmpeg. A flat sum is required; nested conditionals stop working near 100 levels.
- **Zoom is the next thing to move, and it was not tested here.** Whether the `crop` filter can
  change `w`/`h` per frame, by expression or by command, was not measured (S-04). The pipe route
  has no such open point; the filter routes do.
- **A per-match index is possible but not needed for the time budget.** Byte seek makes the read
  independent of the offset without any side file (finding 1), at the price of relying on the
  file's exact serialisation.

## Historical Context (from prior changes)

- `context/changes/ball-following-crop/change.md` (Risk) — "Tracking is sampled at 16.67 fps over
  a 50 fps source, so times have to be mapped between the two grids." Supported, and simpler than
  stated: the file carries source frame numbers, exactly every third frame (finding 2).
- `context/changes/ball-following-crop/change.md` (Risk) — "only the needed window may be read,
  streamed (ijson), never the whole file into memory." Supported on memory (35 MB against
  2589 MB). Streaming is not faster than loading: 4.5 s to minute 90 against 5.07 s (finding 1).
- `context/changes/ball-following-crop/change.md` (Open unknown) and
  `context/foundation/roadmap.md:93` — "missing or predicted rather than detected (about 26% of
  positions)". Partial: the total is right (26.1%), but it merges 21.3% predicted samples, which
  carry interpolated positions, with 4.8% null samples, which carry none (finding 3).
- `context/foundation/prd.md:146`, `context/foundation/roadmap.md:161` — "the 26% of predicted
  (rather than detected) ball positions". Contradicted on the count: 21.3% are predicted; the
  remaining 4.8% are absent.
- `transfer-01a1f923/match_tracking_report.md:70-71` — 100% tracked, 90.2% and 82.5% directly
  detected in the two named windows. Not reproduced by the delivered full-match file: 83.7% and
  72.1% detected, and 8 null samples at the start of the first window. The report's figures come
  from separate 25 fps clip runs (`match_tracking_report.md:77`, `:118`).
- `transfer-01a1f923/match_tracking_report.md:167` — 95.2% tracked (94 415 / 99 157), 73.9%
  detected (73 300 / 99 157). Supported exactly.
- `context/archive/2026-11-21-first-playable-clip/research.md`, finding 8 — filters and pipes
  "do not produce the same bytes … The cause was not investigated." Supported, and the cause is
  now partly known: missing colour tags change the stream; with tags, 26 bytes of container
  metadata remain (finding 5).
- `context/archive/2026-11-21-first-playable-clip/research.md`, finding 1 — "That the tracking
  file uses the same origin is S-02's question." Answered: same origin, frame 0 (finding 2).
- `context/foundation/tech-stack.md:32` — the design is described as frames piped through numpy.
  Still open: the measurements show pipes are not required for a moving crop of fixed size.

## Related Research

- `context/archive/2026-11-21-first-playable-clip/research.md` — the source recording, trim
  cost, frame-exact seeking and byte identity; this document builds on its findings 1, 3, 4, 8.

No `context/foundation/lessons.md` exists. The repository is not a Gridaly work repo, so there
was no work branch to resolve, and it is not mapped in `~/sosek-workflow/context/registry.md`,
so no stack assessment was loaded.

## Open Questions

These are choices for `/10x-plan`, not missing evidence. **None blocks planning**; questions 2
and 3 must be decided in the plan because the crop path cannot be written without them.

1. **How the window is read.** Streaming with ijson (4.5 s at minute 90, tolerant of any valid
   JSON, what `change.md` names) or byte seek (0.01 s, tied to this file's serialisation).
   Blocks planning: no.
2. **What the crop does on the two output frames between samples.** Hold the last sample (crop
   steps every third frame) or interpolate linearly (crop moves every frame, by up to 76 source
   px). Both keep the ball centre inside the crop in all but one sample pair of the recording.
   Blocks planning: no, but the plan has to pick one.
3. **The fallback for null runs, and for a window that starts inside one.** "Hold last known"
   means a still crop for 2.82–25.74 s followed by a jump of up to 1876 px, and it is undefined
   when the window begins in a null run (the 370–430 s window does) unless the reader looks back
   before the window. Alternatives the data allows: move linearly across the run between the two
   surrounding detections, fall back to the centre crop, or reject such windows. Owner: user
   (per `change.md`). Blocks planning: no, but the plan has to pick one and FR-002 requires it
   to be documented.
4. **Whether predicted samples are treated differently from detected ones in S-02.** They are
   already straight lines between detections, so using them as they are is equivalent to
   interpolating. Blocks planning: no.
5. **What exactly the automatic check asserts.** Ball centre, not ball box; on sample frames
   only or on interpolated positions for every output frame; and what it asserts during a null
   run, where there is no position to test. Under a centred, clamped crop the check holds by
   construction. Blocks planning: no.
6. **Render route.** Expression, `sendcmd` or pipes cost the same and give the same pictures.
   Filters keep the current command and S-01's bytes; pipes are the route `tech-stack.md`
   describes and the only one with no open point for zoom. Blocks planning: no.
7. **How the caller supplies the tracking file,** and whether a run without it still produces
   the S-01 centre crop. Blocks planning: no.
8. **Not measured:** a cold-cache read of the tracking file; time-varying crop size in the
   `crop` filter; which container field accounts for the 26-byte difference; byte identity
   across machines or ffmpeg builds; any tracking file other than this one.
