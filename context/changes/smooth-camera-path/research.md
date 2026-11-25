---
date: 2026-11-25T19:04:24+01:00
researcher: Claude Fable 5.2 (session run for Bartosz Sosin)
git_commit: 6e7fb4ea41d000f1014dd31314472d80f304b60d
branch: main
repository: ai-reel-montage
topic: "S-03 smooth-camera-path, research stage 3 of 3: synthesis of the web findings and the knowledge base, closed by measurement on the two evaluation windows — the nine points documentation could not settle, Open Roadmap Question 1, and the material for the smooth-versus-straight choice"
tags: [research, camera-path, smoothing, whittaker, l1-trend, determinism, evaluation-windows, smooth-camera-path]
status: complete
last_updated: 2026-11-25
last_updated_by: Claude Fable 5.2
---

# Research: S-03 smooth-camera-path — synthesis and measurements on the evaluation windows

**Date**: 2026-11-25T19:04:24+01:00
**Researcher**: Claude Fable 5.2 (session run for Bartosz Sosin)
**Git Commit**: 6e7fb4ea41d000f1014dd31314472d80f304b60d
**Branch**: main
**Repository**: ai-reel-montage

## Research Question

Stage 3 of the three-stage technique research `CLAUDE.md` rule 6 prescribes for a "which
technique" slice. Inputs: `research/web-findings.md` (stage 1, what the literature says) and
`research/knowledge-base.md` (stage 2, what the library documentation says). Stage 2 ends with
nine points that reading could not settle. This document treats that list as a measurement plan
on the two evaluation windows and, for each point, says what came out or why the measurement
does not decide it. Two things were fixed in advance by the brief:

- **Open Roadmap Question 1** (`context/foundation/roadmap.md:106`) must be closed here: should
  the smoothing treat predicted ball samples differently from detected ones?
- **Smooth path or straight pans with sharp corrections** is an aesthetic choice that belongs to
  the user. This document prepares the material and gives no verdict.

**Method and its limits.** Every number below comes from a command run in this session against
`transfer-01a1f923/full_match_tracks.json` or the match recording, unless it is labelled
**extrapolation**, **read** (taken from stage 1 or 2 without re-checking) or **arithmetic**. The
ball track of the whole match (99 157 samples: 73 300 detected, 21 115 predicted, 4 742 without a
ball — the same counts as the S-02 research) was extracted once and every experiment ran on it.
Scratch scripts, not product code; they and their logs are kept outside the repository in the
session notes folder (`.../side-session-notes/local_5cea3b08-…/s03-research-measurements/`).
Timings were taken while two ffmpeg renders ran on 2 of the 16 cores, so they are upper bounds.
No ffmpeg run exceeded one 60 s window. Work ran sequentially in one session, not delegated.

**Conventions.** "Window A" is 06:10–07:10 (source frames 18 500–21 499), "window B" is
18:35–19:35 (55 750–58 749). The crop is 608 px wide on a 1920 px source, so the crop centre
lives in 304..1616 and the crop's left edge in 0..1312. Smoothing strength of the L2 smoother is
quoted as its **half-gain cut-off in Hz** (finding 5 gives the conversion to λ). "Ball outside
the crop" uses exactly `check_follow`'s predicate (`src/ai_reel_montage/core/camera.py:131-133`)
on the even, clamped crop x the renderer receives.

## Summary

1. **Open Roadmap Question 1 is closed: do not treat predicted samples differently.** Give them
   the same weight as detections. In a controlled experiment — straight chords implanted over
   about 10 000 real detections, in the run pattern of the real predicted mask — the path
   smoothed with weight 1 was the closest to the path smoothed from the true detections at every
   cut-off from 1 Hz down (RMS error 5.5–12.9 px), weight 0.25 was worse (10.1–15.3 px) and
   weight 0 worst (11.4–22.3 px). Excluding them also breaks the ball-in-crop check, which
   counts predicted positions as tracked: on the whole match, zero-weighting put the recorded
   ball outside the crop in 24–78 samples at cut-offs where weight 1 lost none. The predicted
   samples are not what hurts the path; finding 2 says what does.
2. **A data-driven smoothing strength is unusable on this material.** REML chose
   λ = 2.2·10⁻⁴² on window B — no smoothing at all, output equal to input — and returned NaN for
   every case with a zero weight; GCV left the path with more direction reversals than the raw
   ball track itself (143–159 per minute against 137 in window A, 92–102 against 76 in B). The
   strength has to be a hand-set constant.
3. **Unconstrained L2 smoothing cannot be both calm and safe.** With one global strength the
   ball stays in the crop on both windows down to 0.7 Hz, and over the whole match only down to
   1.0 Hz (6 samples lost at 0.7 Hz, 87 at 0.5 Hz, 1 325 at 0.25 Hz). Anything calmer needs an
   inclusion rule. Two were measured: a bounded least-squares solver (works, 1.4–10.5 s per
   window, hit its iteration limit in 4 of 10 runs) and repeating the banded solve with raised
   weights where the ball escapes (works, at most 17 ms and 41 repeats, zero samples lost on the
   whole match).
4. **Every route measured is bit-reproducible here, across four scipy releases.** The float
   paths of the banded L2 solve, the reweighted variant, `lsq_linear` and `linprog` were
   byte-identical on repeat runs and across scipy 1.15.3 / 1.16.3 / 1.17.1 / 1.18.1 with numpy
   2.2.6 / 2.3.5 / 2.5.5, Python 3.13 and 3.14, default and single-thread BLAS settings — on this
   one machine. But the
   ℓ1 trend-filter LP has more than one optimum: simplex and interior-point gave paths up to
   16.6 px apart. That route is deterministic only while the solver method is named.
5. **`scipy.signal.whittaker_henderson` is not needed.** Fifteen lines over
   `scipy.linalg.solveh_banded` reproduce it to 8·10⁻¹² px, so the `scipy>=1.14` floor can stay.
6. **One solve on the 50 fps grid replaces "smooth, then upsample".** Giving the samples their
   weight and every other frame weight 0, with λ multiplied by 27, matches the 16.67 Hz solve to
   0.28 px and needs no interpolator; an interpolating `CubicSpline` on top of the sample-grid
   solve overshoots by at most 2.0 px.
7. **A window's first and last seconds depend on track that lies outside the window.** With the
   track `read_ball_track` keeps today (one positioned sample each side) the path at the edge of
   window B differs from the same path computed with context by up to 27 px at 0.5 Hz and 120 px
   at 0.25 Hz. Three seconds of context bring that to 0.01 px and 5.8 px, five seconds to 0.00
   and 0.18 px.
