import math

import cv2
import numpy as np

from open_hoops.identity.player import finalize_jerseys
from open_hoops.identity.team import assign_teams_from_profiles
from open_hoops.models import (
    AnalysisResult,
    AnalyzedPlayerStats,
    AnalyzedTeamStats,
    BBox,
    Point,
    Roster,
    SubstitutionEvent,
    Video,
)
from open_hoops.overlay import Overlay
from open_hoops.pass_one import run_pass_one
from open_hoops.stats.ball_interpolator import interpolate_ball
from open_hoops.stats.movement import MovementTracker
from open_hoops.stats.passes import PassDetector
from open_hoops.stats.possession import PossessionTracker
from open_hoops.stats.score import ScoreTracker
from open_hoops.stats.shots import ShotDetector
from open_hoops.stats.substitutions import SubstitutionTracker

_DEFAULT_SRC = np.array([[0, 0], [1280, 0], [1280, 720], [0, 720]], dtype=np.float32)
_DEFAULT_DST = np.array([[0, 0], [28.65, 0], [28.65, 15.24], [0, 15.24]], dtype=np.float32)

_DEFAULT_FPS = 30.0


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class OpenHoop:
    def __init__(
        self,
        video: Video,
        model_path: str = "yolo26x.pt",
        src_pts: np.ndarray | None = None,
        dst_pts: np.ndarray | None = None,
        roster: Roster | None = None,
    ) -> None:
        self._video = video
        self._model_path = model_path
        self._src = src_pts if src_pts is not None else _DEFAULT_SRC
        self._dst = dst_pts if dst_pts is not None else _DEFAULT_DST
        self._roster = roster

    def extract_stats(self) -> AnalysisResult:
        """Single-pass detection/tracking/stats pipeline. Returns GameStats."""
        valid_numbers: set[int] | None = None
        if self._roster:
            valid_numbers = set(self._roster.home.players + self._roster.away.players)

        pass_one = run_pass_one(
            video_path=self._video.path,
            model_path=self._model_path,
            src_pts=self._src,
            dst_pts=self._dst,
            valid_numbers=valid_numbers,
        )

        # Lock team/jersey assignments from collected profiles
        assign_teams_from_profiles(pass_one.tracks, self._roster)
        finalize_jerseys(pass_one.tracks)

        team_assignments = {tid: p.team for tid, p in pass_one.tracks.items()}
        jersey_assignments = {tid: p.jersey for tid, p in pass_one.tracks.items()}

        # Apply interpolated ball positions to stored frames
        ball_positions = interpolate_ball(pass_one.ball_positions, pass_one.fps)
        for i, pos in enumerate(ball_positions):
            if pos is not None:
                pass_one.frames[i].ball_pos = pos

        # Replay frames through stats trackers
        fps = pass_one.fps
        subs = SubstitutionTracker()
        possession = PossessionTracker()
        shots = ShotDetector()
        movement = MovementTracker()
        passes = PassDetector()
        score = ScoreTracker()
        all_events = []

        for frame_idx, tf in enumerate(pass_one.frames):
            subs.update(tf)

            # Filter to on-court players only
            on_court_players = [p for p in tf.players if subs.is_on_court(p.track_id, frame_idx)]
            tf.players = on_court_players

            possession_owner: int | None = None
            if tf.players and tf.ball_pos is not None:
                nearest = min(tf.players, key=lambda p: _dist(p.court_pos, tf.ball_pos))
                possession_owner = nearest.track_id

            poss_events = possession.update(tf, team_assignments, frame_idx, fps)
            shot_events = shots.update(tf, team_assignments, possession_owner, frame_idx, fps)
            shot_this_frame = any(e.type == "shot" for e in shot_events)
            pass_events = passes.update(
                tf, team_assignments, possession_owner, frame_idx, fps, shot_this_frame
            )
            movement.update(tf)
            score.update(shot_events)

            frame_events = poss_events + shot_events + pass_events
            bbox_by_track = {p.track_id: p.bbox for p in tf.players}
            for ev in frame_events:
                if ev.player_id is not None and ev.player_id in bbox_by_track:
                    b = bbox_by_track[ev.player_id]
                    ev.bbox = BBox(x1=b[0], y1=b[1], x2=b[2], y2=b[3])

            all_events.extend(frame_events)

        return self._build_stats(
            fps,
            pass_one.frame_count,
            team_assignments,
            jersey_assignments,
            movement,
            possession,
            score,
            subs,
            all_events,
        )

    def edit_overlay(self, game_stats: AnalysisResult, output_path: str) -> Video:
        """Render score HUD onto source video. Writes to output_path."""
        cap = cv2.VideoCapture(self._video.path)
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"Cannot open video: {self._video.path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or _DEFAULT_FPS
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
        team_assignments: dict[int, str | None],
        jersey_assignments: dict[int, int | None],
        movement: MovementTracker,
        possession: PossessionTracker,
        score: ScoreTracker,
        subs: SubstitutionTracker,
        events: list,
    ) -> AnalysisResult:
        pct = possession.finalize(total_frames)

        team_colors: dict[str, str] = {}
        if self._roster:
            team_colors = {"team_a": self._roster.home.color, "team_b": self._roster.away.color}

        teams: dict[str, AnalyzedTeamStats] = {
            "team_a": AnalyzedTeamStats(
                team_id="team_a",
                color=team_colors.get("team_a", ""),
                score=score.scores["team_a"],
                possession_pct=pct.get("team_a", 0.0),
            ),
            "team_b": AnalyzedTeamStats(
                team_id="team_b",
                color=team_colors.get("team_b", ""),
                score=score.scores["team_b"],
                possession_pct=pct.get("team_b", 0.0),
            ),
        }

        shot_makes: dict[int, int] = {}
        shot_attempts: dict[int, int] = {}
        passes_made: dict[int, int] = {}
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

        substitutions: list[SubstitutionEvent] = []
        for tid, team_id in team_assignments.items():
            if team_id is None:
                continue
            jersey = jersey_assignments.get(tid)
            positions = [Point(x=x, y=y) for x, y in movement.get_positions(tid)]
            ps = AnalyzedPlayerStats(
                player_id=jersey,
                team_id=team_id,
                positions=positions,
                distance_covered_m=movement.get_distance(tid),
                game_time_seconds=subs.get_game_time(tid, fps),
                shot_attempts=shot_attempts.get(tid, 0),
                shot_makes=shot_makes.get(tid, 0),
                passes_made=passes_made.get(tid, 0),
                passes_received=0,
                possession_frames=possession_frames.get(tid, 0),
            )
            if team_id in teams:
                teams[team_id].players.append(ps)

            for frame_on, frame_off in subs.get_timeline(tid):
                substitutions.append(
                    SubstitutionEvent(
                        track_id=tid,
                        team_id=team_id,
                        jersey=jersey,
                        frame_on=frame_on,
                        frame_off=frame_off if frame_off < total_frames else None,
                    )
                )

        return AnalysisResult(
            video=self._video,
            duration_seconds=total_frames / fps if fps > 0 else 0.0,
            fps=fps,
            teams=list(teams.values()),
            events=events,
            substitutions=substitutions,
        )
