from unittest.mock import MagicMock, patch

import numpy as np

from open_hoops.identity.team_classifier import TeamClassifierWrapper


@patch("open_hoops.identity.team_classifier.TeamClassifier")
def test_fit_calls_underlying_classifier(mock_tc_class):
    mock_tc = MagicMock()
    mock_tc_class.return_value = mock_tc

    wrapper = TeamClassifierWrapper(device="cpu")
    crops = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(10)]
    wrapper.fit(crops)

    mock_tc.fit.assert_called_once_with(crops)


@patch("open_hoops.identity.team_classifier.TeamClassifier")
def test_predict_returns_team_id(mock_tc_class):
    mock_tc = MagicMock()
    mock_tc_class.return_value = mock_tc
    mock_tc.predict.return_value = 0

    wrapper = TeamClassifierWrapper(device="cpu")
    crop = np.zeros((64, 64, 3), dtype=np.uint8)
    result = wrapper.predict(crop)

    assert result in (0, 1)


@patch("open_hoops.identity.team_classifier.TeamClassifier")
def test_predict_batch(mock_tc_class):
    mock_tc = MagicMock()
    mock_tc_class.return_value = mock_tc
    mock_tc.predict.side_effect = [0, 1, 0]

    wrapper = TeamClassifierWrapper(device="cpu")
    crops = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(3)]
    results = wrapper.predict_batch(crops)

    assert results == [0, 1, 0]
