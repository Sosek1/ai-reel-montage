# Follow-ups from the implementation review (S-02)

Source: `../reviews/impl-review.md`. These are the parts of the findings that belong to later
slices; everything that fitted S-02 was fixed in code on 2026-11-22.

## For the S-03 plan (smoothed camera path)

- **F4 — every crop path goes through `check_follow` before `render_clip`.** The right-edge bound
  (`x <= source_width - crop_width`) is refused by `check_follow` only; `render_clip` checks the
  path's length and the expression's size, and ffmpeg clamps an out-of-range x silently. A
  smoothed path can overshoot at the touchline. The S-03 plan must keep the `check_follow` call
  on the route to the render and add a named test of the smoothed path at the right edge. If a
  second production caller of `render_clip` appears, reconsider making the bound part of
  `CropPath` (S-04 turns it into a per-frame bound).
- The whole-match containment test (`test_ball_is_inside_the_crop_over_the_whole_match`) is the
  assertion that can really fail once the crop is no longer centred by construction. Keep it as
  it is and run it against the smoothed function.

## For the S-05 research and plan (several windows)

- **F5 — move read → path → check → verdict out of `cli.py`.** `cli._follow` composes
  `load_ball_track`, `crop_path`, `ball_centre` and `check_follow` for one window. S-05 runs that
  sequence once per window; it belongs in a shell-level function, with `cli.py` formatting the
  result. `FollowCheck.passed` already holds the pass rule.
- **F6 — the crop expression and `sendcmd`.** The flat-sum expression costs about 9.6 characters
  per output frame, is refused above 100 000 characters, and is evaluated term by term for every
  frame. One ffmpeg run per window keeps it at window size and needs no change. If one run has to
  carry several windows:
  - cheapest: the same expression read from a file (`-/filter:v`), which changes only how the
    text reaches ffmpeg;
  - `sendcmd` is helped by: `CropPath` crossing the boundary as data, the text being built in one
    place (`crop_filter`), `crop_x_expression` already reducing the path to change points, `fps`
    being an argument of `render_clip`, and the pixel test comparing against `path.x`;
  - `sendcmd` is hindered by: `crop_filter` returning one self-contained string that three tests
    pin, the script being a second temporary file while `_publishing` cleans up one, the size
    guard being expressed in characters, `_raw_frames` in the pixel test taking filter text only,
    and change times having to be exact frame times, which nothing formats yet.
