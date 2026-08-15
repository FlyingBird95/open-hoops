from __future__ import annotations

from open_hoops.models import GameEvent


class ScoreTracker:
    def __init__(self) -> None:
        self.scores: dict[str, int] = {"team_a": 0, "team_b": 0}

    def update(self, events: list[GameEvent]) -> None:
        for event in events:
            if event.type == "make" and event.team_id in self.scores:
                self.scores[event.team_id] += 2
