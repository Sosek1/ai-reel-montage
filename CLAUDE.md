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
