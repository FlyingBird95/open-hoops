"""Fine-tune YOLO11x on basketball detection data.

Usage:
    python -m open_hoops.training.train [--epochs 50] [--dataset-id ROBOFLOW_ID]

Requires:
    pip install roboflow
    ROBOFLOW_API_KEY environment variable set
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from ultralytics import YOLO


def download_dataset(api_key: str, workspace: str, project: str, version: int, dest: Path) -> Path:
    """Download dataset from Roboflow."""
    from roboflow import Roboflow

    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    ds = proj.version(version).download("yolov8", location=str(dest))
    return Path(ds.location)


def train(
    dataset_path: Path,
    base_model: str = "yolo11x.pt",
    epochs: int = 50,
    imgsz: int = 640,
    output_name: str = "basketball-yolo11x",
) -> Path:
    """Fine-tune YOLO on basketball dataset."""
    model = YOLO(base_model)

    results = model.train(
        data=str(dataset_path / "data.yaml"),
        epochs=epochs,
        imgsz=imgsz,
        name=output_name,
        patience=10,
        save=True,
        plots=True,
    )

    best_path = Path(results.save_dir) / "weights" / "best.pt"
    return best_path


def main():
    parser = argparse.ArgumentParser(description="Train basketball YOLO model")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--base-model", default="yolo11x.pt")
    parser.add_argument("--workspace", default="basketball-detection")
    parser.add_argument("--project", default="basketball-object-detection")
    parser.add_argument("--version", type=int, default=1)
    args = parser.parse_args()

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        print("Error: ROBOFLOW_API_KEY environment variable required")
        sys.exit(1)

    dest = Path(__file__).parent / "datasets" / "basketball"
    print(f"Downloading dataset to {dest}...")
    dataset_path = download_dataset(api_key, args.workspace, args.project, args.version, dest)

    print(f"Training for {args.epochs} epochs...")
    best = train(dataset_path, args.base_model, args.epochs, args.imgsz)

    # Copy best model to project root
    output_path = Path(__file__).parent.parent.parent / "basketball-yolo11x.pt"
    shutil.copy2(best, output_path)
    print(f"Model saved to {output_path}")


if __name__ == "__main__":
    main()
