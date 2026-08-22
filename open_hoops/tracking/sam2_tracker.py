from dataclasses import dataclass, field

import numpy as np
import supervision as sv
import torch
from sam2.build_sam import build_sam2_video_predictor as build_sam2_camera_predictor

SAM2_CHECKPOINT = "checkpoints/sam2.1_hiera_large.pt"
SAM2_CONFIG = "configs/sam2.1/sam2.1_hiera_l.yaml"


@dataclass
class TrackedPlayer:
    track_id: int
    bbox: tuple[int, int, int, int]
    court_pos: tuple[float, float] = (0.0, 0.0)
    mask: "np.ndarray | None" = None


@dataclass
class TrackedFrame:
    players: "list[TrackedPlayer]" = field(default_factory=list)
    ball_pos: "tuple[float, float] | None" = None
    frame_idx: int = 0


class SAM2Tracker:
    def __init__(
        self,
        checkpoint: str = SAM2_CHECKPOINT,
        config: str = SAM2_CONFIG,
    ) -> None:
        self._predictor = build_sam2_camera_predictor(config, checkpoint)
        self._prompted = False

    def prompt_first_frame(self, frame: np.ndarray, detections: sv.Detections) -> None:
        if len(detections) == 0:
            return
        if detections.tracker_id is None:
            detections.tracker_id = np.arange(1, len(detections) + 1)

        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            self._predictor.load_first_frame(frame)
            for xyxy, obj_id in zip(detections.xyxy, detections.tracker_id):
                bbox = np.asarray([xyxy], dtype=np.float32)
                self._predictor.add_new_prompt(
                    frame_idx=0,
                    obj_id=int(obj_id),
                    bbox=bbox,
                )
        self._prompted = True

    def track_frame(self, frame: np.ndarray) -> sv.Detections:
        if not self._prompted:
            return sv.Detections.empty()

        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            masks_by_id, _scores_by_id = self._predictor.track(frame)

        if not masks_by_id:
            return sv.Detections.empty()

        obj_ids = list(masks_by_id.keys())
        mask_array = np.stack([masks_by_id[oid] for oid in obj_ids]).astype(bool)
        xyxy = sv.mask_to_xyxy(mask_array)

        return sv.Detections(
            xyxy=xyxy,
            mask=mask_array,
            tracker_id=np.array(obj_ids, dtype=int),
        )

    def add_new_object(self, frame: np.ndarray, bbox: np.ndarray, obj_id: int) -> None:
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            self._predictor.add_new_prompt(
                frame_idx=0,
                obj_id=obj_id,
                bbox=np.asarray([bbox], dtype=np.float32),
            )
