---
change_id: ball-following-crop
title: Ball-following crop
status: plan_reviewed
created: 2026-11-21
updated: 2026-11-21
archived_at: null
---

## Notes

- **Outcome:** the user can get a clip whose 9:16 crop follows the ball, using the supplied tracking data, instead of the fixed centre crop from S-01.
- **Roadmap ref:** S-02 (`context/foundation/roadmap.md`), milestone `first-watchable-reel` (M-1).
- **PRD refs:** FR-001, FR-002, FR-005, US-01.
- **Prerequisites:** S-01 (`first-playable-clip`, done and archived in `context/archive/2026-11-21-first-playable-clip/`). **Roadmap slice status:** `ready`.
- **Why this slice is next:** the roadmap names it the milestone's "north star" — the smallest end-to-end slice whose delivery proves the core product hypothesis, that a data-driven crop keeps the action in frame. It is the earliest point at which that can be seen on real footage. S-01 came first only as the cheapest proof that video can be cut and rendered at all.
- **Open unknown (owner: user, does not block):** which documented fallback keeps the crop stable where the ball position is missing or predicted rather than detected (about 26% of positions). The starting point is "hold last known position". It is refined later by S-03 and by Open Roadmap Question 1.
- **Risk:** this is the first contact between the tracking file and real footage.
  - Tracking is sampled at 16.67 fps over a 50 fps source, so times have to be mapped between the two grids.
  - The tracking file (`full_match_tracks.json`) is 398 MB, so only the needed window may be read, streamed (ijson), never the whole file into memory.
- **Verification:** automatic, not by eye — the ball is inside the crop for every output frame of the window. Output must stay byte-identical on re-runs (product NFR).
- **Evaluation set:** not needed. The named evaluation windows are a prerequisite of S-03, S-05 and S-06, not of this slice; any window works for testing.
- **Out of scope (belongs to later slices):** smoothing and damping of the camera path (S-03), adaptive zoom (S-04), multi-window assembly (S-05), the watchability verdict (S-06).
