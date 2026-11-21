# First Playable Clip (S-01) — Plan Brief

> Full plan: `context/changes/first-playable-clip/plan.md`
> Research: `context/changes/first-playable-clip/research.md`

## What & Why

The caller names one window of the match recording and gets a playable 9:16 clip trimmed to it,
framed by a fixed centre crop, with the match audio. It is the first roadmap slice (FR-001a,
US-01) because the whole pipeline rides on video being cut cheaply and exactly, and because it
sets up window handling, determinism and the pure-core / IO-shell split for every later slice.

## Starting Point

The project is scaffolded but empty: the CLI has only `--version`, and `core/` and `shell/` hold
no code. Research measured the real AV1 source and found the trim is cheap (about 1 s of decoding
for a 10 s window, about 12 s for the whole render) and which ffmpeg flags make the cut exact and
byte-identical.

## Desired End State

`uv run ai-reel-montage --input <recording> --window 10:04.78-10:14.78 --output out/clip.mp4`
writes a 1080x1920 H.264 clip of exactly 500 frames with AAC audio of the same length. Running it
twice gives the same bytes. A window that cannot be honoured exactly writes no file and exits
non-zero with a message naming the window and the recording length.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Seek placement | before the input | Decode cost stays about 1 s at any offset instead of growing with it. | Research |
| Clip length | `-frames:v` plus `-t` | `-t` alone drops a frame for off-grid starts; `-frames:v` alone leaves audio 16 ms short. | Research / Plan |
| Determinism | one encoder thread, `-bitexact` | The only variant whose bytes do not depend on the core count. | Research |
| Pixel aspect | `setsar=1` | Without it the file is flagged 76:135, not 9:16. | Research |
| Audio | keep match audio as AAC 128k | Costs no time, stays byte-identical, and a silent clip reads as broken. | Plan |
| Encoder | `veryfast`, CRF 20, fixed | 12 s per 10 s clip against 31 s at `medium`; the engine has no knobs. | Plan |
| Rendering | ffmpeg filters, one process | Smallest code for a fixed crop; pipes are S-02's question. | Plan |
| Window form | `--window A-B`, seconds or `[h:]mm:ss[.fff]` | Matches what a video player shows and repeats cleanly in S-05. | Plan |
| Window past the end | reject, no file | "Trims exactly those windows" stays literally true. | Plan |
| Rounding | nearest source frame, ties upward | Deterministic and at most 10 ms from what was typed. | Plan |
| Recording properties | probed with `ffprobe` | A new recording needs no code change. | Plan |
| Output writing | temporary file, renamed on success | A failed run leaves no partial clip; measured to give the same bytes. | Plan |

## Scope

**In scope:**

- Window parsing, frame conversion, validation and centre-crop geometry in `core/`
- `ffprobe` and `ffmpeg` wrappers with a frame-count check and atomic write in `shell/`
- `--input`, `--window`, `--output` on the CLI, with exit codes 0, 1 and 2
- Unit tests for the maths and the CLI; integration tests on 2 s windows of the real source
- A usage note in `README.md`

**Out of scope:**

- Tracking data, ball-following crop, camera path, zoom (S-02 to S-04)
- More than one window, ordering, joining (S-05)
- Clamping out-of-range windows, encoder options, piped rendering, `+faststart`
- Any stored output hash, platform upload tests, cross-machine byte identity

## Architecture / Approach

```
cli.py  --window text-->  core/window.py   parse_window -> Window
        --probe------->   shell/video.py   probe_source -> SourceInfo (size, fps, frame count)
        --validate---->   core/window.py   to_frame_range -> FrameRange (or WindowError)
        --geometry---->   core/framing.py  centre_crop -> CropBox (608x1080 at x=656)
        --render------>   shell/video.py   render_clip: ffmpeg -> .partial -> count -> rename
```

`core/` is arithmetic on `Fraction` and `int` with no IO. `shell/` owns the two subprocess calls.
`cli.py` only wires them and maps exceptions to messages and exit codes.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Window maths in the pure core (`/10x-tdd`) | Parsed, validated frame range and crop rectangle, fully unit-tested | A boundary rule (rounding, last frame) defined loosely and changed later by accident |
| 2. Probe and render in the IO shell (`/10x-implement`) | A rendered, checked clip from a frame range; integration tests on the real source | Integration tests skipping silently and verifying nothing |
| 3. CLI wiring and end-to-end check (`/10x-implement`) | The working command, plus a timed and watched 10 s clip | Error paths mapped to the wrong exit code or leaving a file behind |

**Prerequisites:** ffmpeg and ffprobe on `PATH` (installed, 8.0.1); the recording in
`transfer-01a1f923/`. No roadmap prerequisites.
**Estimated effort:** 3 implementation sessions, one per phase; each is small.

## Open Risks & Assumptions

- Visual quality of `veryfast` CRF 20 was not compared against `medium`; changing it later changes
  output bytes but nothing structural.
- If S-02 moves to piped frames, output bytes change. No test pins a stored hash, so nothing
  breaks.
- Byte identity is established only for this machine and this ffmpeg build.
- Keyframe spacing was sampled, not scanned; a much longer gap somewhere would slow one seek, not
  break it.
- Whether short-form platforms accept 50 fps H.264 level 4.2 without re-encoding is untested.
- The probe relies on the container reporting a frame count; a recording without one is rejected
  with a clear error rather than scanned.

## Success Criteria (Summary)

- One command turns a named window into a vertical clip with sound that plays in an ordinary
  player, in well under a minute for 10 s of footage.
- The clip has exactly the frames asked for, and a second run produces the same file.
- A window outside the recording produces an error and no file, never a shorter clip.
