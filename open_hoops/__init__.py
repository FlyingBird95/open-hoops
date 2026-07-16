from open_hoops.analyzer import Analyzer
from open_hoops.models import GameStats


def analyze(video_path: str, output_video: str | None = None) -> GameStats:
    return Analyzer(video_path, output_video=output_video).run()
