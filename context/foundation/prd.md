---
project: "AI Reel Montage"
version: 1
status: draft
created: 2026-11-21
context_type: greenfield
product_type: cli
target_scale:
  users: small
  qps: low
  data_volume: medium
timeline_budget:
  mvp_weeks: 1
  hard_deadline: null
  after_hours_only: true
---

# PRD — AI Reel Montage

## Vision & Problem Statement

Lower-league footballers run their own social media profiles and need marketing content — especially around transfer windows, when they have to show their skills and advertise themselves. Today the only route is commissioning a human editor, who charges several dozen euros or dollars for a single reel. The pain is twofold: the direct cost and friction of commissioning (finding an editor, negotiating, revision rounds), and the fact that the player cannot do it himself — he has no editing skill and no tool that produces an acceptable result for him.

The insight is a market gap rather than a technology gap. Lower leagues are too cheap a segment for media agencies to serve, and too expensive to serve with per-unit manual editing. Nobody has aimed at them. If a programme can take a match recording, its tracking data and a few named moments and assemble a reel people actually want to watch, the economics of the segment change.

> Socratic: what would have to be true for automated montage to be the wrong problem? Answer: if the value of a reel lived in a human editor's creative choices rather than in a repeatable template, automation would produce generic noise. Resolution: the bet is that football reels follow a narrow, repeatable grammar — this bet is the core risk of the project and is tested by the montage quality work itself.

Scope note: this repository implements **part two** of a two-part product — the montage engine. Part one (analysing a full match recording, detecting and tracking players and ball, identifying players by jersey) is out of scope here. Revised 2026-11-21: part one now exists and has produced real output. The original split assumed it would hand over pre-cut clips; it hands over a full match plus dense tracking instead, so trimming to the named windows happens here. Trimming is not analysis — the vision work stays upstream.

## User & Persona

**Primary persona: the system / pipeline.** This repository is an engine consumed by a larger product, invoked as a command-line tool, not a human-facing application. Its caller supplies a match recording, tracking data and timestamp windows; it returns a finished reel. There is no UI, no account, no human in the loop at this layer.

