---
project: "AI Reel Montage"
context_type: greenfield
created: 2026-11-14
updated: 2026-11-14
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
      decision: "accepted as a blocker — v1 starts when part one delivers; contract handed over now, marked v0"
    - topic: "clip selection"
      decision: "dropped from the engine — the caller supplies exactly the clips that go in"
    - topic: "clip ordering"
      decision: "chronological by match time; dramaturgical reordering deferred to v2"
    - topic: "crop subject"
      decision: "the play (action + ball), not the target player; guardrail rewritten accordingly"
    - topic: "output duration"
      decision: "follows the supplied material; no fixed target window"
  frs_drafted: 6
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

- **Part one (out of scope here):** upload a full match recording, analyse it, identify the target player, cut labelled fragments. Not built here — only simulated via an agreed metadata format.
- **Part two (this repo):** given several short clips plus per-clip metadata, produce a finished vertical reel.

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

1. Caller supplies 3–5 clips (a few seconds each) plus metadata describing each clip.
2. Engine orders them chronologically by match time.
3. Engine crops each clip from 16:9 to 9:16, following the play.
4. Engine concatenates them with hard cuts.
5. Engine writes one vertical file whose length follows the material.

(Steps 2, 3 and 5 were rewritten in Phase 4.5 — see the Socrates notes under the FRs.)

Scope decision: music, beat-synced cuts, metadata overlays and slow-motion/zoom-punch were all considered and cut from v1 — see `## Non-Goals`. Beat-sync was cut because it inverts control over clip lengths and rebuilds the montage core rather than adding to it; slow-motion was cut because it depends on key-frame timestamps that part one does not yet produce.

## Functional Requirements

### Input contract

- FR-001: Caller can supply a bundle of short clips, each accompanied by a metadata record whose only required field is a per-clip framing target — the position of the play (the action and the ball) within the frame over time. Action type, attractiveness score and match context are optional fields carried through the contract but unused in v1. Priority: must-have
  > Socrates: Counter-argument accepted — "four required fields is too much for v1". Resolution: only the framing target is required. The chain that followed: dropping engine-side selection (FR-003) and dramaturgical ordering (FR-004) left the attractiveness score with no consumer in v1, so it joins action type and match context as carried-but-unused. They stay in the contract so the format does not have to change when overlays, selection and beat-sync land.
- FR-002: Engine can degrade gracefully when optional metadata is missing, applying a documented fallback rather than refusing the bundle; it rejects only when it cannot produce a reel at all. Priority: must-have
  > Socrates: Counter-argument accepted — "better to degrade than reject". Rationale: during a one-week prototype the metadata is hand-written, and strict validation means fighting the schema instead of watching reels. An engine that always returns something is more useful than one that is fussy.

### Ordering

- FR-003: ~~Engine selects which clips enter the reel.~~ **Dropped.** The caller supplies exactly the clips that go in.
  > Socrates: Counter-argument accepted — "with 3–5 clips there is nothing to select". Selection also belongs upstream: part one already scores clips, so it should hand over a chosen pool. An editor receives chosen material; he does not pick it himself. Revisit if the engine is ever fed a larger pool.
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

- **Given** a bundle of several short clips, each with a metadata record carrying at least a framing target
- **When** the caller invokes the montage engine on that bundle
- **Then** a single vertical video file is written, containing every supplied clip reframed to 9:16, ordered by match time and joined with hard cuts

#### Acceptance Criteria

- The output is a single file in 9:16 throughout, with no letterboxing or pillarboxing
- Every supplied clip appears in the output, in chronological order by match time
- The play — the action and the ball — is in frame for the whole of every clip
- Re-running on the same bundle produces the same output
- A record missing an optional field yields a reel built on the documented fallback, not an error

## Business Logic

**From the per-clip framing targets, the product computes a continuous vertical camera path and a matching zoom level over time — wide while the play builds, tight at the decisive moment — such that the action always fits the 9:16 frame and the movement reads as deliberate camera work rather than a shaky follow.**

The rule consumes one input the caller supplies: where the action sits in each clip over time. Its output is the reel itself — a vertical video in which the viewer never has to look for the ball and never notices the reframing. The user encounters the rule only through the finished reel; there is no setting, no preview, no knob to turn.

Two variables, not one: the path (where the frame sits) and the zoom (how wide it is). The zoom is what distinguishes this from a mechanical crop-follow — it is the part that imitates an editor's judgement about when to breathe and when to tighten.

After the Phase 4.5 revisions this is the **only** decision the engine makes. Clip selection belongs to the caller and ordering is chronological, so the entire value of v1 sits in this rule. That concentration is a risk worth naming: if the camera path is mediocre, nothing else in the pipeline can compensate.

## Non-Functional Requirements

