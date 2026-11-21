---
bootstrapped_at: 2026-11-21T14:00:00Z
starter_id: custom
starter_name: "Python application (uv) + ffmpeg subprocess"
project_name: ai-reel-montage
language_family: python
package_manager: uv
cwd_strategy: subdir-then-move
bootstrapper_confidence: best-effort
phase_3_status: ok
audit_command: "pip-audit"
---

## Hand-off

```yaml
starter_id: custom
custom_starter:
  name: "Python application (uv) + ffmpeg subprocess"
  docs_url: https://docs.astral.sh/uv/guides/projects/
package_manager: uv
project_name: ai-reel-montage
hints: {language_family: python, team_size: solo, deployment_target: self-host,
  ci_provider: github-actions, ci_default_flow: manual-promotion,
  bootstrapper_confidence: best-effort, path_taken: custom, quality_override: false,
  self_check_answers: {typed: true, from_official_starter: true, conventions: false,
  docs_current: true, can_judge_agent: true}, has_auth: false, has_payments: false,
  has_realtime: false, has_ai: false, has_background_jobs: false}
```

Why this stack: see `context/foundation/tech-stack.md` (unchanged).

## Pre-scaffold verification

| Signal | Value | Severity | Notes |
| --- | --- | --- | --- |
| npm package | not run | n/a | Python stack |
| GitHub repo | astral-sh/uv last pushed 2026-11-21 | fresh | docs_url is not a GitHub URL; checked uv's repo instead |

## Scaffold log

**Resolved invocation**: `uv init --package --name ai-reel-montage --python ">=3.12" --no-workspace --vcs none .bootstrap-scaffold`
**Strategy**: subdir-then-move (uv 0.13.9, installed this session via the official astral.sh installer to ~/.local/bin — it was absent)
**Exit code**: 0
**Files moved**: 4 (.python-version, README.md, pyproject.toml replaced, src/ai_reel_montage/__init__.py)
**Conflicts (.scaffold siblings)**: none
**.gitignore handling**: not touched by uv; Python entries appended by hand, existing entries kept
**.bootstrap-scaffold cleanup**: deleted
**context/**: preserved untouched

Manual layout added on top (custom starter): `src/ai_reel_montage/{core,shell,cli.py}`, `tests/{unit,integration}`, pyproject with numpy, scipy, ijson (runtime) and pytest, mypy (strict), ruff (dev); author block with e-mail dropped from pyproject. Resolved versions are in `uv.lock`. CLAUDE.md: stack conventions appended under a new heading.

Checks: `uv run pytest` 1 passed; `uv run mypy` clean; `uv run ruff check` clean.

## System tooling

| Tool | Status |
| --- | --- |
| uv | 0.13.9 (installed this session) |
| Python | 3.14.4 (system), pinned in .python-version |
| ffmpeg | NOT INSTALLED (`ffmpeg` not found on PATH; apt/sudo required) |

**Action for the user before any video work:** `sudo apt install ffmpeg`, then record `ffmpeg -version` here. Nothing in this step needs ffmpeg; the first integration/video phase will.

## Post-scaffold audit

**Tool**: pip-audit (run via uvx against the exported uv.lock requirements, --no-deps)
**Summary**: 0 CRITICAL, 0 HIGH, 0 MODERATE, 0 LOW — no known vulnerabilities found.
**Direct vs transitive**: not distinguished by this tool.

## Hints recorded but not acted on

| Hint | Value |
| --- | --- |
| bootstrapper_confidence | best-effort (compensated by CLAUDE.md conventions) |
| quality_override | false |
| path_taken | custom |
| self_check_answers | typed, from_official_starter, docs_current, can_judge_agent = true; conventions = false |
| team_size | solo |
| deployment_target | self-host |
| ci_provider | github-actions (not set up; not this step's job) |
| ci_default_flow | manual-promotion |
| has_auth / payments / realtime / ai / background_jobs | all false |

## Next steps

Next chain step: `/10x-agents-md` (Sonnet). Install ffmpeg first (see System tooling).