The **end beneficiary** (one layer up, outside this repo's surface) is a lower-league footballer running his own social profile, who wants reels around transfer windows without paying an editor per reel.

## Success Criteria

### Primary

- On a fixed evaluation set of reels generated from named timestamp windows, a human reviewer answers "would I post this on a profile?" with yes for the majority of generated reels. The judgement is subjective and deliberately so — at this stage no automatic metric stands in for watchability.

### Secondary

- The montage decisions (where the frame sits, how wide it is, in what order windows appear) are driven by the supplied tracking data and timestamp windows rather than hardcoded per recording, so the same engine handles a new recording and new windows without code changes.

### Guardrails

- The play never leaves frame. Cropping 16:9 to 9:16 discards roughly 56% of the width; a reel where the crop loses the action and the ball is worthless regardless of everything else. (Rewritten in Phase 4.5: this guardrail originally read "the target player never leaves frame" — see FR-005 for why it now tracks the play instead.)
- Deterministic output: the same inputs produce the same reel. Without this there is no way to tell whether an engine change improved or degraded the montage.
- Render time stays in minutes, not hours, so the change-and-watch loop remains usable during prototyping.

### MVP flow (locked)

1. Caller supplies the match recording, its tracking data, and 3–5 timestamp windows naming the moments to use.
2. Engine trims each named window out of the recording.
3. Engine orders the windows chronologically by match time.
4. Engine crops each one from 16:9 to 9:16, following the play.
5. Engine concatenates them with hard cuts.
6. Engine writes one vertical file whose length follows the material.

(Steps 3, 4 and 6 were rewritten in Phase 4.5; steps 1 and 2 in the 2026-11-21 correction, once it turned out that nobody hands over pre-cut clips.)

Scope decision: music, beat-synced cuts, metadata overlays and slow-motion/zoom-punch were all considered and cut from v1 — see `## Non-Goals`. Beat-sync was cut because it inverts control over clip lengths and rebuilds the montage core rather than adding to it; slow-motion was cut because it depends on key-frame timestamps that part one does not produce.

## User Stories

### US-01: Engine turns a recording and named windows into a vertical reel

- **Given** a match recording, its tracking data, and 3–5 named timestamp windows
- **When** the caller invokes the montage engine on them
- **Then** a single vertical video file is written, containing every named window trimmed out, reframed to 9:16, ordered by match time and joined with hard cuts

#### Acceptance Criteria

- The output is a single file in 9:16 throughout, with no letterboxing or pillarboxing
- Every named window appears in the output, trimmed to its boundaries, in chronological order by match time
- The play — the action and the ball — is in frame for the whole of every clip
- Re-running on the same inputs produces the same output
- A window whose ball track is partly predicted rather than detected still yields a reel, built on the documented fallback, not an error

## Functional Requirements

### Input contract

- FR-001: Caller can supply the match recording, its tracking data, and a list of timestamp windows naming the moments to use. The required content of the tracking data is the ball's position over time; player positions and identities are available and may inform the crop. Priority: must-have
  > Socratic (Phase 4.5): Counter-argument accepted — "four required fields is too much for v1". Only the framing target was kept required.
  > Correction (2026-11-21): the delivered data settled the rest by fact. The attractiveness score and action type were removed from the contract entirely — nothing produces them, and keeping fields no producer fills is wishful schema design. Match context exists in the tracking file's own metadata block and needs no separate field. The framing target turned out to be dense (16.67 fps effective), so the sparse-keypoint question is moot.
- FR-001a: Caller can name timestamp windows by match time, and the engine trims exactly those windows out of the recording. Priority: must-have
  > Socratic (added 2026-11-21): nobody hands over pre-cut clips, so trimming moved in scope. Deliberately *not* paired with automatic moment-finding — see FR-003.
- FR-002: Engine can degrade gracefully when tracking data is missing or predicted rather than detected, applying a documented fallback rather than refusing the window; it rejects only when it cannot produce a reel at all. Priority: must-have
  > Socratic: Counter-argument accepted — "better to degrade than reject". Rationale: during a one-week prototype the input data is hand-prepared, and strict validation means fighting the schema instead of watching reels. An engine that always returns something is more useful than one that is fussy.

### Ordering

- FR-003: ~~Engine selects which moments enter the reel.~~ **Still dropped, for a new reason.** The user names the timestamp windows by hand.
  > Socratic (Phase 4.5): Counter-argument accepted — "with 3–5 clips there is nothing to select", and selection belongs upstream.
  > Correction (2026-11-21): the original reasoning collapsed — nobody supplies a chosen pool, and there are 99 minutes to choose from. The decision survives on different grounds: picking moments automatically would mean scoring player involvement from the tracking data, which means first solving identity fragmentation, which is a second module. The user names timestamps instead. Automate this only once the camera path works.
- FR-004: Engine can order the clips chronologically by match time. Priority: must-have
  > Socratic: Counter-argument accepted — "chronological order is enough and more honest". A match reel read in order has a natural narrative, and reshuffling for drama falsifies how the match went. Dramaturgical reordering mainly pays off alongside a soundtrack and pacing, so it moves to v2.

### Framing and assembly

- FR-005: Engine can reframe each clip from 16:9 to 9:16 while keeping the play — the action and the ball — in frame. Priority: must-have
  > Socratic: Counter-argument accepted — "following the player frames worse than following the play". A viewer wants the action, not the person; a crop glued to the player away from the ball is four seconds of running through empty space. Consequence: the Phase 3 guardrail was rewritten from "the player never leaves frame" to "the play never leaves frame", and the target player may sit outside the crop when he is off the ball. This is a deliberate trade and the single most reversible decision in the set.
- FR-006: Engine can join the reframed clips with hard cuts into one continuous video. Priority: must-have
  > Socratic: No counter-argument; hard cuts stand as written for v1.
- FR-007: Engine can write the result as a single vertical video file whose duration follows the supplied material rather than a fixed target window. Priority: must-have
  > Socratic: Counter-argument accepted — "duration should follow the material, not a rule". Three strong four-second clips make a better twelve-second reel than one padded to twenty. A fixed 20–40 s window would force padding with weak material.

## Non-Functional Requirements

- The output file plays on the mainstream short-form platforms without the user re-encoding or re-exporting it.
- A single unreadable input window yields a reel assembled from the remaining windows plus a message naming the window that failed — never an empty result.
- The same inputs submitted twice yield byte-identical output.
- A reel is produced in minutes, not hours, on commodity consumer hardware.

## Business Logic

**From the ball's position over time, the product computes a continuous vertical camera path and a matching zoom level over time — wide while the play builds, tight at the decisive moment — such that the action always fits the 9:16 frame and the movement reads as deliberate camera work rather than a shaky follow.**

The rule consumes one input the caller supplies: where the action sits in each clip over time. Its output is the reel itself — a vertical video in which the viewer never has to look for the ball and never notices the reframing. The user encounters the rule only through the finished reel; there is no setting, no preview, no knob to turn.

Two variables, not one: the path (where the frame sits) and the zoom (how wide it is). The zoom is what distinguishes this from a mechanical crop-follow — it is the part that imitates an editor's judgement about when to breathe and when to tighten.

After the Phase 4.5 revisions this is the **only** decision the engine makes. Moment selection belongs to the user, trimming is mechanical and ordering is chronological, so the entire value of v1 sits in this rule. That concentration is a risk worth naming: if the camera path is mediocre, nothing else in the pipeline can compensate.

Correction (2026-11-21): the rule now has a measured input rather than an assumed one. It consumes a ball track that is 95.2% covered but only 73.9% directly detected — so roughly a quarter of the path is built on predictions. Whether the rule can tell the difference, and whether it should, is Open Question 5.

## Access Control

No authentication. The engine runs locally as a tool invoked by its caller (command line, function call, or script). No user accounts, no roles, no sessions — access to the engine equals access to the machine it runs on. If the engine is later exposed as a network service, access control becomes a question for that layer, not for this one.

## Non-Goals

- **No video analysis: no detection, no tracking, no player identification.** All of it belongs to part one and all of it is already done. This is the load-bearing non-goal — it is what keeps the project to one week instead of one quarter. Narrowed 2026-11-21: the non-goal originally also covered "no match cutting". It no longer can, because what arrives is a full match rather than clips. Trimming named windows out of a recording stays in scope; *finding* those windows does not.
- **No automatic moment-finding.** The engine does not decide which parts of a match are worth showing. The user names timestamps. Scoring player involvement would require resolving identity fragmentation across 186 tracked entities — a second module, not a feature.
- **No soundtrack and no beat-synced cutting.** No music, no beat detection, no fitting clip lengths to a rhythm grid. Cut deliberately in Phase 3 because beat-sync inverts control over clip lengths and rebuilds the montage core rather than adding to it.
- **No on-screen text or graphics.** Player name, minute and score exist in the tracking data but nothing is rendered from them. Overlays are deferred beyond v1.

## Open Questions

1. ~~**Does the crop trust the upstream framing target, or detect the action itself?**~~ **Resolved by delivery (2026-11-21):** it trusts the upstream track. Part one produces ball positions for 95.2% of frames; there is nothing to re-derive.
2. ~~**What exactly is the framing target?**~~ **Resolved in Phase 7:** the position of the play. The delivered data confirms this is what exists — a per-frame ball position, with player positions alongside it.
3. ~~**How dense does the framing target have to be?**~~ **Resolved by delivery:** dense, at 16.67 fps effective. The sparse-keypoint question does not arise.
4. ~~**Does the attractiveness score stay in the contract?**~~ **Resolved: removed.** Nothing produces it.
5. **How much does the 26% of predicted (rather than detected) ball positions hurt the camera path?** — Unknown and directly load-bearing: the whole domain rule consumes this track. Measure before designing around it. Owner: `/10x-research`. Block: no, but it may change the smoothing approach.
6. **How is "our player" resolved across fragmented identities?** — One player spans several persistent IDs, and jersey OCR returns numbers absent from both squads. Not needed for v1 (the user names timestamps) but it is the gate on ever automating moment-finding. Owner: `/10x-research`, or part one's owner.
7. **Is slow-motion / zoom-punch a deferred feature or a non-goal?** — Cut from v1 scope in Phase 3, deliberately not declared a non-goal in Phase 6. First candidate for v2. Owner: user.
8. **How does the camera-path rule survive a 100x scale increase?** — Per-frame path computation stops being free at scale; it would have to run on sparser samples or consume pre-computed paths. Not a v1 blocker, but it constrains the shape of the rule. Owner: user.