- The output file plays on the mainstream short-form platforms without the user re-encoding or re-exporting it.
- A single unreadable input clip yields a reel assembled from the remaining clips plus a message naming the clip that failed — never an empty result.
- The same bundle submitted twice yields byte-identical output.
- A reel is produced in minutes, not hours, on commodity consumer hardware.

## Non-Goals

- **No player detection and no match cutting.** The whole of part one is outside this repository's surface — clips and metadata are assumed to arrive from elsewhere. This is the load-bearing non-goal: it is what keeps the project to one week instead of one quarter.
- **No soundtrack and no beat-synced cutting.** No music, no beat detection, no fitting clip lengths to a rhythm grid. Cut deliberately in Phase 3 because beat-sync inverts control over clip lengths and rebuilds the montage core rather than adding to it.
- **No on-screen text or graphics.** Player name, minute and score travel in the metadata but nothing is rendered from them. The fields exist so the contract does not have to change when overlays land.

## Forward: tech-stack

Not part of the PRD — captured for the stack-selection step that runs after `/10x-prd`.

- The engine must run locally on commodity consumer hardware with no paid API and no GPU requirement (stated as a Phase 3 guardrail; it reads as a runtime constraint, so it belongs here rather than in NFRs).
- Both AI models and deterministic video tooling are acceptable means. No preference was expressed, and none should be assumed.
- Render speed target: a reel in minutes, not hours, so the change-and-watch loop stays usable.

## Critical-path dependency on part one

**v1 cannot start, and cannot be evaluated, until part one produces framing-target data.** This is a blocker, not an open question.

After the Phase 4.5 revisions the engine makes exactly one decision — the camera path and zoom over time (see `## Business Logic`). That decision consumes the framing target and nothing else. There is therefore no subset of v1 that can be built or judged without it: no evaluation set, no camera-path rule, no way to tell whether a montage change helped.

Two unblocking routes were considered and rejected:

- **Hand-authoring the framing targets.** Rejected as unreasonable: manually pointing at where the player or the ball sits is not something a person should be doing per clip, and the exercise says nothing about whether the rule works on real upstream data.
- **Running a throwaway detector to generate an evaluation set.** Rejected: it reintroduces the second model that was deliberately cut from scope, even framed as a test fixture.

Accepted consequence: the one-week build window begins when part one delivers, not before. The schedule is serial.

### Handoff to part one

Since part one now sits on the critical path, the contract goes to its owner as soon as possible rather than after research. Sending it also settles Open Question 1 — the engine trusts the upstream framing target rather than detecting the action itself.

What part one is being asked for:

1. Short clips cut from a real match, 16:9, a few seconds each — enough for one reel.
2. Per clip, a framing target: where the play (the action and the ball) sits in the frame over time.
3. Optionally, and unused in v1: action type, an attractiveness score, match context.

Marked **v0** — provisional. The required field is stable because it follows directly from FR-005; the optional fields may still change or disappear.

## Quality cross-check

Run in Phase 7. All six greenfield elements present: Access Control, Business Logic (one-sentence rule), project artifacts, timeline-cost acknowledgement (1 week, under the three-week threshold), Non-Goals (three entries), preserved behavior n/a for greenfield. Status: `accepted`.

One contract-level inconsistency was surfaced during the check and resolved on the spot rather than deferred — see Open Question 2.

## Open Questions

1. ~~**Does the crop trust the upstream framing target, or detect the action itself?**~~ **Resolved:** the engine trusts the upstream framing target. Detecting the action here would reintroduce the second model that scope deliberately excludes. See `## Critical-path dependency on part one`.
1a. **How dense does the framing target have to be — per frame, or a few keypoints per clip?** — Open, and worth settling during the handoff conversation rather than in research. The play does not teleport, so sparse keypoints plus interpolation may be indistinguishable from a dense track. If so, part one's job shrinks considerably and the contract should say keypoints, not a per-frame path. Owner: user + part one's owner.
2. ~~**What exactly is the framing target?**~~ **Resolved in Phase 7:** the metadata field carries the position of the *play* — the action and the ball — not the position of the target player. This makes the contract consistent with FR-005 and gives part one an unambiguous job: return the path of the action. The target player's own position is no longer part of the required contract.
3. **Is slow-motion / zoom-punch a deferred feature or a non-goal?** — It was cut from v1 scope in Phase 3, but deliberately not declared a non-goal in Phase 6. Treat it as the first candidate for v2 rather than as ruled out. Owner: user.
4. **Does the attractiveness score stay in the contract with no v1 consumer?** — Kept as a carried-but-unused field after selection and dramaturgical ordering were dropped. If part one never produces it, the field should go. Owner: user, once part one is scoped.
5. **How does the camera-path rule survive a 100x scale increase?** — Per-frame path computation stops being free at scale; the rule would have to run on sparser samples or consume pre-computed paths from part one. Not a v1 blocker, but it constrains the shape of the rule. Owner: user.