8. **Two facts about the material that the roadmap does not have.** Window A is not fully
   covered: its first 25 frames lie in a run without a ball (finding 1). And the largest camera
   swings in window A are not ball motion: for 4.3 s the track alternates between a ball waiting
   at a corner kick and, on the one frame inspected there, a false detection in the penalty
   area 780–1 120 px away (finding 2).
9. **The aesthetic choice has its material.** Ten clips and two side-by-side comparisons are in
   `out/s03-research/` (git-ignored); the ten clips all passed through `check_follow` and
   `render_clip`. The numbers that distinguish the candidates are in finding 10; which one reads
   as camera work is for the user to say.

### The nine stage-2 points at a glance

| # | Point (`research/knowledge-base.md`, last section) | Outcome | Finding |
| --- | --- | --- | --- |
| 1 | `whittaker_henderson` needs scipy 1.18 | Closed in stage 2; made moot — a banded solve gives the same numbers on scipy 1.15–1.18 | 5, 12 |
| 2 | Open Roadmap Question 1: weight of predicted samples | **Closed: same weight as detections** | 3 |
| 3 | Is a data-driven λ safe? | **Closed: no.** REML returns λ ≈ 0 or NaN, GCV under-smooths | 4 |
| 4 | Which grid; PCHIP or CubicSpline | **Closed:** one solve on the 50 fps grid, or sample grid + cubic; overshoot under 2 px | 6 |
| 5 | λ is not portable | **Closed:** keep the constant in Hz; factors 27 and 81 confirmed | 5 |
| 6 | L2 or L1 | **Not decided, by design** — clips and figures prepared for the user | 10, 11 |
| 7 | Check or constrain; solver in the deterministic path | **Closed on the first half:** below 1 Hz a constraint is required, and it can be had without a solver. Second half measured clean across four scipy releases, with one caveat | 7, 8 |
| 8 | Which numbers become assertions | **Partly:** baseline and candidate figures measured; thresholds wait for the choice in point 6 | 1, 10, 12 |
| 9 | Edge mode on short windows | **Closed:** the edge depends on track outside the window; 3–5 s of context removes it | 9 |

## Environment

Same machine as the S-01 and S-02 research: AMD Ryzen 7 6800HS, 16 logical cores,
ffmpeg 8.0.1-3ubuntu2.

| Item | Value | Source |
| --- | --- | --- |
| Python | 3.14.4 (project), 3.13.18 (cross-version runs) | printed by the probe script |
| scipy / numpy | 1.18.1 / 2.5.5 (pinned by `uv.lock`) | `scipy.__version__`, `numpy.__version__` |
| Other builds tried | scipy 1.17.1 + numpy 2.5.5, 1.16.3 + 2.3.5, 1.15.3 + 2.2.6 | `uv run --no-project --with …` |
| Load | 1.4 before the measurements; two single-threaded ffmpeg renders ran during most of them | `uptime` |

## Detailed Findings

### 1. What the two evaluation windows contain

| | Window A 06:10–07:10 | Window B 18:35–19:35 |
| --- | --- | --- |
| Samples inside the window | 1 000 | 1 000 |
| Detected / predicted / no ball | 837 / 155 / 8 | 721 / 279 / 0 |
| Predicted runs | 48, median 2 samples, longest 17 (1.02 s) | 79, median 2, longest 22 (1.32 s) |
| Ball x range | 174.6–1709.1 px | 5.8–1539.8 px |
| Largest sample-to-sample step | 186.6 px (3 110 px/s) | 174.9 px (2 916 px/s) |
| Frames where a centred crop is clamped, left / right | 4.0% / 3.0% | 4.3% / 0.0% |

(The counts in the track `read_ball_track` returns are slightly different because it adds
samples outside the window: 838/155 for A from frame 18 525 on, 722/279 for B.)

- **Window A does not have full ball coverage in this file.** Samples 18 501–18 522 (8 samples)
  have `ball: null`; they are the tail of a 108-sample run without a ball, frames 18 201–18 522
  (6.48 s). The first positioned sample in the window is frame 18 525. The render log confirms
  it: 25 fallback frames, 2 975 tracked. The roadmap's "100% ball coverage"
  (`context/foundation/roadmap.md:174`) comes from `match_tracking_report.md:63`, which reports
  a separately tracked 25 fps clip (`clip_60s_370_430.mp4`, 1 500 frames), not
  `full_match_tracks.json`. Window B is fully covered in both.
- **Share of predicted samples differs by a factor of 1.8** between the windows (15.5% and
  27.9%), so the pair does exercise Open Roadmap Question 1.
- **Where the slope breaks.** The second difference of ball x is 0.00 px inside predicted runs
  (maximum 0.02, they are straight lines). At the two ends of a run it is 8.3 px at the median
  in A and 6.5 in B, with a 95th percentile of 158 and 98 px. Among detections it is 1.0 / 1.2 px
  at the median and 14.2 / 9.7 px at the 95th percentile. So the ends of predicted runs are
  where the track bends hardest, five to eight times the typical detection.
- **Raw S-02 path as the baseline to beat**: 79 direction reversals per minute in A and 64 in B
  (counted on the even-pixel crop x); peak speed 3 111 and 2 916 px/s, RMS acceleration 11 062
  and 6 413 px/s², and 48% and 38% of the velocity energy above 1 Hz (on the unrounded centre,
  tracked frames).
- **Where the ball's own motion sits in frequency** (velocity spectrum at the sample rate):
  in window B 74.7% of the energy is above 0.25 Hz, 51.3% above 0.5 Hz, 40.3% above 1 Hz and
  17.5% above 2 Hz; in window A 87.6%, 74.7%, 47.0% and 26.1%. There is no gap between "motion"
  and "jitter" to place a cut-off in — every cut-off removes real ball motion, which is why
  finding 7 exists.
- **Detection noise is small.** Residual of detected samples against a 4 Hz smooth: 5.3 px RMS
  in A, 3.5 px in B (95th percentile 8.1 and 5.8 px) — under 1% of the crop width.

### 2. The violent motion in window A is a tracker identity switch, not noise

Between 5.4 s and 14.2 s into window A the track reads (`full_match_tracks.json`, frames
18 768–19 212): detected at x = 353.6, eight predicted samples in a straight line, detected at
x = 1432–1438 for 1.8 s, two predicted samples, detected at x = 1092 for 1.5 s, four predicted
samples, detected at x = 310–318 for 4.2 s, four predicted samples, detected at x = 1096.

