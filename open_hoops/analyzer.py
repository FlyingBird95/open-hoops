"""Analyzer stub - will be implemented in future tasks."""


class Analyzer:
    def __init__(self, video_path: str, output_video: str | None = None):
        self.video_path = video_path
        self.output_video = output_video

    def run(self):
        raise NotImplementedError("Analyzer.run() not yet implemented")
