---
starter_id: custom
custom_starter:
  name: "Python application (uv) + ffmpeg subprocess"
  docs_url: https://docs.astral.sh/uv/guides/projects/
package_manager: uv
project_name: ai-reel-montage
hints:
  language_family: python
  team_size: solo
  deployment_target: self-host
  ci_provider: github-actions
  ci_default_flow: manual-promotion
  bootstrapper_confidence: best-effort
  path_taken: custom
  quality_override: false
  self_check_answers:
    typed: true
    from_official_starter: true
    conventions: false
    docs_current: true
    can_judge_agent: true
  has_auth: false
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: false
---

## Why this stack

A solo, after-hours, one-week CLI whose whole value is one numeric rule (ball track to camera path and zoom) needs the shortest route to a working reel. Python with uv gives numpy/scipy for interpolation and smoothing, pytest for the TDD'd camera-path module, and ijson for streaming the 398 MB tracking file with bounded memory. Video work is delegated to the system ffmpeg over pipes: decode the trimmed window, crop and scale each frame with a time-varying window in numpy/OpenCV, and encode to H.264 with a single thread and bit-exact flags so output is byte-identical. No paid API, no GPU. The registry has no Python CLI card, so this is a custom starter (best-effort scaffolding via `uv init`). Convention-based is the weak gate; compensate in CLAUDE.md/AGENTS.md with a fixed src layout, strict mypy, ruff and a pure-core/IO-shell split. CI is GitHub Actions; deployment is self-host (local CLI).
