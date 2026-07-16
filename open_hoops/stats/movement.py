"""Movement tracking for basketball players."""
from __future__ import annotations
import math
from open_hoops.tracker import TrackedFrame


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Euclidean distance between two points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


class MovementTracker:
    """Tracks player movement across frames, accumulating distance and position history."""

    def __init__(self) -> None:
        self._last_pos: dict[int, tuple[float, float]] = {}
        self._distances: dict[int, float] = {}
        self._positions: dict[int, list[tuple[float, float]]] = {}

    def update(self, tf: TrackedFrame) -> None:
        """Update tracker with a new frame of tracked players.

        Args:
            tf: TrackedFrame containing a list of tracked players
        """
        for player in tf.players:
            tid = player.track_id
            pos = player.court_pos
            self._positions.setdefault(tid, []).append(pos)
            if tid in self._last_pos:
                self._distances[tid] = (
                    self._distances.get(tid, 0.0) + _dist(self._last_pos[tid], pos)
                )
            self._last_pos[tid] = pos

    def get_distance(self, track_id: int) -> float:
        """Get total distance covered by a player.

        Args:
            track_id: The player's track ID

        Returns:
            Total distance in meters. Returns 0.0 if track_id is unknown.
        """
        return self._distances.get(track_id, 0.0)

    def get_positions(self, track_id: int) -> list[tuple[float, float]]:
        """Get all recorded court positions for a player.

        Args:
            track_id: The player's track ID

        Returns:
            List of (x, y) tuples representing court positions. Returns [] if track_id is unknown.
        """
        return self._positions.get(track_id, [])
