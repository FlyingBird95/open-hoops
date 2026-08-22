"""Tests for open_hoops.training.train."""

from pathlib import Path
from unittest.mock import MagicMock, patch


@patch("open_hoops.training.train.YOLO")
def test_train_returns_best_model_path(mock_yolo_cls, tmp_path):
    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    weights_dir = tmp_path / "runs" / "detect" / "basketball-yolo11x" / "weights"
    weights_dir.mkdir(parents=True)
    best_pt = weights_dir / "best.pt"
    best_pt.write_bytes(b"fake model")

    mock_results = MagicMock()
    mock_results.save_dir = str(weights_dir.parent)
    mock_model.train.return_value = mock_results

    from open_hoops.training.train import train

    result = train(tmp_path, base_model="yolo11x.pt", epochs=10, imgsz=640)

    assert result == best_pt
    mock_yolo_cls.assert_called_once_with("yolo11x.pt")
    mock_model.train.assert_called_once()
    call_kwargs = mock_model.train.call_args.kwargs
    assert call_kwargs["epochs"] == 10
    assert call_kwargs["imgsz"] == 640


@patch("open_hoops.training.train.YOLO")
def test_train_uses_data_yaml(mock_yolo_cls, tmp_path):
    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    mock_results = MagicMock()
    mock_results.save_dir = str(tmp_path)
    mock_model.train.return_value = mock_results
    (tmp_path / "weights").mkdir()
    (tmp_path / "weights" / "best.pt").write_bytes(b"x")

    from open_hoops.training.train import train

    train(tmp_path, epochs=5)

    call_kwargs = mock_model.train.call_args.kwargs
    assert call_kwargs["data"] == str(tmp_path / "data.yaml")


def test_download_dataset():
    import sys

    mock_roboflow = MagicMock()
    sys.modules["roboflow"] = mock_roboflow

    mock_rf = MagicMock()
    mock_roboflow.Roboflow.return_value = mock_rf
    mock_project = MagicMock()
    mock_rf.workspace.return_value.project.return_value = mock_project
    mock_ds = MagicMock()
    mock_ds.location = "/tmp/dataset"
    mock_project.version.return_value.download.return_value = mock_ds

    try:
        from open_hoops.training.train import download_dataset

        result = download_dataset("key123", "ws", "proj", 1, Path("/tmp/dest"))

        assert result == Path("/tmp/dataset")
        mock_roboflow.Roboflow.assert_called_once_with(api_key="key123")
        mock_project.version.assert_called_once_with(1)
        mock_project.version.return_value.download.assert_called_once_with(
            "yolov8", location="/tmp/dest"
        )
    finally:
        del sys.modules["roboflow"]
