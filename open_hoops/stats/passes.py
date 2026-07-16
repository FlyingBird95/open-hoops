from __future__ import annotations
import math
from open_hoops.tracker import TrackedFrame
from open_hoops.models import GameEvent


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _nearest_player(players, ball_pos) -> int | None:
    if not players or ball_pos is None:
        return None
    return min(players, key=lambda p: _dist(p.court_pos, ball_pos)).track_id


class PassDetector:
    def __init__(self) -> None:
        self._prev_owner: int | None = None

    def update(
        self,
        tf: TrackedFrame,
        player_teams: dict[int, str],
        possession_owner: int | None,
        frame_idx: int,
        fps: float,
        shot_this_frame: bool,
    ) -> list[GameEvent]:
        if tf.ball_pos is None or shot_this_frame:
            self._prev_owner = possession_owner
            return []

        nearest = _nearest_player(tf.players, tf.ball_pos)
        events: list[GameEvent] = []

        if (
            nearest is not None
            and self._prev_owner is not None
            and nearest != self._prev_owner
        ):
            events.append(GameEvent(
                type="pass",
                frame=frame_idx,
                timestamp_sec=frame_idx / fps,
                player_id=self._prev_owner,
                team_id=player_teams.get(self._prev_owner),
            ))

        self._prev_owner = nearest
        return events
