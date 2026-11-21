# Ball-Following Crop (S-02) — Plan Brief

> Full plan: `context/changes/ball-following-crop/plan.md`
> Research: `context/changes/ball-following-crop/research.md`

## What & Why

The caller adds the tracking file to the S-01 command and gets a clip whose 9:16 crop follows the
ball instead of sitting in the centre. It is the milestone's north star (FR-001, FR-002, FR-005,
US-01): the first clip framed by the real tracking data, and the first contact between the 398 MB
tracking file and the footage.

## Starting Point

S-01 renders one named window with a fixed centre crop; nothing reads the tracking file. Research
measured that the tracking grid maps exactly onto source frames, that reading a window by
streaming costs at most about 5 s at 35 MB, and that a crop moved by a filter expression gives the
same pixels as slicing frames in numpy.

## Desired End State

`uv run ai-reel-montage --input <recording> --tracking <tracks.json> --window 6:20-6:30 --output out/clip.mp4`
writes a 1080x1920 clip of exactly 500 frames with the crop centred on the ball in every frame, as
far as the picture edge allows. The command prints how many frames passed the ball-inside-crop
check and how many were framed by the fallback. Two runs give the same bytes; without `--tracking`
the command behaves exactly as in S-01.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Stretch without a ball (45 runs, 2.82–25.74 s) | cross it in a straight line between the positions on either side | No frozen crop and no jump, and it is the rule the data supplier already applies to shorter gaps. | Plan (user) |
| Position missing on one side, or everywhere | hold the nearest known; centre crop when there is none | FR-002 asks for a clip with a documented fallback, not a refusal. | Plan |
| Frames between samples | linear interpolation, the crop moves every frame | One function covers this and the gap rule, and the ball is inside the crop in every frame. | Plan (user) |
| Predicted samples (21.3%) | used as positions | They are already straight lines between detections. | Research |
| Smoothing | none; the rule is named "piecewise-linear follow" | S-03 owns smoothing and replaces this one function. | Plan |
| Tracking read | ijson stream, `frame_idx` taken from the file | Bounded memory, no reliance on the file's exact serialisation, and the sample before the window comes for free. | Research / Plan |
| Tracking argument | optional `--tracking` | S-01 behaviour and tests stay; the centre clip remains for comparison. | Plan (user) |
| Render route | flat-sum expression in `n` for the `crop` filter | One process and the S-01 command unchanged; the text is a pure function of the path. | Research / Plan (user) |
| Crop resolution | even x, ties upward, clamped to 0–1312 | An odd x is silently rounded down by the filter. | Research |
| Verification | check on every run and over the whole match in tests | "Ball inside the crop" is asserted by a command, not judged by eye. | Plan |

## Scope

**In scope:**

- `core/camera.py`: ball track and crop path types, the follow rule, the ball-inside-crop check,
  the filter expression
- `shell/tracking.py`: streamed read of one window's ball track, with fps and ordering checks
- `render_clip` accepting a crop path; `--tracking` on the CLI; the check result on stdout
- Unit tests on hand-written tracks; integration tests on the real file and recording
- The fallback documented in `README.md`

**Out of scope:**

- Smoothing or damping of the path, different treatment of predicted samples (S-03)
- Zoom and vertical motion (S-04); several windows or one pass serving them (S-05)
- The watchability verdict and the evaluation set (S-06)
- Piped rendering, `sendcmd`, byte-offset reads, any stored output hash

## Architecture / Approach

```
cli.py  --window, probe, frame range, centre crop-->   as in S-01
        --read track-->   shell/tracking.py   load_ball_track -> BallTrack (frame numbers, x, NaN = no ball)
        --path-------->   core/camera.py      crop_path -> CropPath (even x per frame, fallback flags)
        --check------->   core/camera.py      ball_centre, ball_inside -> counts; a failure renders nothing
        --render------>   shell/video.py      render_clip(path): crop=608:1080:x='<expression>':y=0
```

Two types cross the core/shell boundary: `BallTrack` inward, `CropPath` outward. The core sees no
file and returns no ffmpeg arguments; the shell does no arithmetic on positions.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Crop path in the pure core (`/10x-tdd`) | The follow rule, the check and the expression, unit-tested on hand-written tracks | A boundary of the rule (rounding, gap edges, fallback flags) left loose and changed later by accident |
| 2. Tracking reader in the IO shell (`/10x-implement`) | A window's ball track from the real file in bounded memory; ball-inside-crop proven over the whole match | The reader stopping too early or too late around a stretch without a ball |
| 3. Moving crop, `--tracking`, end-to-end check (`/10x-implement`) | The working command, pixel-checked against numpy, plus a watched clip | The rendered crop not being the crop the path describes |

**Prerequisites:** S-01 (done); ffmpeg and ffprobe on `PATH`; the recording and
`full_match_tracks.json` in `transfer-01a1f923/`.
**Estimated effort:** 3 implementation sessions, one per phase; Phase 3 is the largest.

## Open Risks & Assumptions

- The check holds by construction for a centred, clamped crop. It guards frame mapping, clamp and
  rounding; it does not show that the recorded positions are right (research finding 2 does).
- In a long stretch without a ball the crop travels across the pitch on an assumed line, up to
  1876 px in 25 s. The clip is produced and the fallback frames are counted, but what they show is
  not verified.
- Whether the `crop` filter can change size per frame was not measured; S-04 must measure it, and
  a move to pipes would change container bytes once.
- The expression is limited to 100 000 characters, about three minutes of footage.
- The path is raw and will look jittery; that is S-03's subject, not a defect here.
- Only this one tracking file has been seen; a cold-cache read was not measured.

## Success Criteria (Summary)

- One command with `--tracking` produces a vertical clip in which the ball stays in the picture,
  and says so itself: `ball inside crop in 500/500 frames`.
- Over the whole match, every one of the 94 415 recorded ball positions lies inside the crop.
- A second run gives the same file, and a run without `--tracking` is unchanged from S-01.
