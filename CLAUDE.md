# AI Reel Montage

A montage engine: given short football clips plus per-clip metadata, it produces a finished
vertical (9:16) reel. Player detection and match cutting belong to a separate upstream project
("part one") and are out of scope here. The product shape lives in
`context/foundation/shape-notes.md` — read it before proposing anything.

# Workflow protocol — READ BEFORE ACTING

This project runs the 10x chain with **one chain step per session**. This is not a style
preference; it is how context is kept small and how the user stays in control.

## Hard rules

1. **One step per session.** Run exactly the chain step this session was opened for. When it is
   done, STOP.
2. **Never start the next step.** Do not chain into the following skill, even when the finished
   step's own output suggests it and even when it would obviously work. Instead: say the step is
   done, name the next step and its model, and let the user open a session for it. The user
   approves every new session by hand, on purpose.
3. **Commit and push before ending the step.** Artifacts in this repository are the only handoff
   between sessions. An uncommitted artifact does not exist for the next session. Commit to
   `main` with a message naming the step, then push.
4. **Read the artifacts, do not re-derive them.** Earlier decisions live in `context/foundation/`
   and `context/changes/`. Read them instead of re-asking the user or re-reasoning from scratch.
5. **If you are unsure which step this session is for, ask.** Do not guess and do not do two.
6. **Research method depends on the question.** Where a slice asks "how long does this take" or
   "does this produce identical output", measure it against the real materials — do not read about
   it. Where a slice asks "which technique", run the three-stage research first: web search, then
   a documentation knowledge base, then synthesis. The `10x-chain` skill says which slices are
   which and what each stage writes.

## Model per step

| Step | Model |
|---|---|
| `/10x-prd` | Sonnet |
| `/10x-tech-stack-selector` | Sonnet |
| `/10x-bootstrapper` | Sonnet |
| `/10x-agents-md` | Sonnet |
| `/10x-roadmap` | Sonnet |
| `/10x-new` | Sonnet |
| `/10x-research` | Fable |
| `/10x-plan` | Fable |
| `/10x-plan-review` | Fable |
| `/10x-tdd` / `/10x-implement` | Sonnet |
| `/10x-impl-review` | Fable |
| `/10x-archive` | Sonnet |

Judgment work sits on Fable because Fable draws from a separate weekly limit pool; this
deliberately preserves the shared "all models" budget for token-heavy implementation.

For the full chain, what each step leaves behind, and the TDD split, invoke the `10x-chain` skill.

# Stack conventions (Python + uv + ffmpeg)

Written by `/10x-bootstrapper`. The stack failed the "convention-based" quality gate, so this
section is the compensating control. Follow it exactly.

## Commands

All via `uv run` (never bare `python`/`pytest`). Python version is pinned in `.python-version`.

- Install/sync: `uv sync`
- Tests: `uv run pytest` (fast tier: `uv run pytest -m "not integration"`)
- Types: `uv run mypy` (strict, covers `src` and `tests`)
- Lint: `uv run ruff check` — fix with `uv run ruff check --fix`
- Format: `uv run ruff format src tests`
- Run the CLI: `uv run ai-reel-montage --help`

Before every commit: ruff check, ruff format, mypy and pytest must all pass.

## Layout (fixed — do not invent new top-level locations)

- `src/ai_reel_montage/` — the only package. `src` layout, built with `uv_build`.
  - `core/` — **pure core**: numpy/scipy maths (camera path, zoom, ordering, window logic).
  - `shell/` — **IO shell**: ijson streaming of the tracking JSON, ffmpeg pipes, filesystem.
  - `cli.py` — argument parsing and wiring only.
- `tests/unit/` — tests for `core` and `cli`; no video, no real files, no subprocess.
- `tests/integration/` — need ffmpeg and/or `transfer-*/` data; mark `@pytest.mark.integration`.
- `context/` — chain artifacts. Never edit from code or tooling.

## Pure core / IO shell rule

The camera-path rule (ball position over time -> vertical path + zoom so the action fits 9:16)
is the whole value of v1 and is built test-first. Therefore:

- `core/` never imports `subprocess`, `os`, `pathlib`, `open`, `ijson`, `json` file loading,
  network, `time`, `datetime.now` or `random` without an explicit seed. It takes arrays/dataclasses
  in and returns arrays/dataclasses out.
- `shell/` may call `core/`; `core/` never imports `shell/` or `cli`.
- Determinism: same inputs => byte-identical output. No wall clock, no unseeded randomness, no
  dict/set iteration order dependence in `core/`. ffmpeg runs single-threaded with bit-exact flags.

## Typing and style

- mypy strict is on; no untyped defs, no `Any` leaking from public functions. `scipy`/`ijson`
  stubs are ignored via config — wrap them in typed functions at the boundary.
- Prefer frozen `dataclass`es and `numpy.typing.NDArray` for data crossing module boundaries.
- Line length 100, double quotes, imports sorted by ruff. Do not silence a rule without a comment.

## Scope guards

Do not add a web framework, database, auth, GPU dependency or paid API — the PRD calls for none.
Never read `transfer-*/` in unit tests; large data stays behind `integration` marks.
Never run ffmpeg over the 99-minute source unbounded — always trim by window.
