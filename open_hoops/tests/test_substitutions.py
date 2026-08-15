from open_hoops.stats.substitutions import SubstitutionTracker
from open_hoops.tracker import TrackedFrame, TrackedPlayer

COURT_W = 28.65
COURT_H = 15.24


def _frame_with_player(track_id, x, y, frame_idx=0):
    return TrackedFrame(
        players=[TrackedPlayer(track_id=track_id, bbox=(0, 0, 50, 100), court_pos=(x, y))],
        frame_idx=frame_idx,
    )


def test_player_on_court_initially():
    tracker = SubstitutionTracker()
    tf = _frame_with_player(1, 14.0, 7.0, frame_idx=0)
    tracker.update(tf)
    assert tracker.is_on_court(1, 0)


def test_player_off_court_after_leaving_bounds():
    tracker = SubstitutionTracker(off_threshold_frames=3)
    # Player on court for 2 frames
    for i in range(2):
        tracker.update(_frame_with_player(1, 14.0, 7.0, frame_idx=i))
    # Player leaves court bounds for 3 frames
    for i in range(2, 5):
        tracker.update(_frame_with_player(1, -5.0, 7.0, frame_idx=i))

    assert tracker.is_on_court(1, 1)
    assert not tracker.is_on_court(1, 4)


def test_player_returns_to_court():
    tracker = SubstitutionTracker(off_threshold_frames=3, on_threshold_frames=2)
    # On court
    for i in range(2):
        tracker.update(_frame_with_player(1, 14.0, 7.0, frame_idx=i))
    # Off court
    for i in range(2, 5):
        tracker.update(_frame_with_player(1, -5.0, 7.0, frame_idx=i))
    # Returns
    for i in range(5, 7):
        tracker.update(_frame_with_player(1, 14.0, 7.0, frame_idx=i))

    assert tracker.is_on_court(1, 6)


def test_player_disappearing_counts_as_off():
    tracker = SubstitutionTracker(off_threshold_frames=3)
    # Player visible on court
    for i in range(2):
        tracker.update(_frame_with_player(1, 14.0, 7.0, frame_idx=i))
    # Player not in frame at all for 3 frames
    for i in range(2, 5):
        tracker.update(TrackedFrame(players=[], frame_idx=i))

    assert not tracker.is_on_court(1, 4)


def test_game_time_calculation():
    tracker = SubstitutionTracker(off_threshold_frames=3)
    fps = 30.0
    # On court frames 0-4
    for i in range(5):
        tracker.update(_frame_with_player(1, 14.0, 7.0, frame_idx=i))
    # Off court frames 5-7 — threshold met at frame 7
    for i in range(5, 8):
        tracker.update(_frame_with_player(1, -5.0, 7.0, frame_idx=i))

    game_time = tracker.get_game_time(1, fps)
    # On-court through frame 6 (threshold not met until frame 7) = 7 frames
    assert abs(game_time - 7 / 30.0) < 0.01


def test_timeline_events():
    tracker = SubstitutionTracker(off_threshold_frames=3, on_threshold_frames=2)
    # On court
    for i in range(3):
        tracker.update(_frame_with_player(1, 14.0, 7.0, frame_idx=i))
    # Off court — threshold met at frame 5
    for i in range(3, 6):
        tracker.update(_frame_with_player(1, -5.0, 7.0, frame_idx=i))
    # Back on — threshold met at frame 7
    for i in range(6, 8):
        tracker.update(_frame_with_player(1, 14.0, 7.0, frame_idx=i))

    timeline = tracker.get_timeline(1)
    assert len(timeline) == 2
    assert timeline[0] == (0, 5)  # first stint ends when off-threshold met
    assert timeline[1][0] == 7  # second stint starts when on-threshold met


def test_out_of_bounds_detection():
    tracker = SubstitutionTracker(off_threshold_frames=1, margin=1.0)
    # Just inside margin
    tracker.update(_frame_with_player(1, -0.5, 7.0, frame_idx=0))
    assert tracker.is_on_court(1, 0)

    # Outside margin
    tracker.update(_frame_with_player(1, -1.5, 7.0, frame_idx=1))
    assert not tracker.is_on_court(1, 1)


def test_multiple_players_tracked_independently():
    tracker = SubstitutionTracker(off_threshold_frames=2)
    # Both on court
    tf = TrackedFrame(
        players=[
            TrackedPlayer(track_id=1, bbox=(0, 0, 50, 100), court_pos=(10.0, 7.0)),
            TrackedPlayer(track_id=2, bbox=(0, 0, 50, 100), court_pos=(20.0, 7.0)),
        ],
        frame_idx=0,
    )
    tracker.update(tf)

    # Player 1 leaves, player 2 stays
    for i in range(1, 3):
        tf = TrackedFrame(
            players=[
                TrackedPlayer(track_id=1, bbox=(0, 0, 50, 100), court_pos=(-5.0, 7.0)),
                TrackedPlayer(track_id=2, bbox=(0, 0, 50, 100), court_pos=(20.0, 7.0)),
            ],
            frame_idx=i,
        )
        tracker.update(tf)

    assert not tracker.is_on_court(1, 2)
    assert tracker.is_on_court(2, 2)
