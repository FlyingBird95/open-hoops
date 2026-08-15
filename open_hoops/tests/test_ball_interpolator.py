import pytest

from open_hoops.stats.ball_interpolator import interpolate_ball


def test_no_gaps():
    positions = [(1.0, 2.0), (2.0, 3.0), (3.0, 4.0)]
    result = interpolate_ball(positions, fps=30.0)
    assert result == positions


def test_short_gap_interpolated():
    # Gap of 2 frames at 30fps = 0.067s, well under 0.5s max
    positions = [(0.0, 0.0), None, None, (3.0, 3.0)]
    result = interpolate_ball(positions, fps=30.0)
    assert result[0] == (0.0, 0.0)
    assert result[1] == pytest.approx((1.0, 1.0))
    assert result[2] == pytest.approx((2.0, 2.0))
    assert result[3] == (3.0, 3.0)


def test_long_gap_not_interpolated():
    # Gap of 30 frames at 30fps = 1.0s, exceeds 0.5s max
    positions = [(0.0, 0.0)] + [None] * 30 + [(10.0, 10.0)]
    result = interpolate_ball(positions, fps=30.0)
    assert result[0] == (0.0, 0.0)
    assert result[15] is None  # gap too long, left as None
    assert result[31] == (10.0, 10.0)


def test_gap_at_start():
    positions = [None, None, (2.0, 2.0), (3.0, 3.0)]
    result = interpolate_ball(positions, fps=30.0)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == (2.0, 2.0)


def test_gap_at_end():
    positions = [(1.0, 1.0), (2.0, 2.0), None, None]
    result = interpolate_ball(positions, fps=30.0)
    assert result[2] is None
    assert result[3] is None


def test_empty_input():
    assert interpolate_ball([], fps=30.0) == []
