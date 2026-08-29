import os

import pytest

import module_obs.run as module_obs_run
from module_obs.batch import run_batch

SITES = [
    {
        "site_id": "S1",
        "geometry_4326": {
            "type": "Polygon",
            "coordinates": [[[127.203, 37.251], [127.204, 37.251], [127.204, 37.252], [127.203, 37.252], [127.203, 37.251]]],
        },
    },
    {
        "site_id": "S2",
        "geometry_4326": {
            "type": "Polygon",
            "coordinates": [[[127.210, 37.258], [127.211, 37.258], [127.211, 37.259], [127.210, 37.259], [127.210, 37.258]]],
        },
    },
]


@pytest.fixture(autouse=True)
def _reset_ee_init_cache():
    module_obs_run._ee_initialized = False
    yield
    module_obs_run._ee_initialized = False


def test_missing_input_returns_degraded():
    result = run_batch({"sites": SITES})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_missing_project_id_returns_degraded_with_empty_scenes(monkeypatch):
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)
    result = run_batch({"sites": SITES, "date_range": ["2026-06-01", "2026-08-25"]})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3
    assert result["data"]["scenes_by_site"] == {"S1": [], "S2": []}


@pytest.mark.skipif(
    not os.environ.get("GEE_PROJECT_ID"),
    reason="GEE_PROJECT_ID 없이는 실제 Earth Engine 배치 왕복 테스트를 건너뜀 — 프로젝트 ID 확보 후 로컬에서 수동 실행",
)
def test_live_batch_fetch_returns_scenes_for_multiple_sites():
    result = run_batch({"sites": SITES, "date_range": ["2026-06-01", "2026-06-20"]})
    assert result["status"] in ("ok", "degraded")
    assert set(result["data"]["scenes_by_site"].keys()) == {"S1", "S2"}
    # 둘 다 유방동 근처 실제 좌표라 최소 하나의 site는 유효 관측이 있어야 한다
    assert any(result["data"]["scenes_by_site"].values())
