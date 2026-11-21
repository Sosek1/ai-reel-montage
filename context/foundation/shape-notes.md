---
project: "AI Reel Montage"
context_type: greenfield
created: 2026-11-14
updated: 2026-11-21
checkpoint:
  current_phase: 8
  phases_completed: [1, 2, 3, 4, 5, 6, 7]
  gray_areas_resolved:
    - topic: "pain category"
      decision: "cost & friction of commissioning + lack of editing skill"
    - topic: "insight"
      decision: "market gap, not tech gap — lower leagues too cheap for agencies, too expensive for per-unit manual editing"
    - topic: "primary persona scope"
      decision: "system/pipeline — this repo is an engine consumed by a larger product; input is files + metadata, not a human UI"
    - topic: "access model"
      decision: "none — local tool/library; access to the engine equals access to the machine"
    - topic: "v1 montage scope"
      decision: "9:16 crop + hard cuts only; music, beat-sync, overlays and slow-motion cut from v1"
    - topic: "quality measurement"
      decision: "human review on a fixed evaluation set — would I post this: yes/no"
    - topic: "metadata contract"
      decision: "framing target required; action type, score and match context carried but unused in v1"
    - topic: "framing target definition"
      decision: "position of the play (action + ball) over time — not the target player's position"
    - topic: "framing data source"
      decision: "trust the upstream framing target; no detection in this repo"
    - topic: "part-one dependency"
      decision: "lifted 2026-11-21 — real tracking data arrived; see '## Source materials'"
    - topic: "window selection"
      decision: "manual — the user names timestamps; the engine does not pick moments"
    - topic: "contract narrowing"
      decision: "attractiveness score and action type removed — no producer exists in the delivered data"
    - topic: "clip selection"
      decision: "dropped from the engine — the caller supplies exactly the clips that go in"
    - topic: "clip ordering"
      decision: "chronological by match time; dramaturgical reordering deferred to v2"
    - topic: "crop subject"
      decision: "the play (action + ball), not the target player; guardrail rewritten accordingly"
    - topic: "output duration"
      decision: "follows the supplied material; no fixed target window"
  frs_drafted: 7
  quality_check_status: accepted
prd_frontmatter:
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

# Shape Notes — AI Reel Montage

## Scope of this repository

This repository implements **part two** of a two-part product: the montage engine.

- **Part one (out of scope here):** analyse a full match recording, detect and track players and ball, identify players by jersey. Not built here. **As of 2026-11-21 this exists and has produced real output** — see `## Source materials`.
- **Part two (this repo):** given a match recording, its tracking data, and timestamps naming the moments to use, produce a finished vertical reel.

Revised 2026-11-21: the original split assumed part one would hand over pre-cut clips. It hands over a full match plus dense tracking instead, so trimming to the named windows happens here. Trimming is not analysis — the vision work stays upstream.

## Vision & Problem Statement

Lower-league footballers run their own social media profiles and need marketing content — especially around transfer windows, when they have to show their skills and advertise themselves. Today the only route is commissioning a human editor, who charges several dozen euros or dollars for a single reel. The pain is twofold: the direct cost and friction of commissioning (finding an editor, negotiating, revision rounds), and the fact that the player cannot do it himself — he has no editing skill and no tool that produces an acceptable result for him.

The insight is a market gap rather than a technology gap. Lower leagues are too cheap a segment for media agencies to serve, and too expensive to serve with per-unit manual editing. Nobody has aimed at them. If a programme can take labelled clips and assemble a reel people actually want to watch, the economics of the segment change.

> Socrates asked: what would have to be true for automated montage to be the wrong problem? Answer: if the value of a reel lived in a human editor's creative choices rather than in a repeatable template, automation would produce generic noise. Resolution: the bet is that football reels follow a narrow, repeatable grammar — this bet is the core risk of the project and is tested by the montage quality work itself.

## User & Persona

**Primary persona: the system / pipeline.** This repository is an engine consumed by a larger product, not a human-facing application. Its caller supplies short clips and metadata; it returns a finished reel. There is no UI, no account, no human in the loop at this layer.

