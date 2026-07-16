from open_hoops.analyzer import Analyzer


def analyze(video_path: str, output_video: str | None = None):
    return Analyzer(video_path, output_video=output_video).run()
