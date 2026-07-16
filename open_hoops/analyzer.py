from __future__ import annotations
import math
import warnings
import cv2
import numpy as np

from open_hoops.models import GameStats, TeamStats, PlayerStats, Point
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

# Default: assume 1280×720 frame mapped to NBA full-court dimensions (28.65m × 15.24m)
_DEFAULT_SRC = np.array(
    [[0, 0], [1280, 0], [1280, 720], [0, 720]], dtype=np.float32
)
_DEFAULT_DST = np.array(
    [[0, 0], [28.65, 0], [28.65, 15.24], [0, 15.24]], dtype=np.float32
)

# Warn if ball is missing for more than 5 seconds worth of frames
_BALL_MISSING_WARN_FRAMES = 5 * 30  # 5 seconds at 30 fps


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Analyzer:
    def __init__(
        self,
        video_path: str,
        model_path: str = "yolo11n.pt",
        output_video: str | None = None,
        src_pts: np.ndarray | None = None,
        dst_pts: np.ndarray | None = None,
    ) -> None:
        self._video_path = video_path
        self._model_path = model_path
        self._output_video = output_video
        self._src = src_pts if src_pts is not None else _DEFAULT_SRC
        self._dst = dst_pts if dst_pts is not None else _DEFAULT_DST

    def run(self) -> GameStats:
        cap = cv2.VideoCapture(self._video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {self._video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

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
        overlay = Overlay()

        writer: cv2.VideoWriter | None = None
        all_events = []
        player_teams: dict[int, str] = {}

        # Accumulate first 30 frames for team classifier warmup
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

            # Team classifier: warmup on frames 0-29, fit at frame 30
            if frame_idx < 30:
                warmup_frames.append(frame)
                warmup_bboxes.append([p.bbox for p in fd.players])
            elif frame_idx == 30:
                team_clf.fit(warmup_frames, warmup_bboxes)

            # Assign team and player identity for detected players
            for p in fd.players:
                if p.track_id is None:
                    continue
                team = team_clf.assign(frame, p.bbox) if frame_idx >= 30 else "team_a"
                player_teams[p.track_id] = team
                player_ident.identify(frame, p.bbox, p.track_id)

            # Track ball-missing warning
            if tf.ball_pos is None:
                ball_missing_count += 1
                if ball_missing_count == warn_threshold:
                    warnings.warn(
                        f"Ball not detected for 5+ seconds at frame {frame_idx}"
                    )
            else:
                ball_missing_count = 0

            # Determine possession owner: nearest player to ball
            possession_owner: int | None = None
            if tf.players and tf.ball_pos is not None:
                nearest = min(tf.players, key=lambda p: _dist(p.court_pos, tf.ball_pos))
                possession_owner = nearest.track_id

            # Update all stats modules
            poss_events = possession.update(tf, player_teams, frame_idx, fps)
            shot_events = shots.update(tf, player_teams, possession_owner, frame_idx, fps)
            shot_this_frame = any(e.type == "shot" for e in shot_events)
            pass_events = passes.update(
                tf, player_teams, possession_owner, frame_idx, fps, shot_this_frame
            )
            movement.update(tf)
            score.update(shot_events)

            all_events.extend(poss_events + shot_events + pass_events)

            # Write annotated output video if requested
            if self._output_video:
                if writer is None:
                    h, w = frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(self._output_video, fourcc, fps, (w, h))
                annotated = overlay.render(
                    frame, score.scores, team_clf.team_colors, frame_idx, fps
                )
                writer.write(annotated)

            frame_idx += 1

        cap.release()
        if writer:
            writer.release()

        return self._build_stats(
            fps, frame_idx, player_teams, player_ident, movement, possession, score, team_clf, all_events
        )

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

        # Aggregate per-player stats from events
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
            video_path=self._video_path,
            duration_seconds=total_frames / fps if fps > 0 else 0.0,
            fps=fps,
            teams=list(teams.values()),
            events=events,
        )
