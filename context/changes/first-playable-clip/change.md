---
change_id: first-playable-clip
title: First playable clip
status: impl_reviewed
created: 2026-11-21
updated: 2026-11-21
archived_at: null
---

## Notes

- **Outcome:** the user names one timestamp window of the match and gets a playable 9:16 clip trimmed from it, framed by a fixed centre crop.
- **Roadmap ref:** S-01 (`context/foundation/roadmap.md`), milestone `first-watchable-reel` (M-1).
- **PRD refs:** FR-001a, US-01.
- **Prerequisites:** none. **Roadmap slice status:** `ready`.
- **Open unknown (answered by this slice's own timing measurement, not by a question to the user):** how long does trimming a ~10 s window take on the AV1 source when the cut is made before decoding rather than after? The reel must come out in minutes, so the trim has to bound decode work to the window. Measure on a bounded window only, never over the whole recording.
- **Why first:** the whole pipeline depends on video being cut cheaply; software AV1 decoding is slow, and discovering that after the camera maths is built would invalidate the render-time guardrail.
- **Evaluation set:** not needed. Nothing in S-01 is judged for watchability, so any timestamp works as a test window.
