---
project: "AI Reel Montage"
version: 1
status: draft
created: 2026-11-21
updated: 2026-11-21
prd_version: 1
main_goal: speed
top_blocker: decisions
milestone_id: first-watchable-reel
milestone_seq: 1
milestone_status: open
---

# Roadmap: AI Reel Montage

> Derived from `context/foundation/prd.md` (v1), `tech-stack.md`, the `## Source materials` and `## Open Questions` of `shape-notes.md`, and the repository baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Milestone

**M-1: First watchable reel** — Status: open

- **Intent:** Produce one finished vertical reel from the real 99-minute match and the user's named timestamp windows, good enough for a human to judge "would I post this?". The milestone proves the camera path, not feature breadth.
- **Source materials:** `context/foundation/prd.md` (v1)
- **Done when:** every F-NN and S-NN below is `done`.
- **Scope anchors:** FR-001, FR-001a, FR-002, FR-004, FR-005, FR-006, FR-007, US-01 (all PRD must-haves; the PRD has exactly one user story).

## Vision recap

Lower-league footballers need reels for their own profiles, especially around transfer windows, and today pay a human editor several dozen euros per reel. This repository is the montage engine: given a match recording, its tracking data and 3–5 named timestamp windows, it trims, reframes 16:9 to 9:16 following the play, joins with hard cuts and writes one vertical file. Almost all of the value sits in one numeric rule — from the ball's position over time, compute a continuous camera path and a time-varying zoom so the action always fits the frame — and everything else in the pipeline is plumbing.

## North star

**S-02: Ball-following crop** — the first slice where a reel is reframed by the real tracking data instead of a fixed crop, so it is the earliest point at which the core hypothesis (a data-driven crop keeps the play in frame) can be seen on real footage.

> "North star" here means the smallest end-to-end slice whose delivery would prove the core product hypothesis — placed as early as its prerequisites allow, because the rest only matters if this works. S-01 comes first only because it is the cheapest proof that video can be cut and rendered at all, and it carries the decode-cost risk.

## At a glance

| ID   | Change ID                  | Outcome (user can …)                                                              | Prerequisites                                  | PRD refs                   | Status   |
| ---- | -------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------- | -------------------------- | -------- |
| S-01 | first-playable-clip        | name one timestamp window and get a playable 9:16 clip trimmed from the match     | —                                              | FR-001a, US-01             | ready    |
| S-02 | ball-following-crop        | get a clip whose crop follows the ball from the tracking data                     | S-01                                           | FR-001, FR-002, FR-005, US-01 | proposed |
| S-03 | smooth-camera-path         | get a clip whose frame moves like deliberate camera work, not a jittery follow    | S-02, evaluation windows named by the user     | FR-002, FR-005, US-01      | proposed |
| S-04 | adaptive-zoom              | get a clip that is wide while play builds and tight at the decisive moment        | S-03                                           | FR-005, US-01              | proposed |
| S-05 | multi-window-reel          | name 3–5 windows and get one chronological, hard-cut reel, identical on re-runs   | S-02, evaluation windows named by the user     | FR-004, FR-006, FR-007, US-01 | proposed |
| S-06 | evaluation-set-verdict     | watch reels from the named evaluation windows and record a yes/no "would I post"  | S-04, S-05, evaluation windows named by the user | US-01                    | blocked  |

## Baseline

What's already in place in the repository as of 2026-11-21 (per `tech-stack.md` and the bootstrap verification).
There are no Foundations below; nothing in this baseline needs a cross-cutting enabler ahead of S-01.

- **Frontend:** absent by design — product is a CLI, no UI.
- **Backend / API:** partial — a command-line entry point and its unit test exist; no engine logic behind it. The package is already split into a pure `core` and an IO `shell`, both empty.
- **Data:** absent by design — no database. Inputs are the match recording and a large tracking file in a git-ignored delivery folder.
- **Auth:** absent by design — local tool, no access control (PRD `## Access Control`).
- **Deploy / infra:** absent — no CI workflows yet; self-host, run locally.
- **Observability:** absent — not required for v1.

