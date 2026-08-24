import numpy as np
import supervision as sv

from open_hoops.detection.rfdetr import (
    BALL_IN_BASKET_CLASS_ID,
    PLAYER_IN_POSSESSION_CLASS_ID,
    PLAYER_JUMP_SHOT_CLASS_ID,
    PLAYER_LAYUP_DUNK_CLASS_ID,
)
from open_hoops.service.analysis.models import AnalyzedEvent

SHOT_CLASS_IDS = [PLAYER_JUMP_SHOT_CLASS_ID, PLAYER_LAYUP_DUNK_CLASS_ID]
SHOT_COOLDOWN_FRAMES = 15


class EventDetector:
    def __init__(self) -> None:
        self._current_possession_team: str | None = None
        self._current_possession_player: int | None = None
        self._last_shot_frame: int = -999
        self._awaiting_make: bool = False
        self._last_shooter: int | None = None
        self._last_shooter_team: str | None = None

    def update(
        self,
        detections: sv.Detections,
        team_assignments: dict[int, str],
        frame_idx: int,
        fps: float,
    ) -> list[AnalyzedEvent]:
        events: list[AnalyzedEvent] = []
        timestamp = frame_idx / fps

        # Possession detection
        poss_mask = detections.class_id == PLAYER_IN_POSSESSION_CLASS_ID
        if poss_mask.any() and detections.tracker_id is not None:
            poss_ids = detections.tracker_id[poss_mask]
            player_id = int(poss_ids[0])
            team = team_assignments.get(player_id)
            if team and team != self._current_possession_team:
                events.append(
                    AnalyzedEvent(
                        type="possession_change",
                        frame=frame_idx,
                        timestamp_sec=timestamp,
                        player_id=player_id,
                        team_id=team,
                    )
                )
            self._current_possession_team = team
            self._current_possession_player = player_id

        # Shot detection
        shot_mask = np.isin(detections.class_id, SHOT_CLASS_IDS)
        if shot_mask.any() and (frame_idx - self._last_shot_frame) > SHOT_COOLDOWN_FRAMES:
            shooter_id = None
            if detections.tracker_id is not None:
                shot_tracker_ids = detections.tracker_id[shot_mask]
                shooter_id = int(shot_tracker_ids[0])

            team = team_assignments.get(shooter_id) if shooter_id else self._current_possession_team
            events.append(
                AnalyzedEvent(
                    type="shot",
                    frame=frame_idx,
                    timestamp_sec=timestamp,
                    player_id=shooter_id,
                    team_id=team,
                )
            )
            self._last_shot_frame = frame_idx
            self._awaiting_make = True
            self._last_shooter = shooter_id
            self._last_shooter_team = team

        # Make detection (ball-in-basket)
        make_mask = detections.class_id == BALL_IN_BASKET_CLASS_ID
        if make_mask.any() and self._awaiting_make:
            events.append(
                AnalyzedEvent(
                    type="make",
                    frame=frame_idx,
                    timestamp_sec=timestamp,
                    player_id=self._last_shooter,
                    team_id=self._last_shooter_team,
                )
            )
            self._awaiting_make = False

        return events
