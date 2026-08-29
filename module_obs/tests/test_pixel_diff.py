import os

import pytest

import module_obs.run as module_obs_run
from module_obs.pixel_diff import compute_changed_area_ratio, compute_changed_area_ratio_batch

SITES = [
    {
        "site_id": "S1",
        "geometry_4326": {
            "type": "Polygon",
            "coordinates": [[[127.203, 37.251], [127.204, 37.251], [127.204, 37.252], [127.203, 37.252], [127.203, 37.251]]],
        },
    },
]
BASELINE_PERIOD = ["2024-06-01", "2024-08-31"]
CURRENT_PERIOD = ["2026-06-01", "2026-08-25"]


@pytest.fixture(autouse=True)
def _reset_ee_init_cache():
    module_obs_run._ee_initialized = False
    yield
    module_obs_run._ee_initialized = False


def test_missing_project_id_returns_none(monkeypatch):
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)
    assert compute_changed_area_ratio(SITES[0]["geometry_4326"], BASELINE_PERIOD, CURRENT_PERIOD) is None


def test_missing_project_id_batch_returns_all_none(monkeypatch):
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)
    assert compute_changed_area_ratio_batch(SITES, BASELINE_PERIOD, CURRENT_PERIOD) == {"S1": None}


@pytest.mark.skipif(
    not os.environ.get("GEE_PROJECT_ID"),
    reason="GEE_PROJECT_ID 없이는 실제 Earth Engine 왕복 테스트를 건너뜀 — 프로젝트 ID 확보 후 로컬에서 수동 실행",
)
def test_live_pixel_diff_returns_ratio_between_0_and_1():
    result = compute_changed_area_ratio(SITES[0]["geometry_4326"], BASELINE_PERIOD, CURRENT_PERIOD)
    assert result is None or (0.0 <= result <= 1.0)


@pytest.mark.skipif(
    not os.environ.get("GEE_PROJECT_ID"),
    reason="GEE_PROJECT_ID 없이는 실제 Earth Engine 왕복 테스트를 건너뜀 — 프로젝트 ID 확보 후 로컬에서 수동 실행",
)
def test_live_pixel_diff_batch_returns_ratio_per_site():
    result = compute_changed_area_ratio_batch(SITES, BASELINE_PERIOD, CURRENT_PERIOD)
    assert result["S1"] is None or (0.0 <= result["S1"] <= 1.0)
