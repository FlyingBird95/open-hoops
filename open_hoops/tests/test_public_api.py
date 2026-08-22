from open_hoops.analyzer import OpenHoop
from open_hoops.models import GameStats, Roster, TeamRoster, Video


def test_public_imports():
    assert OpenHoop is not None
    assert Video is not None
    assert GameStats is not None
    assert Roster is not None
    assert TeamRoster is not None


def test_video_construction():
    v = Video(path="game.mp4")
    assert v.path == "game.mp4"


def test_open_hoop_construction():
    hoops = OpenHoop(Video("game.mp4"))
    assert hoops is not None


def test_open_hoop_with_roster():
    roster = Roster(
        home=TeamRoster(color="#ffffff", players=[3, 11, 23]),
        away=TeamRoster(color="#0000ff", players=[5, 10, 15]),
    )
    hoops = OpenHoop(Video("game.mp4"), roster=roster)
    assert hoops._roster is roster
