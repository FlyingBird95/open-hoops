import math

from open_hoops.models import AnalyzedEvent
from open_hoops.tracker import TrackedFrame

_MAKE_RADIUS = 0.15  # ball centre within this of hoop centre = make


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class ShotDetector:
    def __init__(self, hoop_radius_m: float = 0.45) -> None:
        self._radius = hoop_radius_m
        self._in_region: dict[int, bool] = {}
        self._made: dict[int, bool] = {}  # hoop_idx -> current entry already produced a make

    def update(
        self,
        tf: TrackedFrame,
        player_teams: dict[int, str],
        possession_owner: int | None,
        frame_idx: int,
        fps: float,
    ) -> list[AnalyzedEvent]:
        if tf.ball_pos is None or not tf.hoops:
            return []

        events: list[AnalyzedEvent] = []
        team_id = player_teams.get(possession_owner) if possession_owner is not None else None

        for idx, hoop in enumerate(tf.hoops):
            dist = _dist(tf.ball_pos, hoop)
            was_in = self._in_region.get(idx, False)
            now_in = dist <= self._radius

            if now_in and not was_in:
                events.append(
                    AnalyzedEvent(
                        type="shot",
                        frame=frame_idx,
                        timestamp_sec=frame_idx / fps,
                        player_id=possession_owner,
                        team_id=team_id,
                    )
                )
                self._made[idx] = False
            if dist <= _MAKE_RADIUS and was_in and not self._made.get(idx, False):
                events.append(
                    AnalyzedEvent(
                        type="make",
                        frame=frame_idx,
                        timestamp_sec=frame_idx / fps,
                        player_id=possession_owner,
                        team_id=team_id,
                    )
                )
                self._made[idx] = True
            elif not now_in and was_in and not self._made.get(idx, False):
                events.append(
                    AnalyzedEvent(
                        type="miss",
                        frame=frame_idx,
                        timestamp_sec=frame_idx / fps,
                        player_id=possession_owner,
                        team_id=team_id,
                    )
                )

            if not now_in:
                self._made[idx] = False
            self._in_region[idx] = now_in

        return events
