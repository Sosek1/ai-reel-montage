import numpy as np
import pytest
from numpy.typing import NDArray

from ai_reel_montage.core.camera import (
    BallTrack,
    CameraPathError,
    CropPath,
    FollowCheck,
    ball_centre,
    ball_inside,
    check_follow,
    crop_path,
    crop_x_expression,
)
from ai_reel_montage.core.framing import CropBox, centre_crop
from ai_reel_montage.core.window import FrameRange

SOURCE_WIDTH = 1920
CENTRE = centre_crop(SOURCE_WIDTH, 1080)  # 608 wide at x 656
NAN = float("nan")


def _track(frames: list[int], xs: list[float]) -> BallTrack:
    return BallTrack(frame_idx=np.array(frames, dtype=np.int64), x=np.array(xs, dtype=np.float64))


def _path(track: BallTrack, start: int, n: int, centre: CropBox = CENTRE) -> CropPath:
    return crop_path(FrameRange(start, n), track, SOURCE_WIDTH, centre)


def _hand_path(xs: list[int], fallback: list[bool] | None = None) -> CropPath:
    flags = fallback if fallback is not None else [False] * len(xs)
    return CropPath(x=np.array(xs, dtype=np.int64), fallback=np.array(flags, dtype=np.bool_))


def _gap_track() -> BallTrack:
    # Ball at 600, then two samples without a ball, then 1500.
    return _track([0, 3, 6, 9], [600.0, NAN, NAN, 1500.0])


# --- the rule -------------------------------------------------------------------------------


def test_crop_is_centred_on_the_ball_at_a_sample_frame() -> None:
    path = _path(_track([0], [1000.0]), 0, 1)
    assert path.x.tolist() == [696]


def test_frames_between_samples_are_interpolated_linearly() -> None:
    path = _path(_track([0, 3], [1000.0, 1030.0]), 0, 4)
    assert path.x.tolist() == [696, 706, 716, 726]


def test_crop_x_is_even_with_ties_upward() -> None:
    # 961 - 304 = 657 is equidistant from 656 and 658; ties go up (numpy.round would give 656).
    assert _path(_track([0], [961.0]), 0, 1).x.tolist() == [658]


def test_interpolated_tie_rounds_upward() -> None:
    track = _track([0, 3], [1000.0, 1003.0])
    assert ball_centre(FrameRange(0, 4), track)[1] == 1001.0
    assert _path(track, 0, 4).x[1] == 698


def test_crop_is_clamped_at_both_picture_edges() -> None:
    track = _track([0, 3], [3.51, 1917.05])
    path = _path(track, 0, 4)
    assert path.x[0] == 0
    assert path.x[3] == 1312
    centres = ball_centre(FrameRange(0, 4), track)
    assert ball_inside(path, centres, CENTRE.width)[[0, 3]].all()


def test_run_without_ball_is_crossed_in_a_straight_line() -> None:
    track = _gap_track()
    frames = FrameRange(0, 10)
    assert ball_centre(frames, track)[3] == 900.0
    path = _path(track, 0, 10)
    assert path.fallback.tolist() == [False] + [True] * 8 + [False]


def test_window_starting_inside_a_run_uses_the_sample_before_it() -> None:
    centres = ball_centre(FrameRange(4, 3), _gap_track())
    assert centres[0] == 1000.0  # 600 + (1500 - 600) * 4 / 9


def test_no_position_after_the_window_holds_the_last_known() -> None:
    track = _track([0, 3, 6], [1000.0, 1030.0, NAN])
    path = _path(track, 0, 9)
    assert path.x[3:].tolist() == [726] * 6  # held at the sample at frame 3 (1030 - 304)
    assert path.fallback.tolist() == [False] * 4 + [True] * 5


def test_no_position_before_the_window_holds_the_first_known() -> None:
    track = _track([0, 3, 6], [NAN, 1000.0, 1030.0])
    path = _path(track, 0, 4)
    assert path.x[:4].tolist() == [696] * 4
    assert path.fallback.tolist() == [True, True, True, False]


@pytest.mark.parametrize("track", [_track([0, 3], [NAN, NAN]), _track([], [])])
def test_track_without_any_position_gives_the_centre_crop(track: BallTrack) -> None:
    path = _path(track, 10, 5)
    assert path.x.tolist() == [656] * 5
    assert path.fallback.all()


def test_window_not_starting_on_the_sample_grid() -> None:
    track = _track([18999, 19002], [1000.0, 1030.0])
    path = _path(track, 19001, 1)
    assert ball_centre(FrameRange(19001, 1), track)[0] == pytest.approx(1020.0)
    assert path.x.tolist() == [716]
    assert not path.fallback[0]


def test_ball_is_inside_the_crop_in_every_frame_across_a_large_jump() -> None:
    track = _track([0, 3], [700.0, 1295.0])  # 595 px, the largest step in the recording
    frames = FrameRange(0, 4)
    path = crop_path(frames, track, SOURCE_WIDTH, CENTRE)
    centres = ball_centre(frames, track)
    assert ball_inside(path, centres, CENTRE.width).all()
    # The last value is the tie 1295 - 304 = 991, rounded upward.
    assert path.x.tolist() == [396, 594, 792, 992]


