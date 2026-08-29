import os

import pytest

from module_obs.run import _bbox_from_geometry_4326, run

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


def test_bbox_from_geometry_4326():
    bbox = _bbox_from_geometry_4326(YONGIN_POLYGON_4326)
    assert bbox == (127.203, 37.251, 127.218, 37.268)


def test_missing_input_fields_returns_degraded_envelope():
    result = run({"aoi_id": "YONGIN_YUBANG"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3
    assert result["warnings"]


def test_missing_credentials_returns_degraded_envelope_with_empty_scenes(monkeypatch):
    monkeypatch.delenv("SENTINELHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("SENTINELHUB_CLIENT_SECRET", raising=False)

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
    assert any("SENTINELHUB_CLIENT_ID" in w for w in result["warnings"])


@pytest.mark.skipif(
    not os.environ.get("SENTINELHUB_CLIENT_ID"),
    reason="SENTINELHUB_CLIENT_ID/SECRET 없이는 실제 API 왕복 테스트를 건너뜀 — 자격증명 확보 후 로컬에서 수동 실행",
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
