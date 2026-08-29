import os

import pytest

import module_obs.run as module_obs_run
from module_obs.thumbnail import run

SITE_GEOMETRY_4326 = {
    "type": "Polygon",
    "coordinates": [[[127.203, 37.251], [127.204, 37.251], [127.204, 37.252], [127.203, 37.252], [127.203, 37.251]]],
}


@pytest.fixture(autouse=True)
def _reset_ee_init_cache():
    module_obs_run._ee_initialized = False
    yield
    module_obs_run._ee_initialized = False


def test_missing_input_returns_degraded():
    result = run({"site_id": "A1037"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_missing_project_id_returns_degraded(monkeypatch):
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)
    result = run(
        {"site_id": "A1037", "aoi_geometry_4326": SITE_GEOMETRY_4326, "date_range": ["2026-06-01", "2026-06-20"]}
    )
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3
    assert result["data"]["thumbnail"] is None


@pytest.mark.skipif(
    not os.environ.get("GEE_PROJECT_ID"),
    reason="GEE_PROJECT_ID 없이는 실제 Earth Engine 썸네일 생성을 건너뜀 — 프로젝트 ID 확보 후 로컬에서 수동 실행",
)
def test_live_thumbnail_returns_fetchable_url():
    import requests

    result = run(
        {"site_id": "A1037", "aoi_geometry_4326": SITE_GEOMETRY_4326, "date_range": ["2026-06-01", "2026-06-20"]}
    )
    assert result["status"] == "ok"
    thumb = result["data"]["thumbnail"]
    assert thumb["url"].startswith("https://earthengine.googleapis.com/")
    assert len(thumb["image_coordinates"]) == 4
    assert thumb["acquisition_date"]

    # 생성된 URL이 실제로(별도 인증 없이) 이미지를 반환하는지 확인 — MapLibre <img>가 바로 쓸 수 있어야 함
    res = requests.get(thumb["url"], timeout=30)
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