- **One frame was inspected for each plateau.** Frame 19 100 (x = 310): the recorded position is
  the ball at the corner flag, with a player standing over it — a corner kick being set up.
  Frame 18 850 (x = 1434): the recorded position is among the players in the penalty area while
  a ball lies at the corner flag in the same frame. Median detector confidence is 0.52 on the
  1432 plateau and 0.74 on the 310 plateau. The 1092 plateau was not inspected.
- **Consequence.** During 4.3 s (5.4–9.7 s into the window) in which, on the evidence of those
  two frames, the ball is waiting at the corner, the track travels 353 → 1432 → 1092 → 310, and
  every candidate path follows it (see `out/s03-research/paths-A.png`). The predicted chords
  here are not an estimate of a ball in flight; they are a straight line between two different
  objects, covered at about 2 000 px/s.
- **How common, whole match.** Detected plateaus (under 1 px of motion per sample) lasting 1 s
  or more: 128, covering 4 713 samples, 4.8% of the match, the longest 9.12 s. Sample pairs
  faster than 1 000 px/s: 3 188 (3.4%); faster than 2 000 px/s: 862 (0.9%). **Not measured:**
  how many of those plateaus are false detections rather than a ball that really is at rest;
  two frames were inspected by eye, both in this one episode.
- **The source is not a fixed wide shot.** The two inspected frames, 5 s apart, show the same
  corner of the pitch framed differently and a broadcast scoreboard overlay: the recording is an
  operator-panned camera. Ball x is therefore a position in an already moving picture, and a
  crop that holds still in source pixels is not a still shot. Seen on two frames; not
  quantified.

This is upstream of smoothing and outside S-03 as scoped (`change.md` names the problem as
jitter). It is recorded because it will dominate what the user sees in the window A clips and
because no smoother removes it: a smoother can only decide how the camera travels between the
two places.

### 3. Open Roadmap Question 1 — predicted samples (stage-2 point 2)

**How different is the path** (L2 smoother, weight on predicted samples 1 / 0.25 / 0, compared
at 50 fps over the window):

| Cut-off | A: w=0 vs w=1, max / RMS px | B: w=0 vs w=1, max / RMS px | A: w=0.25 vs 1, max | B: w=0.25 vs 1, max |
| --- | --- | --- | --- | --- |
| 2.0 Hz | 57.4 / 4.4 | 48.4 / 6.4 | 15.8 | 5.7 |
| 1.0 Hz | 41.5 / 4.9 | 92.2 / 10.5 | 20.6 | 15.2 |
| 0.5 Hz | 91.5 / 11.3 | 55.6 / 11.3 | 52.1 | 28.9 |
| 0.35 Hz | 96.0 / 14.0 | 58.9 / 15.2 | 59.1 | 29.2 |
| 0.25 Hz | 86.9 / 15.6 | 65.8 / 20.4 | 56.6 | 41.7 |

So the choice is visible: up to 96 px, 16% of the crop width. Stage 1 expected the difference to
be small because a chord is close to what a second-order smoother draws; that is not what
happens. Removing 16–28% of the data points makes the smoother locally stiffer, so the path
changes well outside the runs themselves. Smoothness barely moves: RMS acceleration is 3–12%
lower with weight 0, reversals per minute within ±4.

**Which one is closer to the truth** — the controlled experiment. Take the whole-match track;
shift the real predicted mask in time by 7 000, 23 000, 41 000 and 66 000 samples; wherever the
shifted mask lands on a run of real detections with a real detection on both sides, replace
those detections by the straight chord. That implants 9 977–10 287 chord samples in 3 505–3 561
runs (median length 2, longest 33–44), the real run-length distribution. The reference is the
path smoothed from the untouched detections; the error is measured within 0.6 s of an implant.

| Cut-off | RMS error, w = 1 | RMS error, w = 0.25 | RMS error, w = 0 |
| --- | --- | --- | --- |
| 2.0 Hz | 10.8–13.9 px | 10.7–13.8 | 11.1–12.6 |
| 1.0 Hz | 9.6–12.9 | 10.1–13.3 | 11.4–13.5 |
| 0.5 Hz | 7.6–11.1 | 11.0–14.1 | 15.2–19.2 |
| 0.35 Hz | 6.5–9.8 | 12.1–14.9 | 16.8–21.3 |
| 0.25 Hz | 5.5–8.5 | 12.7–15.3 | 18.5–22.3 |

(Ranges are over the four shifts.) At 2 Hz the three are indistinguishable; from 1 Hz down,
weight 1 is best in all four shifts and the gap widens with smoothing strength. The 95th
percentile says the same: 7.5–10.1 px for weight 1 at every cut-off, 27–46 px for weight 0 at
0.5 Hz and below.

**How wrong the chord itself is**, same implants: RMS 23.5–29.5 px against the true ball.
By run length, the largest error within a run is 0.8–0.9 px at the median for runs of 1–2
samples, 3.1–3.3 px for 3–5 samples, 7.9–9.0 px for 6–10 and 19–26 px for runs of 11–44
samples; the worst single run was 559 px. Runs of 1–2 samples are 64–66% of all runs.

**What exclusion does to the guarantee.** `check_follow` counts a frame as tracked when it lies
between positioned samples, predicted or not (`core/camera.py:97-112`), so the predicted
position is part of what must stay in the crop. On the whole match, sample grid: with weight 1
the recorded ball is outside the crop in 0 samples at 2 Hz and at 1 Hz; with weight 0 in 78 and
24. The largest distance between the path and a predicted sample is 218 px (w = 1) against
606 px (w = 0) at 2 Hz.

**Answer.** Predicted samples are treated exactly like detected ones: same weight, same
inclusion bound. Three measured reasons — it is the closest to the path complete detections
would give; it keeps `check_follow` passable; and it removes the only argument stage 1 had
against convolution filters (they take no weights), though findings 6 and 7 give other reasons
not to pick those.

**Limit of this answer.** The implants fall on stretches the detector did see. Real predicted
runs fall where it failed, which is not a random place (finding 2 shows one cause). The
experiment measures what a chord of the real length distribution costs on ordinary play; it
cannot measure the chord's error where the detector actually lost the ball, because there is no
truth there. Detector `confidence` as a weight was not measured.

### 4. Is a data-driven λ safe? (stage-2 point 3) — no

