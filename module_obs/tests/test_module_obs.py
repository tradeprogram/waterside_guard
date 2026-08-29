import os

import pytest

import module_obs.run as module_obs_run
from module_obs.run import run

YONGIN_POLYGON_4326 = {
    "type": "Polygon",
    "coordinates": [
        [
            [127.203, 37.251],
            [127.218, 37.251],
            [127.218, 37.268],
            [127.203, 37.268],
            [127.203, 37.251],
        ]
    ],
}


@pytest.fixture(autouse=True)
def _reset_ee_init_cache():
    """모듈 레벨 `_ee_initialized` 캐시가 테스트 간에 새지 않도록 매 테스트 전후로 리셋한다."""
    module_obs_run._ee_initialized = False
    yield
    module_obs_run._ee_initialized = False


def test_missing_input_fields_returns_degraded_envelope():
    result = run({"aoi_id": "YONGIN_YUBANG"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_missing_project_id_returns_degraded_envelope_with_empty_scenes(monkeypatch):
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)

    result = run(
        {
            "aoi_id": "YONGIN_YUBANG",
            "date_range": ["2026-06-01", "2026-08-25"],
            "aoi_geometry_4326": YONGIN_POLYGON_4326,
        }
    )

    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3
    assert result["data"]["scenes"] == []
    assert any("GEE_PROJECT_ID" in w for w in result["warnings"])


@pytest.mark.skipif(
    not os.environ.get("GEE_PROJECT_ID"),
    reason="GEE_PROJECT_ID 없이는 실제 Earth Engine 왕복 테스트를 건너뜀 — 프로젝트 ID 확보 후 로컬에서 수동 실행",
)
def test_live_fetch_returns_scenes_when_credentials_present():
    result = run(
        {
            "aoi_id": "YONGIN_YUBANG",
            "date_range": ["2026-06-01", "2026-08-25"],
            "aoi_geometry_4326": YONGIN_POLYGON_4326,
        }
    )
    assert result["status"] in ("ok", "degraded")
    assert result["fallback_tier"] in (1, 2)
