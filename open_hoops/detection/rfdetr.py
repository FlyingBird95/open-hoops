import numpy as np
import supervision as sv
from inference import get_model

BALL_CLASS_ID = 0
BALL_IN_BASKET_CLASS_ID = 1
NUMBER_CLASS_ID = 2
PLAYER_IN_POSSESSION_CLASS_ID = 4
PLAYER_JUMP_SHOT_CLASS_ID = 5
PLAYER_LAYUP_DUNK_CLASS_ID = 6
PLAYER_SHOT_BLOCK_CLASS_ID = 7
PLAYER_CLASS_IDS = [3, 4, 5, 6, 7]

MODEL_ID = "basketball-player-detection-3-ycjdo/4"
DEFAULT_CONFIDENCE = 0.4
DEFAULT_IOU_THRESHOLD = 0.9


class RFDETRDetector:
    def __init__(
        self,
        model_id: str = MODEL_ID,
        confidence: float = DEFAULT_CONFIDENCE,
        iou_threshold: float = DEFAULT_IOU_THRESHOLD,
    ) -> None:
        self._model = get_model(model_id=model_id)
        self._confidence = confidence
        self._iou_threshold = iou_threshold

    def detect(self, frame: np.ndarray) -> sv.Detections:
        result = self._model.infer(
            frame,
            confidence=self._confidence,
            iou_threshold=self._iou_threshold,
        )[0]
        return sv.Detections.from_inference(result)

    def filter_players(self, detections: sv.Detections) -> sv.Detections:
        return detections[np.isin(detections.class_id, PLAYER_CLASS_IDS)]

    def filter_numbers(self, detections: sv.Detections) -> sv.Detections:
        return detections[detections.class_id == NUMBER_CLASS_ID]

    def filter_ball(self, detections: sv.Detections) -> sv.Detections:
        return detections[detections.class_id == BALL_CLASS_ID]
