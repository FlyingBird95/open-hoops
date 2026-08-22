import numpy as np
import supervision as sv
from inference import get_model

NUMBER_MODEL_ID = "basketball-jersey-numbers-ocr/3"
NUMBER_PROMPT = "Read the number."
CROP_PAD = 10


class NumberReader:
    def __init__(self, model_id: str = NUMBER_MODEL_ID) -> None:
        self._model = get_model(model_id=model_id)

    def read(self, frame: np.ndarray, detections: sv.Detections) -> dict[int, str | None]:
        results: dict[int, str | None] = {}
        h, w = frame.shape[:2]

        for idx, xyxy in enumerate(detections.xyxy):
            x1 = max(0, int(xyxy[0]) - CROP_PAD)
            y1 = max(0, int(xyxy[1]) - CROP_PAD)
            x2 = min(w, int(xyxy[2]) + CROP_PAD)
            y2 = min(h, int(xyxy[3]) + CROP_PAD)
            crop = frame[y1:y2, x1:x2]

            if crop.size == 0:
                results[idx] = None
                continue

            response = self._model.infer(crop, prompt=NUMBER_PROMPT)
            results[idx] = response.output if response.output else None

        return results


class NumberValidator:
    def __init__(self, threshold: int = 3) -> None:
        self._threshold = threshold
        self._streaks: dict[int, tuple[str, int]] = {}
        self._locked: dict[int, int] = {}

    def update(self, track_id: int, number_str: str | None) -> int | None:
        if track_id in self._locked:
            return self._locked[track_id]

        if number_str is None or not number_str.strip().isdigit():
            return None

        current = self._streaks.get(track_id)
        if current and current[0] == number_str:
            count = current[1] + 1
            self._streaks[track_id] = (number_str, count)
            if count >= self._threshold:
                self._locked[track_id] = int(number_str)
                return self._locked[track_id]
        else:
            self._streaks[track_id] = (number_str, 1)

        return None
