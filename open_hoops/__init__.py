from open_hoops.analyzer import OpenHoop
from open_hoops.models import GameStats, Video


def analyze(video_path: str, output_video: str | None = None) -> GameStats:
    """Extract basketball stats from a fixed-court video.

    Args:
        video_path: Path to the input video file.
        output_video: Optional path for an annotated output video with score HUD.
            When omitted, no video is written.

    Returns:
        GameStats: Pydantic model with per-team and per-player stats, plus a
        full event log. Call ``.model_dump()`` for a JSON-serializable dict.

    Raises:
        ValueError: If the video file cannot be opened.
    """
    hoops = OpenHoop(Video(path=video_path))
    stats = hoops.extract_stats()
    if output_video:
        hoops.edit_overlay(stats, output_video)
    return stats