def test_ball_inside_reports_a_ball_outside_the_crop() -> None:
    centres = np.array([1000.0, 1000.0, NAN])
    path = _hand_path([0, 696, 696])
    assert ball_inside(path, centres, 608).tolist() == [False, True, False]


def test_crop_path_arrays_are_read_only() -> None:
    path = _hand_path([0, 2])
    with pytest.raises(ValueError):
        path.x[0] = 4


# --- types ----------------------------------------------------------------------------------


def test_crop_path_with_odd_x_is_rejected() -> None:
    with pytest.raises(CameraPathError):
        _hand_path([0, 3])


def test_crop_path_with_negative_x_is_rejected() -> None:
    with pytest.raises(CameraPathError):
        _hand_path([-2])


def test_crop_path_with_unequal_array_lengths_is_rejected() -> None:
    with pytest.raises(CameraPathError):
        _hand_path([0, 2], [False])


def test_track_with_non_increasing_frames_is_rejected() -> None:
    with pytest.raises(CameraPathError):
        _track([0, 3, 3], [1.0, 2.0, 3.0])


def test_track_with_unequal_array_lengths_is_rejected() -> None:
    with pytest.raises(CameraPathError):
        _track([0, 3], [1.0])


# --- the check ------------------------------------------------------------------------------


def test_check_counts_only_frames_that_are_not_fallback() -> None:
    track = _gap_track()
    frames = FrameRange(0, 10)
    path = crop_path(frames, track, SOURCE_WIDTH, CENTRE)
    result = check_follow(path, ball_centre(frames, track), SOURCE_WIDTH, CENTRE.width)
    assert result == FollowCheck(tracked=2, inside=2, fallback=8)


def test_check_never_counts_a_fallback_frame_as_inside() -> None:
    # The fallback happens to assume a position that contains the centre; still not inside.
    path = _hand_path([696, 696], [True, True])
    result = check_follow(path, np.array([1000.0, 1000.0]), SOURCE_WIDTH, 608)
    assert result == FollowCheck(tracked=0, inside=0, fallback=2)


def test_check_of_a_track_without_any_position_counts_nothing_as_tracked() -> None:
    frames = FrameRange(0, 6)
    track = _track([], [])
    path = crop_path(frames, track, SOURCE_WIDTH, CENTRE)
    result = check_follow(path, ball_centre(frames, track), SOURCE_WIDTH, CENTRE.width)
    assert result == FollowCheck(tracked=0, inside=0, fallback=6)


def test_check_reports_a_tracked_frame_outside_the_crop() -> None:
    path = _hand_path([0, 696])
    result = check_follow(path, np.array([1000.0, 1000.0]), SOURCE_WIDTH, 608)
    assert result.inside < result.tracked
    assert result == FollowCheck(tracked=2, inside=1, fallback=0)


def test_check_rejects_a_path_beyond_the_right_edge() -> None:
    path = _hand_path([1314])
    with pytest.raises(CameraPathError):
        check_follow(path, np.array([1500.0]), SOURCE_WIDTH, 608)


def test_check_rejects_centres_of_a_different_length() -> None:
    with pytest.raises(CameraPathError):
        check_follow(_hand_path([0, 2]), np.array([1.0]), SOURCE_WIDTH, 608)


# --- the expression -------------------------------------------------------------------------


def _evaluate(expression: str, n: int) -> int:
    """Evaluate the flat sum the way ffmpeg's ``gte`` does, for one frame number ``n``."""
    total = 0
    sign = 1
    term = ""
    for ch in expression + "+":
        if ch in "+-":
            if term:
                if "*" in term:
                    value, condition = term.split("*")
                    threshold = int(condition.removeprefix("gte(n,").removesuffix(")"))
                    total += sign * int(value) * (1 if n >= threshold else 0)
                else:
                    total += sign * int(term)
            term = ""
            sign = 1 if ch == "+" else -1
        else:
            term += ch
    return total


def test_expression_of_a_constant_path_is_a_single_number() -> None:
    assert crop_x_expression(np.array([656, 656, 656], dtype=np.int64)) == "656"


def test_expression_has_one_term_per_change() -> None:
    x = np.array([656, 656, 660, 660, 658, 658, 658, 700], dtype=np.int64)
    assert crop_x_expression(x) == "656+4*gte(n,2)-2*gte(n,4)+42*gte(n,7)"


def test_expression_evaluates_back_to_the_path() -> None:
    rng = np.random.default_rng(7)
    x = (2 * rng.integers(0, 657, size=300)).astype(np.int64)
    x[50:80] = x[50]  # a constant stretch among the changes
    expression = crop_x_expression(x)
    assert " " not in expression
    assert [_evaluate(expression, n) for n in range(len(x))] == x.tolist()


def test_expression_of_an_empty_path_is_rejected() -> None:
    empty: NDArray[np.int64] = np.array([], dtype=np.int64)
    with pytest.raises(CameraPathError):
        crop_x_expression(empty)
