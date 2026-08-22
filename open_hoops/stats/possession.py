import math

from open_hoops.service.analysis.models import AnalyzedEvent
from open_hoops.tracker import TrackedFrame


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class PossessionTracker:
    def __init__(self) -> None:
        self._current_owner: int | None = None
        self._current_team: str | None = None
        self._frame_counts: dict[str, int] = {"team_a": 0, "team_b": 0}

    def update(
        self,
        tf: TrackedFrame,
        player_teams: dict[int, str],
        frame_idx: int,
        fps: float,
    ) -> list[AnalyzedEvent]:
        if tf.ball_pos is None or not tf.players:
            return []

        nearest = min(tf.players, key=lambda p: _dist(p.court_pos, tf.ball_pos))
        new_owner = nearest.track_id
        new_team = player_teams.get(new_owner, "team_a")

        events: list[AnalyzedEvent] = []
        if new_team != self._current_team and self._current_team is not None:
            events.append(
                AnalyzedEvent(
                    type="possession_change",
                    frame=frame_idx,
                    timestamp_sec=frame_idx / fps,
                    player_id=new_owner,
                    team_id=new_team,
                )
            )

        self._current_owner = new_owner
        self._current_team = new_team
        self._frame_counts[new_team] = self._frame_counts.get(new_team, 0) + 1
        return events

    def finalize(self, total_frames: int) -> dict[str, float]:
        if total_frames == 0:
            return {"team_a": 0.0, "team_b": 0.0}
        ball_frames = sum(self._frame_counts.values())
        if ball_frames == 0:
            return {"team_a": 0.0, "team_b": 0.0}
        return {team: count / ball_frames for team, count in self._frame_counts.items()}
