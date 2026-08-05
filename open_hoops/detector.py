from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    conf: float
    class_name: str
    track_id: int | None = None


@dataclass
class FrameDetections:
    players: list[Detection] = field(default_factory=list)
    ball: Detection | None = None
    hoops: list[Detection] = field(default_factory=list)


_CLASS_MAP = {
    "person": "player",
    "sports ball": "ball",
}


class Detector:
    def __init__(self, model_path: str = "yolo26x.pt") -> None:
        self._model = YOLO(model_path)

    def detect(self, frame: np.ndarray) -> FrameDetections:
        results = self._model.track(frame, persist=True, verbose=False)
        fd = FrameDetections()
        if not results:
            return fd
        r = results[0]
        boxes = r.boxes
        if boxes is None:
            return fd

        bboxes = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        track_ids = (
            boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(bboxes)
        )

        for bbox, conf, cls_id, tid in zip(bboxes, confs, classes, track_ids):
            raw_name = r.names[cls_id]
            name = _CLASS_MAP.get(raw_name, raw_name)
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            det = Detection(
                bbox=(x1, y1, x2, y2),
                conf=float(conf),
                class_name=name,
                track_id=int(tid) if (tid is not None and int(tid) != -1) else None,
            )
            if name == "player":
                fd.players.append(det)
            elif name == "ball":
                fd.ball = det
            elif name == "hoop":
                fd.hoops.append(det)
            else:
                print(name)

        return fd
