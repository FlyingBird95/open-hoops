import numpy as np
import torch
from sports import TeamClassifier


def _get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class TeamClassifierWrapper:
    def __init__(self, device: str | None = None) -> None:
        self._classifier = TeamClassifier(device=device or _get_device())

    def fit(self, crops: list[np.ndarray]) -> None:
        self._classifier.fit(crops)

    def predict(self, crop: np.ndarray) -> int:
        return self._classifier.predict(crop)

    def predict_batch(self, crops: list[np.ndarray]) -> list[int]:
        return [self._classifier.predict(crop) for crop in crops]
