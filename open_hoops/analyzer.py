from __future__ import annotations
import math
import warnings
import cv2
import numpy as np

from open_hoops.models import GameStats, TeamStats, PlayerStats, Point, Video
from open_hoops.detector import Detector
from open_hoops.tracker import Tracker, compute_homography
from open_hoops.identity.team import TeamClassifier
from open_hoops.identity.player import PlayerIdentifier
from open_hoops.stats.possession import PossessionTracker
from open_hoops.stats.shots import ShotDetector
from open_hoops.stats.movement import MovementTracker
from open_hoops.stats.passes import PassDetector
from open_hoops.stats.score import ScoreTracker
from open_hoops.overlay import Overlay

_DEFAULT_SRC = np.array(
    [[0, 0], [1280, 0], [1280, 720], [0, 720]], dtype=np.float32
)
_DEFAULT_DST = np.array(
    [[0, 0], [28.65, 0], [28.65, 15.24], [0, 15.24]], dtype=np.float32
)

_BALL_MISSING_WARN_FRAMES = 5 * 30  # baseline at 30 fps


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class OpenHoop:
    def __init__(
        self,
        video: Video,
        model_path: str = "yolo11n.pt",
        src_pts: np.ndarray | None = None,
        dst_pts: np.ndarray | None = None,
    ) -> None:
        self._video = video
        self._model_path = model_path
        self._src = src_pts if src_pts is not None else _DEFAULT_SRC
        self._dst = dst_pts if dst_pts is not None else _DEFAULT_DST

    def extract_stats(self) -> GameStats:
        """Run detection/tracking/stats pipeline. Returns GameStats. Does not write video."""
        cap = cv2.VideoCapture(self._video.path)
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"Cannot open video: {self._video.path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        H = compute_homography(self._src, self._dst)
        detector = Detector(self._model_path)
        tracker = Tracker(H)
        team_clf = TeamClassifier()
        player_ident = PlayerIdentifier()
        possession = PossessionTracker()
        shots = ShotDetector()
        movement = MovementTracker()
        passes = PassDetector()
        score = ScoreTracker()

        all_events = []
        player_teams: dict[int, str] = {}
        warmup_frames: list[np.ndarray] = []
        warmup_bboxes: list[list[tuple[int, int, int, int]]] = []

        frame_idx = 0
        ball_missing_count = 0
        warn_threshold = int(_BALL_MISSING_WARN_FRAMES * (fps / 30.0)) if fps > 0 else _BALL_MISSING_WARN_FRAMES

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            fd = detector.detect(frame)
            tf = tracker.update(fd, frame_idx)

            if frame_idx < 30:
                warmup_frames.append(frame)
                warmup_bboxes.append([p.bbox for p in fd.players])
            elif frame_idx == 30:
                team_clf.fit(warmup_frames, warmup_bboxes)
                warmup_frames.clear()
                warmup_bboxes.clear()

            for p in fd.players:
                if p.track_id is None:
                    continue
                team = team_clf.assign(frame, p.bbox) if frame_idx >= 30 else "team_a"
                player_teams[p.track_id] = team
                player_ident.identify(frame, p.bbox, p.track_id)

            if tf.ball_pos is None:
                ball_missing_count += 1
                if ball_missing_count == warn_threshold:
                    warnings.warn(f"Ball not detected for 5+ seconds at frame {frame_idx}")
            else:
                ball_missing_count = 0

            possession_owner: int | None = None
            if tf.players and tf.ball_pos is not None:
                nearest = min(tf.players, key=lambda p: _dist(p.court_pos, tf.ball_pos))
                possession_owner = nearest.track_id

            poss_events = possession.update(tf, player_teams, frame_idx, fps)
            shot_events = shots.update(tf, player_teams, possession_owner, frame_idx, fps)
            shot_this_frame = any(e.type == "shot" for e in shot_events)
            pass_events = passes.update(tf, player_teams, possession_owner, frame_idx, fps, shot_this_frame)
            movement.update(tf)
            score.update(shot_events)

            all_events.extend(poss_events + shot_events + pass_events)
            frame_idx += 1

        cap.release()
        return self._build_stats(fps, frame_idx, player_teams, player_ident, movement, possession, score, team_clf, all_events)

    def edit_overlay(self, game_stats: GameStats, output_path: str) -> Video:
        """Render score HUD onto source video using precomputed game_stats. Writes to output_path."""
        cap = cv2.VideoCapture(self._video.path)
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"Cannot open video: {self._video.path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        overlay = Overlay()

        scores = {t.team_id: t.score for t in game_stats.teams}
        team_colors = {t.team_id: t.color for t in game_stats.teams}

        writer: cv2.VideoWriter | None = None
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if writer is None:
                h, w = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
            annotated = overlay.render(frame, scores, team_colors, frame_idx, fps)
            writer.write(annotated)
            frame_idx += 1

        cap.release()
        if writer:
            writer.release()

        return Video(path=output_path)

    def _build_stats(
        self,
        fps: float,
        total_frames: int,
        player_teams: dict[int, str],
        player_ident: PlayerIdentifier,
        movement: MovementTracker,
        possession: PossessionTracker,
        score: ScoreTracker,
        team_clf: TeamClassifier,
        events: list,
    ) -> GameStats:
        pct = possession.finalize(total_frames)

        teams: dict[str, TeamStats] = {
            "team_a": TeamStats(
                team_id="team_a",
                color=team_clf.team_colors.get("team_a", ""),
                score=score.scores["team_a"],
                possession_pct=pct.get("team_a", 0.0),
            ),
            "team_b": TeamStats(
                team_id="team_b",
                color=team_clf.team_colors.get("team_b", ""),
                score=score.scores["team_b"],
                possession_pct=pct.get("team_b", 0.0),
            ),
        }

        shot_makes: dict[int, int] = {}
        shot_attempts: dict[int, int] = {}
        passes_made: dict[int, int] = {}
        passes_received: dict[int, int] = {}
        possession_frames: dict[int, int] = {}

        for e in events:
            pid = e.player_id
            if pid is None:
                continue
            if e.type == "make":
                shot_makes[pid] = shot_makes.get(pid, 0) + 1
            elif e.type == "shot":
                shot_attempts[pid] = shot_attempts.get(pid, 0) + 1
            elif e.type == "pass":
                passes_made[pid] = passes_made.get(pid, 0) + 1
            elif e.type == "possession_change":
                possession_frames[pid] = possession_frames.get(pid, 0) + 1

        for tid, team_id in player_teams.items():
            jersey = player_ident._majority(tid)
            positions = [Point(x=x, y=y) for x, y in movement.get_positions(tid)]
            ps = PlayerStats(
                player_id=jersey,
                team_id=team_id,
                positions=positions,
                distance_covered_m=movement.get_distance(tid),
                shot_attempts=shot_attempts.get(tid, 0),
                shot_makes=shot_makes.get(tid, 0),
                passes_made=passes_made.get(tid, 0),
                passes_received=passes_received.get(tid, 0),
                possession_frames=possession_frames.get(tid, 0),
            )
            if team_id in teams:
                teams[team_id].players.append(ps)

        return GameStats(
            video=self._video,
            duration_seconds=total_frames / fps if fps > 0 else 0.0,
            fps=fps,
            teams=list(teams.values()),
            events=events,
        )
