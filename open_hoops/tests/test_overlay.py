import numpy as np

from open_hoops.overlay import Overlay


def test_render_returns_same_shape():
    overlay = Overlay()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    result = overlay.render(
        frame, {"team_a": 10, "team_b": 8}, {"team_a": "#ff0000", "team_b": "#0000ff"}, 90, 30.0
    )
    assert result.shape == frame.shape


def test_render_does_not_mutate_input():
    overlay = Overlay()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    original = frame.copy()
    overlay.render(frame, {"team_a": 0, "team_b": 0}, {}, 0, 30.0)
    assert np.array_equal(frame, original)


def test_render_modifies_output():
    overlay = Overlay()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    result = overlay.render(
        frame, {"team_a": 5, "team_b": 3}, {"team_a": "#ff0000", "team_b": "#0000ff"}, 60, 30.0
    )
    assert not np.array_equal(result, frame)
