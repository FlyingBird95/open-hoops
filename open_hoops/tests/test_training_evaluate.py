"""Tests for open_hoops.training.evaluate."""

from unittest.mock import MagicMock, patch

from open_hoops.training.evaluate import evaluate, main


@patch("open_hoops.training.evaluate.YOLO")
def test_evaluate_returns_metrics(mock_yolo_cls):
    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    mock_results = MagicMock()
    mock_results.box.map50 = 0.85
    mock_results.box.map = 0.72
    mock_results.box.maps = [0.9, 0.8, 0.6]
    mock_results.names = {0: "ball", 1: "player", 2: "hoop"}
    mock_model.val.return_value = mock_results

    metrics = evaluate("model.pt", "data.yaml")

    assert metrics["mAP50"] == 0.85
    assert metrics["mAP50-95"] == 0.72
    assert metrics["per_class"] == {"ball": 0.9, "player": 0.8, "hoop": 0.6}
    mock_yolo_cls.assert_called_once_with("model.pt")
    mock_model.val.assert_called_once_with(data="data.yaml")


@patch("open_hoops.training.evaluate.YOLO")
def test_evaluate_main(mock_yolo_cls, capsys):
    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    mock_results = MagicMock()
    mock_results.box.map50 = 0.75
    mock_results.box.map = 0.60
    mock_results.box.maps = [0.8]
    mock_results.names = {0: "ball"}
    mock_model.val.return_value = mock_results

    with patch("sys.argv", ["evaluate", "--model", "test.pt", "--data", "test.yaml"]):
        main()

    output = capsys.readouterr().out
    assert "0.750" in output
    assert "0.600" in output
