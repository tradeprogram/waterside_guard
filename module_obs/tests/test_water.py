import os

import pytest

import module_obs.run as module_obs_run
from module_obs.water import is_adjacent_to_water, is_adjacent_to_water_batch

SITES = [
    {
        "site_id": "S1",
        "geometry_4326": {
            "type": "Polygon",
            "coordinates": [[[127.203, 37.251], [127.204, 37.251], [127.204, 37.252], [127.203, 37.252], [127.203, 37.251]]],
        },
    },
]


@pytest.fixture(autouse=True)
def _reset_ee_init_cache():
    module_obs_run._ee_initialized = False
    yield
    module_obs_run._ee_initialized = False


def test_missing_project_id_returns_none(monkeypatch):
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)
    assert is_adjacent_to_water(SITES[0]["geometry_4326"]) is None


def test_missing_project_id_batch_returns_all_none(monkeypatch):
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)
    assert is_adjacent_to_water_batch(SITES) == {"S1": None}


@pytest.mark.skipif(
    not os.environ.get("GEE_PROJECT_ID"),
    reason="GEE_PROJECT_ID 없이는 실제 Earth Engine 왕복 테스트를 건너뜀 — 프로젝트 ID 확보 후 로컬에서 수동 실행",
)
def test_live_water_check_returns_bool():
    result = is_adjacent_to_water(SITES[0]["geometry_4326"])
    assert result in (True, False)


@pytest.mark.skipif(
    not os.environ.get("GEE_PROJECT_ID"),
    reason="GEE_PROJECT_ID 없이는 실제 Earth Engine 왕복 테스트를 건너뜀 — 프로젝트 ID 확보 후 로컬에서 수동 실행",
)
def test_live_water_check_batch_returns_bool_per_site():
    result = is_adjacent_to_water_batch(SITES)
    assert result["S1"] in (True, False)
