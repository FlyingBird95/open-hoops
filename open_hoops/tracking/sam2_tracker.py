import enum
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
import supervision as sv
import torch
from sam2.build_sam import build_sam2_video_predictor

if TYPE_CHECKING:
    from open_hoops.core.logger.protocol import LoggerProtocol

_REPO_ROOT = Path(__file__).resolve().parents[2]
SAM2_CHECKPOINT = os.environ.get(
    "SAM2_CHECKPOINT", str(_REPO_ROOT / "checkpoints" / "sam2.1_hiera_large.pt")
)
SAM2_CONFIG = os.environ.get("SAM2_CONFIG", "configs/sam2.1/sam2.1_hiera_l.yaml")

_MPS_CACHE_CLEAR_INTERVAL = 50


class Device(str, enum.Enum):
    cuda = "cuda"
    mps = "mps"
    cpu = "cpu"


def _get_device() -> Device:
    if torch.cuda.is_available():
        return Device.cuda
    if torch.backends.mps.is_available():
        return Device.mps
    return Device.cpu


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
    """Batch video tracker using SAM2VideoPredictor.

    Usage:
        tracker = SAM2Tracker()
        state = tracker.init_video(video_path)
        tracker.add_objects(state, frame_idx=0, detections=player_dets)
        results = tracker.propagate(state)  # dict[frame_idx -> sv.Detections]
    """

    def __init__(self, checkpoint: str = SAM2_CHECKPOINT, config: str = SAM2_CONFIG) -> None:
        self._device: Device = _get_device()
        if self._device == Device.mps:
            os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
        self._predictor = build_sam2_video_predictor(config, checkpoint, device=self._device)

    def init_video(self, video_path: str) -> dict:
        frame_dir = self._extract_frames(video_path)
        with torch.inference_mode():
            state = self._predictor.init_state(video_path=frame_dir)
        state["_frame_dir"] = frame_dir
        return state

    def _extract_frames(self, video_path: str) -> str:
        frame_dir = tempfile.mkdtemp(prefix="sam2_frames_")
        cap = cv2.VideoCapture(video_path)
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imwrite(os.path.join(frame_dir, f"{idx:06d}.jpg"), frame)
            idx += 1
        cap.release()
        return frame_dir

    def add_objects(self, state: dict, frame_idx: int, detections: sv.Detections) -> None:
        if len(detections) == 0:
            return
        if detections.tracker_id is None:
            detections.tracker_id = np.arange(1, len(detections) + 1)

        with torch.inference_mode():
            for xyxy, obj_id in zip(detections.xyxy, detections.tracker_id):
                self._predictor.add_new_points_or_box(
                    inference_state=state,
                    frame_idx=frame_idx,
                    obj_id=int(obj_id),
                    box=xyxy,
                )

    def propagate(self, state: dict, logger: "LoggerProtocol") -> dict[int, sv.Detections]:
        results: dict[int, sv.Detections] = {}
        num_frames = state.get("num_frames", 0)

        with torch.inference_mode():
            for frame_idx, obj_ids, masks in self._predictor.propagate_in_video(state):
                mask_array = (masks > 0.0).cpu().numpy().squeeze(1)
                if mask_array.ndim == 2:
                    mask_array = mask_array[np.newaxis, ...]

                xyxy = sv.mask_to_xyxy(mask_array)
                results[frame_idx] = sv.Detections(
                    xyxy=xyxy,
                    mask=mask_array,
                    tracker_id=np.array(list(obj_ids), dtype=int),
                )

                if self._device == Device.mps and frame_idx % _MPS_CACHE_CLEAR_INTERVAL == 0:
                    torch.mps.empty_cache()

                if num_frames:
                    pct = int((frame_idx + 1) / num_frames * 100)
                    logger.info(
                        "SAM2 propagation: %d%% (%d/%d frames)", pct, frame_idx + 1, num_frames
                    )

        return results
