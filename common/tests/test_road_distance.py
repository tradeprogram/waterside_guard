from unittest.mock import Mock, patch

from common.road_distance import fetch_road_distance_matrix_m


@patch("common.road_distance.requests.get")
def test_returns_matrix_on_success(mock_get):
    mock_get.return_value = Mock(
        raise_for_status=lambda: None,
        json=lambda: {"code": "Ok", "distances": [[0, 39188.7], [49006.2, 0]]},
    )

    result = fetch_road_distance_matrix_m([(127.2095, 37.2622), (127.6081, 37.2325)])

    assert result == [[0, 39188.7], [49006.2, 0]]
    args, kwargs = mock_get.call_args
    assert "127.209500,37.262200;127.608100,37.232500" in args[0]


@patch("common.road_distance.requests.get")
def test_non_ok_code_returns_none(mock_get):
    mock_get.return_value = Mock(raise_for_status=lambda: None, json=lambda: {"code": "NoRoute"})

    assert fetch_road_distance_matrix_m([(127.0, 37.0), (128.0, 38.0)]) is None


@patch("common.road_distance.requests.get")
def test_null_cell_in_matrix_returns_none(mock_get):
    """일부 구간만 경로를 못 찾아도 전체를 포기한다 — 절반은 도로거리, 절반은
    직선거리인 뒤섞인 결과를 만들지 않기 위해서다."""
    mock_get.return_value = Mock(
        raise_for_status=lambda: None,
        json=lambda: {"code": "Ok", "distances": [[0, None], [None, 0]]},
    )

    assert fetch_road_distance_matrix_m([(127.0, 37.0), (128.0, 38.0)]) is None


@patch("common.road_distance.requests.get")
def test_network_failure_returns_none_not_exception(mock_get):
    mock_get.side_effect = ConnectionError("boom")

    assert fetch_road_distance_matrix_m([(127.0, 37.0), (128.0, 38.0)]) is None


def test_fewer_than_two_points_returns_none_without_request():
    assert fetch_road_distance_matrix_m([(127.0, 37.0)]) is None


def test_too_many_points_returns_none_without_request():
    assert fetch_road_distance_matrix_m([(127.0, 37.0)] * 101) is None
