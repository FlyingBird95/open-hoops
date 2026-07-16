import numpy as np
import pytest
from open_hoops.identity.team import TeamClassifier


def make_frame_with_player(color_bgr, bbox=(100, 200, 150, 300)):
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    x1, y1, x2, y2 = bbox
    frame[y1:y2, x1:x2] = color_bgr
    return frame


def test_fit_and_assign_two_teams():
    clf = TeamClassifier()
    red = (0, 0, 200)
    blue = (200, 0, 0)
    frames = []
    bboxes_per_frame = []
    for _ in range(5):
        f = make_frame_with_player(red, (100, 200, 150, 300))
        f2 = f.copy()
        f2[200:300, 400:450] = blue
        frames.append(f2)
        bboxes_per_frame.append([(100, 200, 150, 300), (400, 200, 450, 300)])

    clf.fit(frames, bboxes_per_frame)

    frame_red = make_frame_with_player(red, (100, 200, 150, 300))
    frame_blue = make_frame_with_player(blue, (400, 200, 450, 300))

    team_r = clf.assign(frame_red, (100, 200, 150, 300))
    team_b = clf.assign(frame_blue, (400, 200, 450, 300))

    assert team_r != team_b
    assert team_r in ("team_a", "team_b")
    assert team_b in ("team_a", "team_b")


def test_team_colors_populated_after_fit():
    clf = TeamClassifier()
    red = (0, 0, 200)
    blue = (200, 0, 0)
    frames, bboxes = [], []
    for _ in range(3):
        f = np.zeros((720, 1280, 3), dtype=np.uint8)
        f[200:300, 100:150] = red
        f[200:300, 400:450] = blue
        frames.append(f)
        bboxes.append([(100, 200, 150, 300), (400, 200, 450, 300)])
    clf.fit(frames, bboxes)
    assert "team_a" in clf.team_colors
    assert "team_b" in clf.team_colors
