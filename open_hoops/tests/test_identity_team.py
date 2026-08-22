import numpy as np

from open_hoops.identity.team import TeamClassifier, assign_teams_from_profiles
from open_hoops.service.analysis.models import Roster, TeamRoster
from open_hoops.pass_one import TrackProfile


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


def test_assign_teams_two_clusters():
    # Create two tracks with distinct color histograms
    red_hist = np.zeros(24)
    red_hist[0] = 1.0  # hue bin 0 dominant (red-ish)
    blue_hist = np.zeros(24)
    blue_hist[8] = 1.0  # hue bin 8 dominant (blue-ish)

    tracks = {
        1: TrackProfile(track_id=1, histograms=[red_hist] * 5),
        2: TrackProfile(track_id=2, histograms=[blue_hist] * 5),
    }

    assign_teams_from_profiles(tracks, roster=None)

    # Both should get assigned, to different teams
    assert tracks[1].team is not None
    assert tracks[2].team is not None
    assert tracks[1].team != tracks[2].team


def test_assign_teams_with_roster():
    roster = Roster(
        home=TeamRoster(color="#ff0000", players=[1, 2]),
        away=TeamRoster(color="#0000ff", players=[3, 4]),
    )

    # Red-dominant histogram
    red_hist = np.zeros(24)
    red_hist[0] = 1.0
    # Blue-dominant histogram
    blue_hist = np.zeros(24)
    blue_hist[8] = 1.0

    tracks = {
        1: TrackProfile(track_id=1, histograms=[red_hist] * 5),
        2: TrackProfile(track_id=2, histograms=[blue_hist] * 5),
    }

    assign_teams_from_profiles(tracks, roster=roster)
    assert tracks[1].team == "team_a"  # red = home = team_a
    assert tracks[2].team == "team_b"


def test_assign_teams_empty_tracks():
    tracks = {}
    assign_teams_from_profiles(tracks, roster=None)
    # Should not crash


def test_assign_teams_single_track():
    hist = np.ones(24) / 24
    tracks = {1: TrackProfile(track_id=1, histograms=[hist] * 3)}
    assign_teams_from_profiles(tracks, roster=None)
    assert tracks[1].team is not None
