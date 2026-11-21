---
name: 10x-chain
description: The 10x workflow chain for this project — which step comes next, which model runs it, what artifact it must leave behind, and which plan phases go through TDD. Use when starting a session and unsure which step it is for, when a step has just finished and the next one needs naming, or when the user asks "co dalej", "what's next", "which model for this step".
---

# 10x chain for AI Reel Montage

This project is greenfield, CLI-shaped, single-developer, after-hours. Every chain step runs in
its own session. The session protocol and the model table are in `CLAUDE.md`, which loads
automatically — this skill carries the detail.

## Why one step per session

Each step produces an artifact and consumes the previous one. Running two steps in one session
buys nothing (there is no parallel work here) and costs twice: the context fills with the first
step's reasoning, and the user loses the checkpoint where they would have caught a wrong turn.
The artifacts, not the conversation, are the handoff.

## The chain

Steps marked **done** are complete; their artifacts are in the repository.

| # | Step | Model | Leaves behind |
|---|---|---|---|
| 0 | `/10x-shape` — **done** | Opus | `context/foundation/shape-notes.md` |
| 1 | `/10x-prd` | Sonnet | `context/foundation/prd.md` |
| 2 | `/10x-tech-stack-selector` | Sonnet | `context/foundation/tech-stack.md` |
| 3 | `/10x-bootstrapper` | Sonnet | scaffolded project + verification log |
| 4 | `/10x-agents-md` | Sonnet | `AGENTS.md` |
| 5 | `/10x-roadmap` | Sonnet | `context/foundation/roadmap.md` |
| | — then, per roadmap slice — | | |
| 6 | `/10x-new` | Sonnet | `context/changes/<change-id>/change.md` |
| 7 | `/10x-research` | Fable | research notes in the change folder |
| 8 | `/10x-plan` | Fable | `context/changes/<change-id>/plan.md` |
| 9 | `/10x-plan-review` | Fable | review in the change folder |
| 10 | `/10x-tdd` or `/10x-implement` | Sonnet | code + flipped Progress rows |
| 11 | `/10x-impl-review` | Fable | `reviews/impl-review.md` |
| 12 | `/10x-archive` | Sonnet | change folder moved to `context/archive/` |

Steps 6–12 repeat per slice. Steps 1–5 run once.

## Which plan phases go through TDD

The domain rule of this product is a calculation: from per-clip framing targets, compute a
continuous vertical camera path and a matching zoom level over time. That calculation is the
whole value of v1, and it is pure numbers in, numbers out.

- **`/10x-tdd`** — camera-path geometry: path interpolation between framing keypoints, zoom
  selection over time, the containment check that proves the action fits inside the 9:16 frame,
  smoothing. Assertable without rendering a single frame.
- **`/10x-implement`** — everything around it: reading files, parsing the metadata contract,
  driving video tooling, concatenation, writing output. A unit test here proves nothing, because
  "looks good" is not an assertion.

The boundary runs exactly where numbers end and pixels begin. When a plan phase sits on the
boundary, split it rather than picking one side.

## Skills deliberately NOT in this chain

- **`/10x-test-plan`** — brownfield only, for existing products. It cannot run here yet. Revisit
  once the engine works and system-level test coverage is worth rolling out.
- **`/10x-configure-hook`** — reads `context/foundation/test-plan.md`, which does not exist for
  the same reason. Quality gates must be hand-written at bootstrap or deferred.
- **`/10x-design`** — no UI; this is a CLI tool.
- **`/10x-infra-research`** — runs locally, no deployment target to choose.
- **`/10x-slice`, `/10x-jira`, `/10x-branch`** — scoped to Gridaly repositories. This is not one.

## Closing a step

Before ending any session:

1. Confirm the step's artifact exists and is complete.
2. `git add` it, commit with a message naming the step, push to `origin main`.
3. Tell the user the step is done, name the next step and its model, and stop. Do not start it.

## State as of 2026-11-21

`/10x-shape` is closed. Part one delivered real materials (`transfer-01a1f923/`, git-ignored): a
99-minute match plus 398 MB of per-frame tracking. Shape-notes were corrected against them —
read `context/foundation/shape-notes.md`, sections `## Source materials` and `## Open Questions`,
before any step that touches the data.

What changed from the original shaping, and matters downstream:

- Trimming named timestamp windows out of the full match is **in** scope. Video analysis is not.
- The user names the moments; the engine never searches for them.
- The contract carries ball position over time plus player positions and identities. The
  attractiveness score and action type were removed — nothing produces them.
- Three data-quality issues are live and belong to `/10x-research`: fragmented player identities,
  jersey OCR reading numbers absent from both squads, and ~26% of ball positions predicted
  rather than detected.

Next step: `/10x-prd` on Sonnet, in its own session.
