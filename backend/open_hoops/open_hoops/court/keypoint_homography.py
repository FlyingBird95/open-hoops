import numpy as np
from inference import get_model
from sports import ViewTransformer
from sports.basketball import CourtConfiguration, League

KEYPOINT_MODEL_ID = "basketball-court-detection-2/14"
DEFAULT_CONFIDENCE = 0.3
DEFAULT_ANCHOR_CONFIDENCE = 0.5


class CourtMapper:
    def __init__(
        self,
        model_id: str = KEYPOINT_MODEL_ID,
        confidence: float = DEFAULT_CONFIDENCE,
        anchor_confidence: float = DEFAULT_ANCHOR_CONFIDENCE,
        league: League = League.NBA,
    ) -> None:
        self._model = get_model(model_id=model_id)
        self._confidence = confidence
        self._anchor_confidence = anchor_confidence
        self._court_config = CourtConfiguration(league=league)
        self._view_transformer: ViewTransformer | None = None

    def _infer_keypoints(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run inference and return (xy, conf, mask).

        xy shape: (N, 2) — pixel coordinates for each keypoint
        conf shape: (N,) — confidence scores
        mask shape: (N,) — boolean mask for keypoints above anchor_confidence
        """
        result = self._model.infer(frame, confidence=self._confidence)[0]
        if not result.predictions:
            empty = np.empty((0, 2))
            return empty, np.empty(0), np.zeros(0, dtype=bool)
        keypoints = result.predictions[0].keypoints
        xy = np.array([[kp.x, kp.y] for kp in keypoints])
        conf = np.array([kp.confidence for kp in keypoints])
        mask = conf >= self._anchor_confidence
        return xy, conf, mask

    def detect_keypoints(self, frame: np.ndarray) -> np.ndarray:
        """Detect court keypoints in frame and return those above anchor confidence.

        Args:
            frame: BGR video frame as numpy array.

        Returns:
            Array of shape (K, 2) with pixel coordinates of detected keypoints,
            filtered to those whose confidence >= anchor_confidence.
        """
        xy, _conf, mask = self._infer_keypoints(frame)
        return xy[mask]

    def compute_homography(self, frame: np.ndarray) -> bool:
        """Detect keypoints and compute a homography to court coordinates.

        Uses the same confidence mask to align pixel keypoints with their
        known court positions from CourtConfiguration.vertices.

        Args:
            frame: BGR video frame as numpy array.

        Returns:
            True if a homography was computed (at least 4 keypoints found),
            False otherwise.
        """
        xy, _conf, mask = self._infer_keypoints(frame)
        pixel_points = xy[mask].astype(np.float32)

        if len(pixel_points) < 4:
            return False

        vertices = np.array(self._court_config.vertices, dtype=np.float32)
        court_points = vertices[mask]

        self._view_transformer = ViewTransformer(
            source=pixel_points,
            target=court_points,
        )
        return True

    def pixel_to_court(self, points: np.ndarray) -> np.ndarray:
        """Transform pixel coordinates to court coordinates.

        Args:
            points: Array of shape (N, 2) with pixel coordinates.

        Returns:
            Array of shape (N, 2) with court coordinates, or the original
            points if no homography has been computed yet.
        """
        if self._view_transformer is None:
            return points
        return self._view_transformer.transform_points(points)