| Selector | Window A | Window B |
| --- | --- | --- |
| `whittaker_henderson(lamb="reml")`, all weights 1 | NaN (the track has NaN at weight 0) | λ = 2.18·10⁻⁴², output equals input to 0.0 px |
| same, predicted weight 0 | NaN, 0 finite outputs | NaN, 0 finite outputs |
| same, predicted weight 0.25 | — | λ = 2.18·10⁻⁴² |
| `make_smoothing_spline` GCV, all positioned | 143 reversals/min, a_rms 5 180 px/s² | 92 reversals/min, a_rms 3 940 |
| same, detected only | 159 reversals/min | 102 reversals/min |

- REML drives λ to zero on the real track: the criterion reads the data as noise-free. On six
  10 s pieces of window B it returned 0.0 six times; on five pieces of window A 0.0, 0.0, 0.01,
  1.16 and 0.0. With any zero weight in the input and λ → 0 the system is singular and the
  function returns NaN without raising — a single zero weight among 1 001 ones was enough.
- The same function is sound on data it was made for: a synthetic sine plus 5 px Gaussian noise
  gave λ = 531 (cut-off 0.55 Hz), and 509 with a zero-weight run. The failure is specific to
  this track, as stage 2 suspected, and stronger than suspected.
- GCV does not do what is wanted either: its path reverses direction more often than the raw,
  unrounded ball centre (137 per minute in A, 76 in B, counted the same way).
- The second half of the question — do the two windows get similar λ — has no meaning once the
  selector fails. **Settled: one hand-set constant, the same for every window.**

### 5. Units of the smoothing constant (stage-2 point 5) and the hand-written solver

- **λ and Hz.** The order-2 penalised least-squares smoother on a uniform grid has gain
  1 / (1 + λ(2 − 2cos ω)²) (arithmetic). Solving for gain ½ gives a cut-off, which is the one
  quantity that does not change with the grid:

  | Half-gain cut-off | λ on the 16.67 Hz sample grid | λ on the 50 fps grid, data at every third frame (×27) |
  | --- | --- | --- |
  | 2.0 Hz | 3.40 | 91.8 |
  | 1.0 Hz | 50.7 | 1 369 |
  | 0.5 Hz | 796.8 | 21 514 |
  | 0.35 Hz | 3 308.7 | 89 336 |
  | 0.25 Hz | 12 692.8 | 342 706 |
  | 0.15 Hz | 97 845.7 | 2 641 835 |

- **The factors, checked numerically** on window B at 0.5 Hz. Solving on the 50 fps grid with
  weight 0 off the samples and λ × 27 matches the 16.67 Hz solve to 0.28 px at the samples;
  × 9 misses by 49.6 px and × 81 by 68.9 px. Linearly upsampling first and giving every frame
  weight 1 needs × 81 and still misses by 7.1 px. So the same number means three different
  strengths depending on the grid and on which frames carry data — stage 2's warning, with the
  factors attached. **The plan should store the constant in Hz and derive λ.**
- **The escape hatch works.** A banded solve of (W + λ DᵀD) z = W y through
  `scipy.linalg.solveh_banded` matches `scipy.signal.whittaker_henderson` to 2.6·10⁻¹² px with
  unit weights and 8.0·10⁻¹² px with zero weights (window B, λ = 100). Stage-2 point 1 found
  that the scipy function needs `scipy>=1.18`; this shows nothing in S-03 needs that function.
  The only thing it adds is REML, which finding 4 rules out.
- **Cost.** One banded solve of a 60 s window on the 50 fps grid (about 3 000 unknowns):
  0.3–0.65 ms. The whole match on the sample grid (99 157 unknowns), 14 solves: 0.2 s.

### 6. Which grid the smoother runs on (stage-2 point 4)

Sample-grid solve followed by an upsampler, against a single solve on the 50 fps grid; RMS
acceleration, peak acceleration and RMS jerk of the resulting 50 fps path, window A:

| Cut-off | linear upsample | PCHIP | CubicSpline | single 50 fps solve |
| --- | --- | --- | --- | --- |
| 1.0 Hz | 1 993 / 17 421 / 140 966 | 1 214 / 10 922 / 27 519 | 1 159 / 5 841 / 6 165 | 1 151 / 5 855 / 6 063 |
| 0.5 Hz | 768 / 5 512 / 54 288 | 455 / 2 771 / 7 409 | 444 / 1 847 / 1 374 | 443 / 1 841 / 1 366 |
| 0.25 Hz | 264 / 1 537 / 18 680 | 154 / 685 / 1 689 | 153 / 513 / 235 | 153 / 513 / 234 |

(px/s², px/s², px/s³; window B gives the same ordering.)

- **Linear upsampling of a smooth path throws the smoothness away**: jerk is 23–80 times that of
  the cubic, because the path gets a corner 16.67 times a second. This is what `np.interp` in
  today's `ball_centre` would do to any sample-grid smoother.
- **PCHIP costs 1.3–1.9 times the peak acceleration and 4.5–7.2 times the jerk** of the cubic in
  window A. It never overshoots (0.0000 px in all six cases).
- **CubicSpline on a smoothed path overshoots by at most 1.97 px** past the two neighbouring
  smoothed samples (0.04–0.39 px at 0.5 Hz and below). Stage 2's worry was real for raw data —
  an interpolating cubic through the unsmoothed samples overshoots by 19.95 px in A and 13.26 px
  in B — and is negligible after smoothing.
- **The single 50 fps solve is equivalent to sample-grid + CubicSpline** to 0.12–1.27 px, with
  the same derivative figures, and overshoots by at most 1.35 px. It needs no interpolator, and
  frames between samples are simply frames with weight 0 — the same mechanism that bridges a run
  without a ball.
- **Upsample-then-smooth** (linear interpolation to 50 fps, then smooth every frame at weight 1)
  differs from the others by 2.6–7.4 px in window B and by up to 121 px in window A, where the
  linearly bridged gap at the start is then smoothed as if it were data.

**Settled by measurement:** smooth on the 50 fps grid with data only at sample frames, or smooth
on the sample grid and upsample with a cubic; not linear, and not upsample-first. The touchline
overshoot either way is under 2 px and is removed by the clamp the path needs anyway (finding 7).

### 7. Check or constrain (stage-2 point 7)

**What an unconstrained L2 path does to the ball** (predicted weight 1, 50 fps, tracked frames):

