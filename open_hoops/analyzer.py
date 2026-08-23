from math import hypot

import numpy as np
import supervision as sv

from open_hoops.core.logger.default import DefaultLogger
from open_hoops.core.logger.protocol import LoggerProtocol
from open_hoops.court.keypoint_homography import CourtMapper
from open_hoops.detection.rfdetr import RFDETRDetector
from open_hoops.identity.number_reader import NumberReader, NumberValidator
from open_hoops.identity.team_classifier import TeamClassifierWrapper
from open_hoops.service.analysis.models import (
    AnalysisResult,
    AnalyzedEvent,
    AnalyzedPlayerStats,
    AnalyzedTeamStats,
    Point,
    Roster,
    Video,
)
from open_hoops.stats.event_detector import EventDetector
from open_hoops.stats.movement import MovementTracker
from open_hoops.stats.passes import PassDetector
from open_hoops.stats.score import ScoreTracker
from open_hoops.tracking.sam2_tracker import SAM2Tracker, TrackedFrame, TrackedPlayer

TEAM_SAMPLE_FPS = 1
NUMBER_READ_INTERVAL = 10


class OpenHoop:
    def __init__(
        self,
        video: "Video",
        roster: "Roster | None" = None,
        logger: "LoggerProtocol | None" = None,
    ) -> None:
        self._video = video
        self._roster = roster
        self._logger: LoggerProtocol = logger or DefaultLogger(__name__)

    def extract_stats(self) -> "AnalysisResult":
        detector = RFDETRDetector()
        tracker = SAM2Tracker()
        court_mapper = CourtMapper()
        team_classifier = TeamClassifierWrapper()
        number_reader = NumberReader()
        number_validator = NumberValidator()
        event_detector = EventDetector()
        movement = MovementTracker()
        passes = PassDetector()
        score = ScoreTracker()

        video_info = sv.VideoInfo.from_video_path(self._video.path)
        fps = video_info.fps
        frames = list(sv.get_video_frames_generator(self._video.path))
        total_frames = len(frames)

        if total_frames == 0:
            return self._empty_result(fps)

        self._logger.info("Loaded %d frames at %.1f FPS", total_frames, fps)

        # Phase 1: Detect first frame, prompt SAM2, propagate tracking
        self._logger.info("Phase 1: Detection + SAM2 tracking")
        first_detections = detector.detect(frames[0])
        player_detections = detector.filter_players(first_detections)
        player_detections.tracker_id = np.arange(1, len(player_detections) + 1)
        self._logger.info("Detected %d players on first frame", len(player_detections))

        sam2_state = tracker.init_video(self._video.path)
        tracker.add_objects(sam2_state, frame_idx=0, detections=player_detections)
        self._logger.info("SAM2 propagating masks across %d frames...", total_frames)
        tracking_results = tracker.propagate(sam2_state, logger=self._logger)
        self._logger.info("SAM2 tracking complete")

        # Phase 2: Compute court homography from first frame
        self._logger.info("Phase 2: Court homography")
        homography_ok = court_mapper.compute_homography(frames[0])
        self._logger.info(
            "Court homography: %s", "OK" if homography_ok else "failed (using identity)"
        )

        # Phase 3: Collect team crops at 1 FPS for classifier training
        self._logger.info("Phase 3: Team classification")
        team_crops = self._collect_team_crops(frames, detector, tracking_results, fps)
        if team_crops:
            team_classifier.fit(team_crops)
            self._logger.info("Team classifier trained on %d crops", len(team_crops))

        # Phase 4: Process all frames
        team_assignments: dict[int, str] = {}
        jersey_assignments: dict[int, int | None] = {}
        all_events: list[AnalyzedEvent] = []
        tracked_frames: list[TrackedFrame] = []

        for frame_idx, frame in enumerate(frames):
            # Detection
            detections = detector.detect(frame)

            # Tracking — use pre-computed SAM2 results
            tracked = tracking_results.get(frame_idx, sv.Detections.empty())

            # Court mapping
            if tracked.tracker_id is not None and len(tracked) > 0:
                centers = np.array(
                    [[(xyxy[0] + xyxy[2]) / 2, (xyxy[1] + xyxy[3]) / 2] for xyxy in tracked.xyxy]
                )
                court_positions = court_mapper.pixel_to_court(centers)
            else:
                court_positions = np.empty((0, 2))

            # Build TrackedFrame
            tf = TrackedFrame(frame_idx=frame_idx)
            if tracked.tracker_id is not None:
                for i, tid in enumerate(tracked.tracker_id):
                    tid_int = int(tid)
                    court_pos = (float(court_positions[i, 0]), float(court_positions[i, 1]))
                    bbox = tuple(int(v) for v in tracked.xyxy[i])
                    tf.players.append(
                        TrackedPlayer(
                            track_id=tid_int,
                            bbox=bbox,
                            court_pos=court_pos,
                        )
                    )

            tracked_frames.append(tf)

            # Team assignment (once per player)
            if tracked.tracker_id is not None and tracked.mask is not None:
                for i, tid in enumerate(tracked.tracker_id):
                    tid_int = int(tid)
                    if tid_int not in team_assignments:
                        mask = tracked.mask[i]
                        crop = self._crop_from_mask(frame, mask, tracked.xyxy[i])
                        if crop is not None:
                            cluster = team_classifier.predict(crop)
                            team_assignments[tid_int] = "team_a" if cluster == 0 else "team_b"

            # Number reading
            if frame_idx % NUMBER_READ_INTERVAL == 0:
                number_dets = detector.filter_numbers(detections)
                if len(number_dets) > 0:
                    readings = number_reader.read(frame, number_dets)
                    self._match_numbers_to_players(
                        readings, number_dets, tracked, number_validator, jersey_assignments
                    )

            # Event detection
            frame_events = event_detector.update(detections, team_assignments, frame_idx, fps)

            # Pass detection (still proximity-based with better data)
            ball_dets = detector.filter_ball(detections)
            ball_pos = None
            if len(ball_dets) > 0:
                ball_center = np.array(
                    [
                        [
                            (ball_dets.xyxy[0][0] + ball_dets.xyxy[0][2]) / 2,
                            (ball_dets.xyxy[0][1] + ball_dets.xyxy[0][3]) / 2,
                        ]
                    ]
                )
                ball_court = court_mapper.pixel_to_court(ball_center)
                ball_pos = (float(ball_court[0, 0]), float(ball_court[0, 1]))
                tf.ball_pos = ball_pos

            shot_this_frame = any(e.type == "shot" for e in frame_events)
            possession_owner = None
            if tf.players and ball_pos:
                nearest = min(
                    tf.players,
                    key=lambda p: hypot(p.court_pos[0] - ball_pos[0], p.court_pos[1] - ball_pos[1]),
                )
                possession_owner = nearest.track_id

            pass_events = passes.update(
                tf, team_assignments, possession_owner, frame_idx, fps, shot_this_frame
            )

            # Movement
            movement.update(tf)

            # Score
            score.update(frame_events)

            all_events.extend(frame_events + pass_events)

        return self._build_result(
            fps,
            total_frames,
            team_assignments,
            jersey_assignments,
            movement,
            score,
            all_events,
            tracked_frames,
        )

    def _collect_team_crops(
        self,
        frames,
        detector,
        tracking_results: dict[int, sv.Detections],
        fps,
    ) -> list[np.ndarray]:
        crops = []
        interval = max(1, int(fps / TEAM_SAMPLE_FPS))
        for i in range(0, min(len(frames), int(fps * 10)), interval):
            frame = frames[i]
            tracked = tracking_results.get(i)
            if tracked is not None and tracked.mask is not None:
                for j in range(len(tracked)):
                    crop = self._crop_from_mask(frame, tracked.mask[j], tracked.xyxy[j])
                    if crop is not None:
                        crops.append(crop)
            else:
                detections = detector.detect(frame)
                players = detector.filter_players(detections)
                for xyxy in players.xyxy:
                    crop = self._central_crop(frame, xyxy)
                    if crop is not None:
                        crops.append(crop)
        return crops

    def _central_crop(self, frame: np.ndarray, xyxy: np.ndarray) -> "np.ndarray | None":
        x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
        h = y2 - y1
        cy1 = y1 + h // 4
        cy2 = y2 - h // 4
        crop = frame[cy1:cy2, x1:x2]
        return crop if crop.size > 0 else None

    def _crop_from_mask(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        xyxy: np.ndarray,
    ) -> "np.ndarray | None":
        x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
        h = y2 - y1
        cy1 = y1 + h // 4
        cy2 = y2 - h // 4
        crop = frame[cy1:cy2, x1:x2].copy()
        crop_mask = mask[cy1:cy2, x1:x2]
        if crop.size == 0:
            return None
        crop[~crop_mask] = 0
        return crop

    def _match_numbers_to_players(
        self,
        readings: dict[int, "str | None"],
        number_dets: sv.Detections,
        player_dets: sv.Detections,
        validator: "NumberValidator",
        jersey_assignments: dict[int, "int | None"],
    ) -> None:
        if player_dets.tracker_id is None:
            return
        for det_idx, number_str in readings.items():
            if number_str is None:
                continue
            # IoS matching: find player whose bbox contains this number bbox
            num_box = number_dets.xyxy[det_idx]
            best_player_tid = None
            best_ios = 0.0
            for p_idx, p_box in enumerate(player_dets.xyxy):
                ios = self._intersection_over_smaller(num_box, p_box)
                if ios > best_ios:
                    best_ios = ios
                    best_player_tid = int(player_dets.tracker_id[p_idx])
            if best_player_tid is not None and best_ios > 0.5:
                locked = validator.update(best_player_tid, number_str)
                if locked is not None:
                    jersey_assignments[best_player_tid] = locked

    def _intersection_over_smaller(self, box_a: np.ndarray, box_b: np.ndarray) -> float:
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        intersection = (x2 - x1) * (y2 - y1)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        smaller = min(area_a, area_b)
        return intersection / smaller if smaller > 0 else 0.0

    def _build_result(
        self,
        fps: float,
        total_frames: int,
        team_assignments: dict[int, str],
        jersey_assignments: dict[int, "int | None"],
        movement: "MovementTracker",
        score: "ScoreTracker",
        events: "list[AnalyzedEvent]",
        tracked_frames: "list[TrackedFrame]",
    ) -> "AnalysisResult":
        # Compute possession percentage from events
        poss_frames: dict[str, int] = {"team_a": 0, "team_b": 0}
        current_team = None
        for tf in tracked_frames:
            for e in events:
                if e.frame == tf.frame_idx and e.type == "possession_change":
                    current_team = e.team_id
            if current_team:
                poss_frames[current_team] = poss_frames.get(current_team, 0) + 1

        total_poss = sum(poss_frames.values())
        poss_pct = {k: v / total_poss if total_poss > 0 else 0.0 for k, v in poss_frames.items()}

        # Build per-player stats
        shot_attempts: dict[int, int] = {}
        shot_makes: dict[int, int] = {}
        passes_made: dict[int, int] = {}

        for e in events:
            pid = e.player_id
            if pid is None:
                continue
            if e.type == "shot":
                shot_attempts[pid] = shot_attempts.get(pid, 0) + 1
            elif e.type == "make":
                shot_makes[pid] = shot_makes.get(pid, 0) + 1
            elif e.type == "pass":
                passes_made[pid] = passes_made.get(pid, 0) + 1

        teams: dict[str, AnalyzedTeamStats] = {
            "team_a": AnalyzedTeamStats(
                team_id="team_a",
                score=score.scores.get("team_a", 0),
                possession_pct=poss_pct.get("team_a", 0.0),
            ),
            "team_b": AnalyzedTeamStats(
                team_id="team_b",
                score=score.scores.get("team_b", 0),
                possession_pct=poss_pct.get("team_b", 0.0),
            ),
        }

        for tid, team_id in team_assignments.items():
            jersey = jersey_assignments.get(tid)
            positions = [Point(x=x, y=y) for x, y in movement.get_positions(tid)]
            ps = AnalyzedPlayerStats(
                player_id=jersey,
                team_id=team_id,
                positions=positions,
                distance_covered_m=movement.get_distance(tid),
                shot_attempts=shot_attempts.get(tid, 0),
                shot_makes=shot_makes.get(tid, 0),
                passes_made=passes_made.get(tid, 0),
                passes_received=0,
                possession_frames=0,
            )
            if team_id in teams:
                teams[team_id].players.append(ps)

        return AnalysisResult(
            video=self._video,
            duration_seconds=total_frames / fps if fps > 0 else 0.0,
            fps=fps,
            teams=list(teams.values()),
            events=events,
            substitutions=[],
        )

    def _empty_result(self, fps: float) -> "AnalysisResult":
        return AnalysisResult(
            video=self._video,
            duration_seconds=0.0,
            fps=fps,
        )
