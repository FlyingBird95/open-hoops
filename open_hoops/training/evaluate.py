"""Evaluate basketball YOLO model on test set.

Usage:
    python -m open_hoops.training.evaluate [--model basketball-yolo11x.pt]
"""

import argparse
from pathlib import Path

from ultralytics import YOLO


def evaluate(model_path: str, data_yaml: str) -> dict:
    """Run evaluation and return metrics."""
    model = YOLO(model_path)
    results = model.val(data=data_yaml)
    return {
        "mAP50": float(results.box.map50),
        "mAP50-95": float(results.box.map),
        "per_class": {
            name: float(results.box.maps[i]) for i, name in enumerate(results.names.values())
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate basketball YOLO model")
    parser.add_argument("--model", default="basketball-yolo11x.pt")
    parser.add_argument("--data", default=str(Path(__file__).parent / "dataset.yaml"))
    args = parser.parse_args()

    metrics = evaluate(args.model, args.data)
    print(f"mAP@50: {metrics['mAP50']:.3f}")
    print(f"mAP@50-95: {metrics['mAP50-95']:.3f}")
    print("Per-class mAP@50-95:")
    for cls, score in metrics["per_class"].items():
        print(f"  {cls}: {score:.3f}")


if __name__ == "__main__":
    main()