| Cut-off | A: max / p95 distance centre–ball | A: frames outside, margin | B: max / p95 | B: frames outside, margin | Whole match, samples outside |
| --- | --- | --- | --- | --- | --- |
| 2.0 Hz | 106 / 22 px | 0, +175 px | 94 / 11 px | 0, +6 px | 0 of 94 415 |
| 1.0 Hz | 205 / 61 | 0, +100 | 193 / 28 | 0, +6 | 0 |
| 0.7 Hz | 251 / 105 | 0, +54 | 222 / 47 | 0, +6 | 6 (6 episodes) |
| 0.5 Hz | 316 / 141 | 2, −12 | 257 / 69 | 0, +6 | 87 (65 episodes) |
| 0.35 Hz | 403 / 180 | 42, −98 | 329 / 107 | 2, −25 | 479 (180 episodes) |
| 0.25 Hz | 452 / 216 | 73, −148 | 400 / 166 | 22, −97 | 1 325 (292 episodes) |

(Window B's +6 px margin is the ball at x = 5.8 against the left picture edge, where the crop is
clamped at 0; it is the same in the raw S-02 path.) So `check_follow` as a post-hoc gate is not
enough: it would reject the 0.5 Hz path on window A and every path calmer than 1 Hz somewhere in
the match. `test_ball_is_inside_the_crop_over_the_whole_match` fails for any unconstrained L2
strength below 1.0 Hz.

**The picture edge.** Before clamping, the unconstrained centre path is outside 304..1616 in
7.5–8.5% of window A's frames at 0.5–2 Hz, by up to 126 px (273 px in window B at 2 Hz), because
it follows the ball to the touchline. Clamping afterwards is what S-02 does and it holds the
bound. Clamping the *target* first and then smoothing does not: the path still overshoots the
range by 10–73 px in window A, and it loses more ball samples on the whole match (32 at 1 Hz,
108 at 0.7 Hz, 303 at 0.5 Hz, against 0, 6 and 87). **Settled: clamp the path, not the target;
the right-edge bound stays where F4 put it.**

**Two ways to add inclusion**, both requiring the centre to stay within H px of the ball at
every sample (and inside 304..1616):

| | `scipy.optimize.lsq_linear` (bounded least squares) | repeated banded solve with raised weights |
| --- | --- | --- |
| Mechanism | one constrained solve, trust-region iterations | solve; multiply by 1.3 (or 2) the weight of each sample whose ball is more than H from the clamped centre; repeat until none is |
| Window A, 0.25 Hz, H = 280 | 100 iterations, **status 0 = iteration limit reached**, 10.5 s, a_rms 317, a_peak 2 778 | 21 repeats, 9 ms, a_rms 338, a_peak 2 711 |
| Window B, 0.25 Hz, H = 280 | 15 iterations, converged, 1.4 s, a_rms 223, a_peak 2 778 | 12 repeats, 5 ms, a_rms 208, a_peak 1 216 |
| All 10 window runs (0.15–0.5 Hz, H 200–280) | 1.4–10.5 s; 4 of 10 stopped at the iteration limit (all in window A) | 0–41 repeats, at most 17 ms, all converged |
| Whole match, sample grid | not run | 0.5 Hz: 6 repeats, 179 samples re-weighted, 0 outside. 0.25 Hz: 13 repeats, 2 311 re-weighted, 0 outside |
| Ball outside the crop, windows | 0 frames in all 10 | 0 frames in all 14 |

- Both hold the ball in. Inclusion is not free: at 0.25 Hz it raises RMS acceleration from 153
  to 317–338 px/s² in window A and from 163 to 208–223 in window B, and peak acceleration by a
  factor of 1.6–5.4, because the path is forced to correct where the ball runs away.
- The reweighted route is three orders of magnitude faster, has no solver, no tolerance and no
  iteration limit that changes the answer, and is the same arithmetic as the unconstrained
  smoother. With a multiplier of 2 instead of 1.3 it needs half the repeats and gives a rougher
  path (window A, 0.25 Hz: a_rms 455 against 338).
- A first version of the reweighting loop did not converge (weights reached 1.3·10³⁶ in 60
  repeats): it compared the unclamped centre with a box that collapses to a point at the
  touchline. Judging the clamped centre fixed it. Worth a named test.
- **What stays open for the plan** is not whether to constrain — any strength below 1 Hz must —
  but H: 280 leaves the ball up to 24 px from the crop edge, 200 keeps it 104 px in and costs
  about twice the acceleration (window A, 0.25 Hz: a_rms 707–767 against 317–455).

### 8. Solver routes and determinism (stage-2 point 7, second half)

Float 50 fps paths hashed with SHA-256, both windows, eight routes (banded L2, reweighted L2,
`lsq_linear`, ℓ1 trend LP with `highs-ds` / `highs-ipm` / `highs`, L1 path LP with `highs-ds` /
`highs-ipm`):

- **Repeat runs in one process:** identical for all 16 window–route pairs.
- **Across builds:** identical for all 16 pairs across scipy 1.18.1 + numpy 2.5.5 on
  Python 3.14.4, the same on Python 3.13.18, scipy 1.17.1 + numpy 2.5.5, scipy 1.16.3 +
  numpy 2.3.5 and scipy 1.15.3 + numpy 2.2.6.
