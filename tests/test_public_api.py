from open_hoops import OpenHoop, Video, GameStats


def test_public_imports():
    assert OpenHoop is not None
    assert Video is not None
    assert GameStats is not None


def test_video_construction():
    v = Video(path="game.mp4")
    assert v.path == "game.mp4"


def test_open_hoop_construction():
    hoops = OpenHoop(Video("game.mp4"))
    assert hoops is not None
