import numpy as np
from sports import TeamClassifier


class TeamClassifierWrapper:
    def __init__(self, device: str = "cuda") -> None:
        self._classifier = TeamClassifier(device=device)

    def fit(self, crops: list[np.ndarray]) -> None:
        self._classifier.fit(crops)

    def predict(self, crop: np.ndarray) -> int:
        return self._classifier.predict(crop)

    def predict_batch(self, crops: list[np.ndarray]) -> list[int]:
        return [self._classifier.predict(crop) for crop in crops]