- **Threads:** identical with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` and with the default.
- **But the ℓ1 trend LP is not unique.** `highs-ds` and `highs-ipm` gave paths differing by up to
  5.67 px in window A and 16.6 px in window B, and the even crop x differed in 73 and 85 frames.
  `method="highs"` picked the simplex result both times. The L1 path LP (penalties on first,
  second and third differences, no data term) agreed between the two methods to 4·10⁻⁹ px and
  gave the same crop x.
- **End to end:** see finding 11 for the rendered files.

**Limits.** One machine, one CPU, x86-64 wheels; no scipy release after 1.18.1; `lsq_linear`
checked at one setting per window. Stage 2 said reproducibility across versions "cannot be
settled from documentation" — it is now measured for four releases and is clean, which is
evidence about the past, not a guarantee about 1.19. The banded route depends on a LAPACK
Cholesky and nothing else; the LP routes depend on HiGHS and on the method name.

### 9. Edges and short windows (stage-2 point 9)

The path of a window computed from the track `read_ball_track` keeps (to the nearest positioned
sample on each side, `src/ai_reel_montage/shell/tracking.py:90-108`) against the path of the
same window computed with 10 s more track on each side:

| Smoother | A 0.5 Hz, first / last second | B 0.5 Hz, first / last | B 0.25 Hz, first / last | Interior 50 s |
| --- | --- | --- | --- | --- |
| Banded L2 (free ends) | 29.9 / 0.6 px | 24.4 / 27.1 | 119.7 / 50.3 | ≤ 0.54 px |
| Butterworth order 2, `sosfiltfilt`, default odd pad | 0.0 / 0.6 | 43.3 / 33.1 | 52.8 / 52.0 | ≤ 0.19 |
| Gaussian, `mode="nearest"` | 0.0 / 0.6 | 1.0 / 15.4 | 3.9 / 11.7 | 0.000 |
| Gaussian, `mode="reflect"` | 0.0 / 0.6 | 26.6 / 42.6 | 42.7 / 72.3 | 0.000 |

- Every smoother invents the camera's motion in the last half-second differently. The L2
  smoother extrapolates the trend it sees; at 0.25 Hz on window B it starts moving at −172 px/s
  where the context-aware path moves at +17 px/s. Stage 2 judged the edge transient "a non-issue
  at our window length" for `filtfilt` from the pad length; measured, it is 33–53 px.
- **How much context removes it** (banded L2 against 30 s of context, maximum over the window):
  window B at 0.5 Hz — 27.1 px with none, 37.2 with 1 s, 1.06 with 2 s, 0.01 with 3 s; at
  0.25 Hz — 119.7, 44.4, 33.6, 5.84 px, and 0.18 px with 5 s. Window A stays at 29.9 px until
  the context reaches past the 6.48 s gap before it (0.13 px at 8 s).
- **Short windows are edge everywhere** (banded L2, own track against context, windows cut from
  B): 3 s windows differ by 50 px at the median and 125 px at worst at 0.5 Hz, in 65% of their
  frames; 10 s windows by 30 px / 94 px in 20% of frames; 20 s windows by 34 px / 63 px in 8%.
  At 0.25 Hz a 5 s window is off by more than 2 px in 80% of its frames.
- **Why this matters beyond looks:** S-05 cuts several windows from one match. A clip's path
  would otherwise depend on where the window was cut, and two windows sharing a boundary would
  not agree on the camera position there.

**Settled:** the smoother must be given track beyond the window — about 3 s at 0.5 Hz and 5 s at
0.25 Hz, i.e. roughly 1.5 / cut-off (extrapolation from two strengths) — or, where a run without
a ball sits at the edge, up to the next positioned sample as today. That is a change to what
`read_ball_track` keeps and is the one place S-03 touches `shell/`.

### 10. Smooth or straight: what the numbers can and cannot say (stage-2 point 6)

Five paths per window were built, each on the product's track, each ending in the same
even-pixel clamp, each passing `check_follow`:

| # | Path | Formulation | Solver |
| --- | --- | --- | --- |
| 0 | Raw S-02 | today's `crop_path` | none |
| 1 | L2 smooth, 0.5 Hz | order-2 penalty, inclusion H = 280 by reweighting (×1.3) | banded solve |
| 2 | L2 smooth, 0.25 Hz | same, calmer | banded solve |
| 3 | L1 straight pans | min Σ\|c − ball\| + 200·Σ\|Δ²c\|, box H = 250 | `linprog`, `highs-ds` |
| 4 | L1 hold + eased pans | min 10·Σ\|Δc\| + Σ\|Δ²c\| + 100·Σ\|Δ³c\|, box H = 250, no data term (Grundmann's weights) | `linprog`, `highs-ds` |

Measured on tracked frames of the unrounded 50 fps centre unless marked; window A / window B:

| Metric | 0 raw | 1 L2 0.5 Hz | 2 L2 0.25 Hz | 3 L1 straight | 4 L1 hold + eased |
| --- | --- | --- | --- | --- | --- |
| Reversals per minute (even-pixel path) | 79 / 64 | 26 / 28 | 18 / 17 | 13 / 9 | 9 / 5 |
| Peak speed, px/s | 3 111 / 2 916 | 1 123 / 974 | 1 055 / 749 | 1 072 / 832 | 1 549 / 1 010 |
| RMS acceleration, px/s² | 11 062 / 6 413 | 464 / 379 | 340 / 208 | 1 844 / 1 084 | 668 / 240 |
| Peak acceleration, px/s² | 173 758 / 144 117 | 2 277 / 1 483 | 2 711 / 1 216 | 47 204 / 32 320 | 5 477 / 2 101 |
| Share of frames exactly straight (zero second difference) | 0.72 / 0.73 | 0.00 / 0.00 | 0.00 / 0.00 | 0.98 / 0.99 | 0.38 / 0.22 |
| Share of frames with the crop still (even-pixel path) | 0.46 / 0.31 | 0.39 / 0.29 | 0.44 / 0.33 | 0.46 / 0.29 | 0.74 / 0.60 |
| Distance crop centre–ball, 95th percentile, px | 8 / 1 | 142 / 77 | 200 / 149 | 217 / 190 | 246 / 245 |
| Distance crop centre–ball, maximum, px | 129 / 298 | 276 / 298 | 280 / 298 | 251 / 298 | 251 / 298 |
| Velocity energy above 1 Hz | 48% / 38% | 0.2% / 0.1% | 0.3% / 0.3% | 7.9% / 4.5% | 6.0% / 0.3% |
| Solve time per window | — | 0–3 ms | 4–7 ms | 82–86 ms | 225–249 ms |

(The raw path is 72–73% "straight" because it is linear between samples; it bends at every
sample. The 298 px maximum in window B is the ball at x = 5.8 with the crop clamped at the left
picture edge, identical for all five. In window B path 1 needed no inclusion correction.)

What the table shows, without choosing:

- **All four candidates remove the jitter by the count that defines it**: reversals per minute
  fall from 64–79 to 5–28 on the path that is rendered.
- **Paths 1–2 and path 3 fail in opposite places.** The L2 paths have low acceleration
  everywhere and are never straight: the camera is always slightly turning. The L1 trend path is
  straight in 98–99% of frames and concentrates all its acceleration in corners — peak
  acceleration 32 320–47 204 px/s², 17–27 times the L2 paths, because at 16.67 Hz a corner is a
  one-sample change of speed. Whether that reads as "an operator correcting" or "a mechanical
  snap" is exactly the question the clips are for.
- **Path 4 is a third aesthetic**, not asked for but produced by the literature's own weights:
  the crop is still in 60–74% of frames and the ball spends most of the time near the crop edge
  (95th percentile of the distance is 245 px of a possible 250). It has no pull toward the ball
  at all.
- **Every candidate lets the ball sit far from the centre.** At the 95th percentile the ball is
  77–246 px off-centre against 1–8 px for the raw path. That is the price of calm in a 608 px
  crop and it is the same trade for L2 and L1.
- **Numbers that would decide it do not exist.** Stage 1 found no validated objective score for
  virtual-camera quality; none of the metrics above ranks "smooth" against "straight" — each
  candidate wins the metric its own objective minimises.

**Pointers for watching** (seconds into each window; positions read from
`out/s03-research/paths-A.png` and `paths-B.png`):

- Window A, 5–10 s: the tracker switch of finding 2. All candidates swing to the penalty area
  and back while the ball waits at the corner; they differ in how.
- Window A, 14–17 s: the corner is taken; the ball crosses about 800 px in 0.3 s.
- Window A, 49–60 s: the ball is almost still. The camera should be too; compare how each
  candidate settles.
- Window B, 7–9 s and 41–44 s: a turn at the left side; the L2 paths round it, the L1 path
  makes one corner.
- Window B, 53–57 s: the fastest stretch, 1 350 px to the left touchline and back in about 3 s;
  the crop is clamped at 0 in the middle of it.

### 11. The rendered material and what rendering showed

All files are in `out/s03-research/` (git-ignored; 1080x1920, 3 000 frames, 60 s each).

| File | `check_follow` | Crop x changes | Expression | Render | SHA-256 (first 16) |
| --- | --- | --- | --- | --- | --- |
| `A-0-raw-s02.mp4` | 2 975/2 975, 25 fallback | 1 627 | 22 551 chars | 86.1 s | 3447de627667ed0c |
| `A-1-L2-smooth-0.50Hz.mp4` | 2 975/2 975 | 1 823 | 25 015 | 96.3 s | 1348d244d84f1eb0 |
| `A-2-L2-smooth-0.25Hz.mp4` | 2 975/2 975 | 1 687 | 23 160 | 97.4 s | 8736063b9577973b |
| `A-3-L1-straight-pans.mp4` | 2 975/2 975 | 1 617 | 22 224 | 100.8 s | 4bdfa09fe4059970 |
| `A-4-L1-hold-and-eased-pans.mp4` | 2 975/2 975 | 768 | 10 569 | 99.1 s | daeaca4d350aac23 |
| `B-0-raw-s02.mp4` | 3 000/3 000, 0 fallback | 2 070 | 28 406 | 87.9 s | 79341f30e165ff3f |
| `B-1-L2-smooth-0.50Hz.mp4` | 3 000/3 000 | 2 126 | 29 007 | 97.9 s | 65086f7661e15640 |
| `B-2-L2-smooth-0.25Hz.mp4` | 3 000/3 000 | 1 997 | 27 199 | 98.4 s | b6a4b0e2b3d3d0a1 |
| `B-3-L1-straight-pans.mp4` | 3 000/3 000 | 2 133 | 29 044 | 101.8 s | 8f0e00415c57c33c |
| `B-4-L1-hold-and-eased-pans.mp4` | 3 000/3 000 | 1 212 | 16 491 | 100.2 s | e52f963f2f4799b1 |

Plus `A-compare-side-by-side.mp4` and `B-compare-side-by-side.mp4` (the five crops of the same
source frames next to each other at 720 px height, labelled; a viewing aid made with a separate
ffmpeg command, not through `render_clip`), and `paths-A.png`, `paths-B.png` (crop band and
ball positions over time for paths 1–4).

- **Render times** are with two renders running at once; the S-02 figure for one render alone
  was 12.9 s per 10 s of output.
- **The crop expression stays inside its limit.** Paths 1–3 change x in 54–71% of frames and
  give a 22–29 kB expression for 60 s (path 4: 26–40% and 11–16 kB), against
  `MAX_EXPRESSION_CHARS = 100_000`
  (`src/ai_reel_montage/shell/video.py:23`). By proportion the limit is reached at about 200 s
  of window (**extrapolation**).
- **Byte-identical re-render:** path 2 of window B was computed and rendered a second time in a
  fresh process. The crop x array was equal and the file had the same SHA-256
  (b6a4b0e2b3d3d0a1…) as the first render. One clip of ten was re-rendered.
- **Even-pixel steps.** The renderer takes an even integer x (`core/camera.py:115-116`), and
  1080/608 = 1.776, so one step is 3.55 output pixels. The smooth paths move slower than
  100 px/s — one 2 px step per frame — in 48–57% of frames; there the crop alternates still
  frames and 2 px steps instead of gliding. Rounding error is 0.55–0.57 px RMS; a 2 px
  back-and-forth within 0.1 s happens 3–6 times per window. **Whether this is visible as
  judder on a slow pan was not judged** — it is something to look for in the calm stretches
  (window A, 49–60 s) and, if it is, it is a property of the render route and not of the
  smoother.

### 12. The remaining stage-2 points

- **Point 1 (scipy version) — closed in stage 2, made moot here.** `whittaker_henderson` needs
  scipy 1.18; finding 5 shows a 15-line banded solve gives the same numbers on scipy 1.15–1.18.
- **Point 8 (which numbers become assertions) — baseline measured, thresholds not set.**
  Finding 1 and finding 10 give the raw S-02 baseline and each candidate's figures. Three
  observations bound the choice. (a) Reversals per minute must be counted on the even-pixel
  path: on the float path of the L1 hold-and-ease candidate it reads 56–214 because a segment
  that should be still moves by 10⁻⁹ px in alternating directions, and 5–9 on the path that is
  rendered. (b) Peak and RMS acceleration separate smooth from raw by a factor of 10–30 and are
  safe to assert against the raw baseline, but they rank L1 below L2 by construction, so they
  cannot be chosen before the aesthetic decision. (c) Ball-in-crop is the one assertion that is
  independent of the aesthetic and it now has teeth (finding 7). Jerk-based dimensionless
  measures and SPARC from stage 1 were not computed.
- **Stage-1 point 6 (sources not read in full)** was not pursued; nothing above depends on it.

## Code References

- `src/ai_reel_montage/core/camera.py:86-94` — `ball_centre`: linear interpolation of the ball
  over positioned samples; the reference `check_follow` judges against, and it treats predicted
  samples as positions.
- `src/ai_reel_montage/core/camera.py:97-112` — `_fallback_flags`: a frame is tracked when it
  lies between two neighbouring positioned samples, predicted included (finding 3).
- `src/ai_reel_montage/core/camera.py:115-128` — `_even_round_up` and `crop_path`: the S-02 rule
  to replace; the even rounding and the clamp to 0..1312 that every candidate here reused.
- `src/ai_reel_montage/core/camera.py:136-148` — `check_follow`: raises on x beyond the right
  edge, counts tracked frames with the ball inside; every rendered path went through it.
- `src/ai_reel_montage/core/camera.py:151-160` — `crop_x_expression`: one term per change of x;
  22–29 kB for the smoothed 60 s paths.
- `src/ai_reel_montage/shell/tracking.py:90-108` — `read_ball_track`: keeps the track from the
  last positioned sample at or before the window to the first at or after it; the smoother needs
  more (finding 9).
- `src/ai_reel_montage/shell/video.py:23`, `:226-230` — the expression length limit and its check.
- `src/ai_reel_montage/cli.py:94-111` — `_follow`: the route track → path → `check_follow` →
  render that F4 requires to stay intact.
- `tests/integration/test_tracking.py:99` — `test_ball_is_inside_the_crop_over_the_whole_match`:
  fails for an unconstrained L2 path below 1.0 Hz (finding 7).
- `pyproject.toml:9` — `scipy>=1.14`; nothing found here requires raising it.

## Architecture Insights

Facts the plan can build on without rediscovering them:

- **The smoother fits the pure core as it is.** Arrays in (frame numbers, ball x with NaN),
  arrays out (one float centre per frame); the only scipy call needed for the L2 family is
  `scipy.linalg.solveh_banded`, a fixed-sequence factorisation. `BallTrack` carries no
  detected/predicted flag and, by finding 3, does not need one.
- **One mechanism covers four needs.** In the weighted banded solve, weight 0 is a frame between
  samples (finding 6), a sample without a ball (stage 2), and context beyond the window is just
  more rows (finding 9); a raised weight is the inclusion rule (finding 7).
- **Order of operations that held up:** smooth the unclamped ball track → enforce inclusion →
  clamp the centre to 304..1616 → round to even → `check_follow` → render. Clamping the target
  first was measured to be worse (finding 7).
- **The strength constant belongs in Hz**, with λ derived from it and from the grid (finding 5).
- **If an L1 route is chosen**, the LP is small (about 3 000–5 000 variables, 30–330 ms), fits
  `scipy.optimize.linprog`, and must name `method="highs-ds"`; the trend-filter form has
  non-unique optima (finding 8). It needs no dependency beyond scipy, as stage 2 concluded.
- **Not needed by any candidate:** `whittaker_henderson`, REML/GCV, `lsq_linear`,
  `make_smoothing_spline`, Savitzky–Golay, Butterworth, a Kalman/RTS smoother, cvxpy,
  statsmodels, filterpy, pybaselines. The convolution filters and the RTS smoother were not
  rendered: the first cannot bridge a run without a ball or take the inclusion weights, and
  stage 1 itself rates the second as equivalent in effect to the L2 smoother with two parameters
  instead of one.

## Historical Context (from prior changes)

- `context/archive/2026-11-21-ball-following-crop/research.md` (finding 3) — "predicted already
  means interpolated": 6 210 of 6 211 two-sided predicted runs are straight to 0.02 px.
  **Supported** on both windows here (second difference at most 0.02 px inside runs).
- Same document, finding 4 — a centred, clamped crop contains the ball at every positioned
  sample "by construction". **Supported, and now the reason S-03 needs an inclusion rule:** the
  moment the crop stops being centred, the property has to be enforced (finding 7).
- `context/archive/2026-11-21-ball-following-crop/follow-ups/review-fixes.md`, F4 — a smoothed
  path can overshoot at the touchline; keep `check_follow` on the route. **Supported with a
  number:** before clamping, the smoothed centre is outside the range in up to 8.5% of frames;
  after the clamp `check_follow`'s right-edge test passed for all ten rendered paths.
- `context/foundation/roadmap.md:174` — window 06:10–07:10 has "100% ball coverage".
  **Contradicted for `full_match_tracks.json`** (8 samples without a ball, 25 fallback frames);
  true of the separately tracked clip the report describes. Window 18:35–19:35: supported.
- `research/web-findings.md`, Q3 — interpolated samples "should be zero-weighted" as a matter of
  statistics, with the visible effect left to measurement. **Contradicted for this use:**
  zero-weighting moves the path away from the complete-data path and breaks the follow check
  (finding 3). The statistical argument concerns uncertainty estimates, which the camera does
  not use.
- `research/knowledge-base.md`, A5 — the `filtfilt` edge transient is "a non-issue at our window
  length". **Contradicted:** 33–53 px in the first and last second of window B (finding 9).
- `research/knowledge-base.md`, A7 — reproducibility of HiGHS across versions "unproven".
  **Now measured clean across scipy 1.15.3–1.18.1**, with the non-uniqueness caveat (finding 8).

## Related Research

- `context/changes/smooth-camera-path/research/web-findings.md` — stage 1, literature.
- `context/changes/smooth-camera-path/research/knowledge-base.md` — stage 2, library documentation.
- `context/archive/2026-11-21-ball-following-crop/research.md` — ball-track quality, render routes.
- `context/archive/2026-11-21-first-playable-clip/research.md` — machine and ffmpeg baseline.

## Open Questions

For the user — before or at the start of `/10x-plan`:

1. **Smooth or straight.** Watch `out/s03-research/A-compare-side-by-side.mp4` and
   `B-compare-side-by-side.mp4`, then the full-size clips of the two or three that survive.
   The choice is between paths 1–2 (L2), path 3 (L1 straight pans) and, if it appeals, path 4
   (hold and ease). Within L2 there is a second choice, 0.5 Hz or 0.25 Hz.
2. **The tracker switch in window A (finding 2).** Is a camera that swings to a false detection
   and back acceptable for v1, or should S-03 (or a slice before S-06) reject implausible
   jumps? Nothing was measured about how to detect them; that would be new research.
3. **Window A's first half-second has no ball.** Keep the window as named, or move its start to
   06:10.5 so that it is what the roadmap says it is?
4. **How far off-centre may the ball sit?** H = 280 (ball may come within 24 px of the crop
   edge) or something tighter such as 200, at about twice the acceleration (finding 7).

For the plan:

5. **How much context `read_ball_track` should keep** — finding 9 gives 3 s at 0.5 Hz and 5 s at
   0.25 Hz; the rule for a window that starts or ends inside a run without a ball needs a named
   test (window A is that case).
6. **What the fallback frames show.** In a run without a ball the banded smoother draws its own
   cubic bridge instead of S-02's chord. At 0.15 Hz the bridge was 505–808 px from the chord
   inside window A's first 25 frames; at the rendered strengths it stayed within 280 px. Not
   examined further — the evaluation windows were chosen to avoid this, and the long runs are a
   product question (stage 1, Q6).
7. **Which metric assertions to adopt**, once question 1 is answered (finding 12, point 8).
8. **Even-pixel stepping on slow pans** (finding 11) — only if it shows in the clips.