The **end beneficiary** (one layer up, outside this repo's surface) is a lower-league footballer running his own social profile, who wants reels around transfer windows without paying an editor per reel.

## Access Control

No authentication. The engine runs locally as a tool/library invoked by its caller (CLI, function call, or script). No user accounts, no roles, no sessions — access to the engine equals access to the machine it runs on. If the engine is later exposed as a network service, access control becomes a question for that layer, not for this one.

## Success Criteria

### Primary

- On a fixed evaluation set of short clip bundles, a human reviewer answers "would I post this on a profile?" with yes for the majority of generated reels. The judgement is subjective and deliberately so — at this stage no automatic metric stands in for watchability.

### Secondary

- The montage decisions (which clips, what order, where to crop) are driven by the agreed metadata format rather than hardcoded per bundle, so the same engine handles a new bundle without code changes.

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

Scope decision: music, beat-synced cuts, metadata overlays and slow-motion/zoom-punch were all considered and cut from v1 — see `## Non-Goals`. Beat-sync was cut because it inverts control over clip lengths and rebuilds the montage core rather than adding to it; slow-motion was cut because it depends on key-frame timestamps that part one does not yet produce.

## Functional Requirements

### Input contract

- FR-001: Caller can supply the match recording, its tracking data, and a list of timestamp windows naming the moments to use. The required content of the tracking data is the ball's position over time; player positions and identities are available and may inform the crop. Priority: must-have
  > Socrates (Phase 4.5): Counter-argument accepted — "four required fields is too much for v1". Only the framing target was kept required.
  > Correction (2026-11-21): the delivered data settled the rest by fact. The attractiveness score and action type were removed from the contract entirely — nothing produces them, and keeping fields no producer fills is wishful schema design. Match context exists in the tracking file's own metadata block and needs no separate field. The framing target turned out to be dense (16.67 fps effective), so the sparse-keypoint question is moot.
- FR-001a: Caller can name timestamp windows by match time, and the engine trims exactly those windows out of the recording. Priority: must-have
  > Added 2026-11-21. Nobody hands over pre-cut clips, so trimming moved in scope. Deliberately *not* paired with automatic moment-finding — see FR-003.
- FR-002: Engine can degrade gracefully when tracking data is missing or predicted rather than detected, applying a documented fallback rather than refusing the window; it rejects only when it cannot produce a reel at all. Priority: must-have
  > Socrates: Counter-argument accepted — "better to degrade than reject". Rationale: during a one-week prototype the metadata is hand-written, and strict validation means fighting the schema instead of watching reels. An engine that always returns something is more useful than one that is fussy.

### Ordering

- FR-003: ~~Engine selects which moments enter the reel.~~ **Still dropped, for a new reason.** The user names the timestamp windows by hand.
  > Socrates (Phase 4.5): Counter-argument accepted — "with 3–5 clips there is nothing to select", and selection belongs upstream.
  > Correction (2026-11-21): the original reasoning collapsed — nobody supplies a chosen pool, and there are 99 minutes to choose from. The decision survives on different grounds: picking moments automatically would mean scoring player involvement from the tracking data, which means first solving identity fragmentation, which is a second module. The user names timestamps instead. Automate this only once the camera path works.
- FR-004: Engine can order the clips chronologically by match time. Priority: must-have
  > Socrates: Counter-argument accepted — "chronological order is enough and more honest". A match reel read in order has a natural narrative, and reshuffling for drama falsifies how the match went. Dramaturgical reordering mainly pays off alongside a soundtrack and pacing, so it moves to v2.

### Framing and assembly

- FR-005: Engine can reframe each clip from 16:9 to 9:16 while keeping the play — the action and the ball — in frame. Priority: must-have
  > Socrates: Counter-argument accepted — "following the player frames worse than following the play". A viewer wants the action, not the person; a crop glued to the player away from the ball is four seconds of running through empty space. Consequence: the Phase 3 guardrail was rewritten from "the player never leaves frame" to "the play never leaves frame", and the target player may sit outside the crop when he is off the ball. This is a deliberate trade and the single most reversible decision in the set.
- FR-006: Engine can join the reframed clips with hard cuts into one continuous video. Priority: must-have
  > Socrates: No counter-argument; hard cuts stand as written for v1.
- FR-007: Engine can write the result as a single vertical video file whose duration follows the supplied material rather than a fixed target window. Priority: must-have
  > Socrates: Counter-argument accepted — "duration should follow the material, not a rule". Three strong four-second clips make a better twelve-second reel than one padded to twenty. A fixed 20–40 s window would force padding with weak material.

## User Stories

### US-01: Engine turns a labelled clip bundle into a vertical reel

- **Given** a match recording, its tracking data, and 3–5 named timestamp windows
- **When** the caller invokes the montage engine on them
- **Then** a single vertical video file is written, containing every named window trimmed out, reframed to 9:16, ordered by match time and joined with hard cuts

#### Acceptance Criteria

- The output is a single file in 9:16 throughout, with no letterboxing or pillarboxing
- Every named window appears in the output, trimmed to its boundaries, in chronological order by match time
- The play — the action and the ball — is in frame for the whole of every clip
- Re-running on the same bundle produces the same output
- A window whose ball track is partly predicted rather than detected still yields a reel, built on the documented fallback, not an error

## Business Logic

**From the per-clip framing targets, the product computes a continuous vertical camera path and a matching zoom level over time — wide while the play builds, tight at the decisive moment — such that the action always fits the 9:16 frame and the movement reads as deliberate camera work rather than a shaky follow.**

The rule consumes one input the caller supplies: where the action sits in each clip over time. Its output is the reel itself — a vertical video in which the viewer never has to look for the ball and never notices the reframing. The user encounters the rule only through the finished reel; there is no setting, no preview, no knob to turn.

Two variables, not one: the path (where the frame sits) and the zoom (how wide it is). The zoom is what distinguishes this from a mechanical crop-follow — it is the part that imitates an editor's judgement about when to breathe and when to tighten.

After the Phase 4.5 revisions this is the **only** decision the engine makes. Moment selection belongs to the user, trimming is mechanical and ordering is chronological, so the entire value of v1 sits in this rule. That concentration is a risk worth naming: if the camera path is mediocre, nothing else in the pipeline can compensate.

Correction (2026-11-21): the rule now has a measured input rather than an assumed one. It consumes a ball track that is 95.2% covered but only 73.9% directly detected — so roughly a quarter of the path is built on predictions. Whether the rule can tell the difference, and whether it should, is Open Question 5.

## Non-Functional Requirements

- The output file plays on the mainstream short-form platforms without the user re-encoding or re-exporting it.
- A single unreadable input clip yields a reel assembled from the remaining clips plus a message naming the clip that failed — never an empty result.
- The same bundle submitted twice yields byte-identical output.
- A reel is produced in minutes, not hours, on commodity consumer hardware.

## Non-Goals

- **No video analysis: no detection, no tracking, no player identification.** All of it belongs to part one and all of it is already done. This is the load-bearing non-goal — it is what keeps the project to one week instead of one quarter.
  Narrowed 2026-11-21: the non-goal originally also covered "no match cutting". It no longer can, because what arrives is a full match rather than clips. Trimming named windows out of a recording stays in scope; *finding* those windows does not.
- **No automatic moment-finding.** The engine does not decide which parts of a match are worth showing. The user names timestamps. Scoring player involvement would require resolving identity fragmentation across 186 tracked entities — a second module, not a feature.
- **No soundtrack and no beat-synced cutting.** No music, no beat detection, no fitting clip lengths to a rhythm grid. Cut deliberately in Phase 3 because beat-sync inverts control over clip lengths and rebuilds the montage core rather than adding to it.
- **No on-screen text or graphics.** Player name, minute and score travel in the metadata but nothing is rendered from them. The fields exist so the contract does not have to change when overlays land.

## Forward: tech-stack

Not part of the PRD — captured for the stack-selection step that runs after `/10x-prd`.

- The engine must run locally on commodity consumer hardware with no paid API and no GPU requirement (stated as a Phase 3 guardrail; it reads as a runtime constraint, so it belongs here rather than in NFRs).
- Both AI models and deterministic video tooling are acceptable means. No preference was expressed, and none should be assumed.
- Render speed target: a reel in minutes, not hours, so the change-and-watch loop stays usable.

## Source materials

Delivered 2026-11-21 in `transfer-01a1f923/` (3 GB, git-ignored — inputs, not artifacts).

| File | What it is |
|---|---|
| `...[RQ_gduINxnw].mp4` | Full match, 99.16 min, 50 fps, 1920x1080 |
| `full_match_tracks.json` | 398 MB of per-frame tracking |
| `match_tracking_report.md` | Human-readable summary of the tracking run |
| 4 x `..._tracked_frame_*.jpg` | Annotated frames — visual proof of tracking |

Tracking quality as reported: ball tracked in **95.2%** of frames (73.9% directly detected, the rest filled by a Viterbi solver), 186 persistent entities merged from 9,645 raw tracklets, 60 jersey OCR reads mapped against the squad lists. Processed at stride 3 over 50 fps source, so the effective sampling rate is **16.67 fps**.

Per-frame shape:

```json
"frames": [{ "ball": {"x": 893.39, "y": 371.81, "bbox": null,
                      "confidence": null, "source": "predicted"},
             "players": [{"player_id": "TEAM_1_#23", "team": "team_1",
                          "jersey_number": "23", "bbox": [...],
                          "center_xy": [1215.5, 454.38], "foot_xy": [...],
                          "player_name": "Rafał Wolszczyński"}] }]
```

**The Phase 4.5 blocker is lifted.** Shape-notes previously recorded that v1 could not start or be evaluated until part one delivered framing-target data. It has. The schedule is no longer serial.

### Known data-quality issues

These are not blockers but they shape the research step, and none of them is visible from the report's headline numbers:

- **Identity fragmentation.** One player appears under several persistent IDs — `TEAM_0_#21`, `TEAM_0_#21_07` and `TEAM_0_#21_43` are all Patryk Bednarczyk. 186 entities cover roughly 30 players. Selecting "our player" is not a single filter.
- **Jersey OCR produces numbers absent from both squads** (#29, #92, #47, #31, #27 among them), so a jersey read is evidence, not identity.
- **Roughly 26% of ball positions are predicted rather than detected** (`"source": "predicted"`). For a camera path this may be the difference between a smooth move and a drift, and it is worth measuring before trusting the track blindly.

## Quality cross-check

Run in Phase 7. All six greenfield elements present: Access Control, Business Logic (one-sentence rule), project artifacts, timeline-cost acknowledgement (1 week, under the three-week threshold), Non-Goals (three entries), preserved behavior n/a for greenfield. Status: `accepted`.

One contract-level inconsistency was surfaced during the check and resolved on the spot rather than deferred — see Open Question 2.

## Open Questions

1. ~~**Does the crop trust the upstream framing target, or detect the action itself?**~~ **Resolved by delivery (2026-11-21):** it trusts the upstream track. Part one produces ball positions for 95.2% of frames; there is nothing to re-derive.
2. ~~**What exactly is the framing target?**~~ **Resolved in Phase 7:** the position of the play. The delivered data confirms this is what exists — a per-frame ball position, with player positions alongside it.
3. ~~**How dense does the framing target have to be?**~~ **Resolved by delivery:** dense, at 16.67 fps effective. The sparse-keypoint question does not arise.
4. ~~**Does the attractiveness score stay in the contract?**~~ **Resolved: removed.** Nothing produces it.
5. **How much does the 26% of predicted (rather than detected) ball positions hurt the camera path?** — Unknown and directly load-bearing: the whole domain rule consumes this track. Measure before designing around it. Owner: `/10x-research`. Block: no, but it may change the smoothing approach.
6. **How is "our player" resolved across fragmented identities?** — One player spans several persistent IDs, and jersey OCR returns numbers absent from both squads. Not needed for v1 (the user names timestamps) but it is the gate on ever automating moment-finding. Owner: `/10x-research`, or part one's owner.
7. **Is slow-motion / zoom-punch a deferred feature or a non-goal?** — Cut from v1 scope in Phase 3, deliberately not declared a non-goal in Phase 6. First candidate for v2. Owner: user.
8. **How does the camera-path rule survive a 100x scale increase?** — Per-frame path computation stops being free at scale; it would have to run on sparser samples or consume pre-computed paths. Not a v1 blocker, but it constrains the shape of the rule. Owner: user.