Verified tooling: video tool installed with the H.264, AAC and crop/scale/concat support the pipeline needs. The source recording is AV1, 1920x1080, 50 fps, 99 minutes; only roughly 30 seconds of it is ever needed.

## Foundations

None. Every technical element is introduced inside the first slice that needs it (progressive disclosure): video trimming and encoding in S-01, tracking-file reading in S-02, camera maths in S-02–S-04, assembly in S-05.

## Slices

### S-01: First playable clip

- **Outcome:** user can name one timestamp window of the match and get a playable 9:16 clip trimmed from it, framed by a fixed centre crop.
- **Change ID:** first-playable-clip
- **PRD refs:** FR-001a, US-01
- **Prerequisites:** —
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - How long does trimming a ~10 s window take on the AV1 source when the cut is made before decoding rather than after? The reel must come out in minutes, so the trim has to bound decode work to the window — measure it here, on a bounded window, never over the whole recording. — Owner: TBD (answered by this slice's own timing). Block: no.
- **Risk:** Sequenced first because the whole pipeline rides on video being cut cheaply; software AV1 decoding is slow, and discovering that after the camera maths is built would invalidate the render-time guardrail. Any timestamp works as a test window — no evaluation set is needed because nothing here is judged for watchability.
- **Status:** ready

### S-02: Ball-following crop

- **Outcome:** user can get a clip whose 9:16 crop follows the ball using the supplied tracking data.
- **Change ID:** ball-following-crop
- **PRD refs:** FR-001, FR-002, FR-005, US-01
- **Prerequisites:** S-01
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - Which documented fallback keeps the crop stable where the ball position is missing or predicted rather than detected (about 26% of positions)? — Owner: user. Block: no. (Starts as hold-last-known; refined by S-03 and by Open Roadmap Question 1.)
- **Risk:** The first contact between the tracking file and real footage: the tracking is sampled at 16.67 fps over a 50 fps source, so times have to be mapped between the two, and the file is 398 MB so only the needed window may be read. This is the earliest slice that can show whether the play stays in frame; it is verified automatically (ball inside the crop for every output frame), not by eye.
- **Status:** proposed

### S-03: Smooth camera path

- **Outcome:** user can get a clip whose frame moves like deliberate camera work — continuous, damped, free of jitter from noisy or predicted ball samples.
- **Change ID:** smooth-camera-path
- **PRD refs:** FR-002, FR-005, US-01
- **Prerequisites:** S-02, evaluation windows named by the user
- **Parallel with:** S-05
- **Blockers:** —
- **Unknowns:**
  - How much does the predicted share of the ball track hurt the path, and does the smoothing need to treat predicted samples differently from detected ones? — Owner: `/10x-research`. Block: no. (Open Roadmap Question 1; run it before `/10x-plan` on this slice because it may change the smoothing approach.)
- **Risk:** This is where the product's value is made or lost, and it is the heaviest slice by design. It is built test-first as a pure computation (ball track in, path out, no files), but "reads as deliberate" can only be judged by watching rendered clips, hence the dependency on the user's named windows.
- **Status:** proposed

### S-04: Adaptive zoom

- **Outcome:** user can get a clip whose zoom is wide while the play builds and tight at the decisive moment, always keeping the action in frame.
- **Change ID:** adaptive-zoom
- **PRD refs:** FR-005, US-01
- **Prerequisites:** S-03
- **Parallel with:** S-05
- **Blockers:** —
- **Unknowns:**
  - What signal tells "the play is building" from "the decisive moment" using only ball and player positions already in the tracking data? — Owner: user. Block: no. (Player positions may inform the zoom per FR-001; picking players by identity is not needed and is out of scope — Open Roadmap Question 2.)
- **Risk:** The second half of the core rule and the part that separates this from a mechanical crop-follow. Sequenced after the path so zoom changes are judged on an already-stable camera; it moves the same pure computation, so it stays in the same area of the code and is not parallel with S-03.
- **Status:** proposed

### S-05: Multi-window reel

- **Outcome:** user can name 3–5 windows and get one chronological, hard-cut vertical reel that is byte-identical on re-runs and survives one unreadable window.
- **Change ID:** multi-window-reel
- **PRD refs:** FR-004, FR-006, FR-007, US-01
- **Prerequisites:** S-02, evaluation windows named by the user
- **Parallel with:** S-03, S-04
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Mostly plumbing, so deliberately small; sequenced against S-02 rather than the finished camera so the assembly, determinism and render-time guardrails are proven early on whatever path the engine currently has, and S-03/S-04 improve the clips inside it without touching assembly. A window that fails yields a reel from the remaining windows plus a message naming it, never an empty result.
- **Status:** proposed

### S-06: Evaluation-set verdict

- **Outcome:** user can watch the reels generated from the named evaluation windows and record a yes/no "would I post this?" for each.
- **Change ID:** evaluation-set-verdict
- **PRD refs:** US-01
- **Prerequisites:** S-04, S-05, evaluation windows named by the user
- **Parallel with:** —
- **Blockers:** The user has not yet named the 3–5 timestamp windows from the match.
- **Unknowns:**
  - Which 3–5 windows of the 99-minute match form the evaluation set? — Owner: user. Block: yes.
- **Risk:** This is the product's only success measure and it is a human judgement, so it needs a fixed set named in advance or the verdict is not comparable between engine changes. It closes the milestone; if the majority of reels are judged "no", the finding goes back into the roadmap as an amendment, not into this slice.
- **Status:** blocked

## Backlog Handoff

| Roadmap ID | Change ID              | Suggested issue title                                   | Ready for `/10x-plan` | Notes                                                           |
| ---------- | ---------------------- | ------------------------------------------------------- | --------------------- | --------------------------------------------------------------- |
| S-01       | first-playable-clip    | Trim a named window into a playable 9:16 clip           | yes                   | Run `/10x-new first-playable-clip`                              |
| S-02       | ball-following-crop    | Crop follows the ball from tracking data                | no                    | Waits for S-01                                                  |
| S-03       | smooth-camera-path     | Smooth, damped camera path from the ball track          | no                    | Waits for S-02 and the evaluation windows; research OQ 1 first  |
| S-04       | adaptive-zoom          | Time-varying zoom: wide while building, tight at decisive moment | no           | Waits for S-03                                                  |
| S-05       | multi-window-reel      | Chronological hard-cut reel from 3–5 windows            | no                    | Waits for S-02 and the evaluation windows                       |
| S-06       | evaluation-set-verdict | Human verdict on reels from the evaluation windows      | no                    | Blocked on the user naming the windows                          |

## Open Roadmap Questions

1. **How much does the 26% of predicted (rather than detected) ball positions hurt the camera path?** — Owner: `/10x-research`. Block: none; informs S-03's smoothing approach. Research, not a slice.
2. **How is "our player" resolved across fragmented identities?** — Owner: `/10x-research`, or part one's owner. Block: none for v1; it is the gate on ever automating moment-finding. Research, not a slice.
3. **Is slow-motion / zoom-punch a deferred feature or a non-goal?** — Owner: user. Block: none; first candidate for v2.
4. **How does the camera-path rule survive a 100x scale increase?** — Owner: user. Block: none; constrains the shape of the rule, not v1.
5. **Which 3–5 timestamp windows form the evaluation set?** — Owner: user. Block: S-03 and S-05 (to judge their output), S-06 (hard). Name them before S-03 is planned, since every rendered judgement from S-03 on needs them.

## Parked

- **Video analysis (detection, tracking, player identification)** — Why parked: PRD §Non-Goals; belongs to part one and is done.
- **Automatic moment-finding** — Why parked: PRD §Non-Goals; needs identity resolution across fragmented tracking IDs, a second module.
- **Soundtrack and beat-synced cutting** — Why parked: PRD §Non-Goals; inverts control over clip lengths.
- **On-screen text and graphics** — Why parked: PRD §Non-Goals; overlays deferred beyond v1.
- **Slow-motion / zoom-punch** — Why parked: cut from v1; v2 candidate (Open Roadmap Question 3).
- **Dramaturgical reordering of clips** — Why parked: FR-004 keeps chronological order; reordering pays off only alongside a soundtrack.

## Milestone History

## Done
