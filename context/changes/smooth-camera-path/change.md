---
change_id: smooth-camera-path
title: Smooth camera path
status: preparing
created: 2026-11-25
updated: 2026-11-25
archived_at: null
---

## Notes

- **Outcome:** the user can get a clip whose frame moves like deliberate camera work — continuous, damped, free of jitter from noisy or predicted ball samples.
- **Roadmap ref:** S-03 (`context/foundation/roadmap.md`), milestone `first-watchable-reel` (M-1).
- **PRD refs:** FR-002, FR-005, US-01.
- **Prerequisites:** S-02 (`ball-following-crop`, done and archived in `context/archive/2026-11-21-ball-following-crop/`) and the named evaluation windows (see below, resolved 2026-11-25). **Roadmap slice status:** `ready`.
- **Parallel with:** S-05.
- **Problem this solves:** S-02's `crop_path` implements the "piecewise-linear follow" rule: the crop goes straight to the ball, interpolated linearly between tracking samples, and crosses runs without a ball in a straight line. It is deliberately raw, with no damping, and was built to be replaced. The user watched the S-02 clip and confirmed that the ball is in frame throughout, but the picture jitters. This slice replaces that function with a smoothed path.
- **What it replaces:** `core/camera.py::crop_path` (the S-02 rule). Surrounding pieces (`BallTrack`, `CropPath`, `check_follow`, `crop_x_expression`, `shell/tracking.py`, `shell/video.py`) exist already; this change names the problem and its limits, not the solution.
- **Open unknown (owner: `/10x-research`, does not block):** how much does the predicted share of the ball track hurt the camera path, and does smoothing need to treat predicted samples differently from detected ones? This is Open Roadmap Question 1. The roadmap says to answer it **before `/10x-plan`** on this slice, because it may change the smoothing approach. Measured facts to start from: 99 157 samples every third source frame; 73.9% detected, 21.3% predicted (practically always a straight line between detections), 4.8% missing in 45 runs of 2.82 s to 25.74 s; the ball never leaves the frame; largest jump between neighbouring samples is 595 px.
- **Carried from the S-02 implementation review** (full text: `context/archive/2026-11-21-ball-following-crop/follow-ups/review-fixes.md`, F4):
  - Every crop path must go through `check_follow` before `render_clip`. The right-edge bound (`x <= source_width - crop_width`) is enforced by `check_follow` only; ffmpeg clamps an out-of-range x silently, and a smoothed path can overshoot at the touchline. The plan must keep that call on the route to the render and add a named test of the smoothed path at the right edge. If a second production caller of `render_clip` appears, consider making the bound part of `CropPath` (S-04 turns it into a per-frame bound).
  - Keep `test_ball_is_inside_the_crop_over_the_whole_match` as it is and run it against the smoothed function: once the crop is no longer centred by construction it is the assertion that can really fail.
- **Risk:** this is where the product's value is made or lost, and it is the heaviest slice by design. It is built test-first as pure computation (ball track in, path out, no files — pure core / IO shell rule). But "reads as deliberate camera work" can only be judged by watching rendered clips. Output must stay byte-identical on re-runs (product NFR).
- **Evaluation set:** needed, unlike S-01 and S-02. Windows 06:10–07:10 (source frames 18 500–21 500) and 18:35–19:35 (55 750–58 750), recorded in the roadmap's `## Evaluation set`. Both have 100% ball coverage, so what is judged is the smoothing and not the handling of missing data — that is why they were chosen. A window crossing a no-ball run (e.g. 6:02–6:12) may be added later and was left out on purpose so smoothing is not confounded with the fallback rule.
- **Out of scope (belongs to later slices):** adaptive zoom (S-04), multi-window assembly (S-05), the watchability verdict (S-06). No technique or architecture is proposed here; that is the job of research and plan.
- **Next step:** `/10x-research smooth-camera-path` (Fable). Per rule 6 in `CLAUDE.md` this slice asks "which technique", so it goes through the three-stage research (web search, documentation knowledge base, synthesis), not a measurement alone.
