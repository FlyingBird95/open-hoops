from open_hoops.tracker import TrackedFrame

COURT_W = 28.65
COURT_H = 15.24


class SubstitutionTracker:
    def __init__(
        self,
        off_threshold_frames: int = 90,
        on_threshold_frames: int = 30,
        margin: float = 1.5,
    ) -> None:
        self._off_threshold = off_threshold_frames
        self._on_threshold = on_threshold_frames
        self._margin = margin

        self._on_court: dict[int, bool] = {}
        self._consecutive_off: dict[int, int] = {}
        self._consecutive_on: dict[int, int] = {}
        self._history: dict[int, list[bool]] = {}
        self._seen_in_frame: set[int] = set()
        self._all_tracks: set[int] = set()

    def _is_in_bounds(self, x: float, y: float) -> bool:
        return (
            -self._margin <= x <= COURT_W + self._margin
            and -self._margin <= y <= COURT_H + self._margin
        )

    def update(self, tf: TrackedFrame) -> None:
        self._seen_in_frame.clear()

        for p in tf.players:
            tid = p.track_id
            self._seen_in_frame.add(tid)
            self._all_tracks.add(tid)
            in_bounds = self._is_in_bounds(*p.court_pos)

            if tid not in self._on_court:
                self._on_court[tid] = in_bounds
                self._consecutive_off[tid] = 0
                self._consecutive_on[tid] = 0
                self._history[tid] = [in_bounds]
                continue

            currently_on = self._on_court[tid]

            if currently_on:
                if not in_bounds:
                    self._consecutive_off[tid] += 1
                    if self._consecutive_off[tid] >= self._off_threshold:
                        self._on_court[tid] = False
                        self._consecutive_on[tid] = 0
                else:
                    self._consecutive_off[tid] = 0
            else:
                if in_bounds:
                    self._consecutive_on[tid] += 1
                    if self._consecutive_on[tid] >= self._on_threshold:
                        self._on_court[tid] = True
                        self._consecutive_off[tid] = 0
                else:
                    self._consecutive_on[tid] = 0

            self._history[tid].append(self._on_court[tid])

        # Players not seen in this frame — count as off-court
        for tid in self._all_tracks:
            if tid in self._seen_in_frame:
                continue
            self._consecutive_off.setdefault(tid, 0)
            self._consecutive_off[tid] += 1
            if self._on_court.get(tid, False) and self._consecutive_off[tid] >= self._off_threshold:
                self._on_court[tid] = False
                self._consecutive_on[tid] = 0
            self._history.setdefault(tid, []).append(self._on_court.get(tid, False))

    def is_on_court(self, track_id: int, frame_idx: int) -> bool:
        history = self._history.get(track_id, [])
        if frame_idx >= len(history):
            return False
        return history[frame_idx]

    def get_game_time(self, track_id: int, fps: float) -> float:
        history = self._history.get(track_id, [])
        on_frames = sum(1 for v in history if v)
        return on_frames / fps if fps > 0 else 0.0

    def get_timeline(self, track_id: int) -> list[tuple[int, int]]:
        history = self._history.get(track_id, [])
        stints: list[tuple[int, int]] = []
        start: int | None = None

        for i, on in enumerate(history):
            if on and start is None:
                start = i
            elif not on and start is not None:
                stints.append((start, i))
                start = None

        if start is not None:
            stints.append((start, len(history)))

        return stints
