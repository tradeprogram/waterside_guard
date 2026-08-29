from unittest.mock import patch

from module_chg.run import run

# 유방동 실제 필지 하나의 근사 사각형(EPSG:5179) — data/processed/yongin_yubang_parcels.geojson 범위 내
SITE_GEOMETRY_5179 = {
    "type": "Polygon",
    "coordinates": [
        [
            [974000.0, 1917500.0],
            [974100.0, 1917500.0],
            [974100.0, 1917600.0],
            [974000.0, 1917600.0],
            [974000.0, 1917500.0],
        ]
    ],
}


def _obs_envelope(ndvi_mean: float, ndmi_mean: float, status="ok", fallback_tier=1):
    return {
        "status": status,
        "fallback_tier": fallback_tier,
        "data": {
            "aoi_id": "A1037",
            "scenes": [
                {
                    "source": "sentinel2",
                    "acquisition_date": "2026-08-20",
                    "cloud_cover_pct": 5.0,
                    "indices": {"ndvi_mean": ndvi_mean, "ndmi_mean": ndmi_mean},
                }
            ],
            "composite_ref": None,
        },
        "warnings": [],
    }


def test_missing_fields_returns_degraded_envelope():
    result = run({"aoi_id": "A1037"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


@patch("module_chg.run.obs_run")
def test_vegetation_decline_detected(mock_obs):
    # baseline NDVI 0.70 -> current NDVI 0.40 : 뚜렷한 식생 감소
    mock_obs.side_effect = [
        _obs_envelope(ndvi_mean=0.70, ndmi_mean=0.30),
        _obs_envelope(ndvi_mean=0.40, ndmi_mean=0.28),
    ]

    result = run(
        {
            "aoi_id": "A1037",
            "site_geometry_5179": SITE_GEOMETRY_5179,
            "baseline_period": ["2024-06-01", "2024-08-31"],
            "current_period": ["2026-06-01", "2026-08-31"],
        }
    )

    assert result["status"] == "ok"
    assert result["data"]["change_type_hint"] == "vegetation_decline"
    assert result["data"]["anomaly_score"] > 0.3
    assert mock_obs.call_count == 2


@patch("module_chg.run.obs_run")
def test_no_significant_change(mock_obs):
    mock_obs.side_effect = [
        _obs_envelope(ndvi_mean=0.65, ndmi_mean=0.30),
        _obs_envelope(ndvi_mean=0.64, ndmi_mean=0.31),
    ]

    result = run(
        {
            "aoi_id": "A1037",
            "site_geometry_5179": SITE_GEOMETRY_5179,
            "baseline_period": ["2024-06-01", "2024-08-31"],
            "current_period": ["2026-06-01", "2026-08-31"],
        }
    )

    assert result["data"]["change_type_hint"] == "no_significant_change"


@patch("module_chg.run.obs_run")
def test_empty_scenes_returns_degraded(mock_obs):
    empty = {"status": "degraded", "fallback_tier": 2, "data": {"scenes": []}, "warnings": ["no scenes"]}
    mock_obs.side_effect = [empty, empty]

    result = run(
        {
            "aoi_id": "A1037",
            "site_geometry_5179": SITE_GEOMETRY_5179,
            "baseline_period": ["2024-06-01", "2024-08-31"],
            "current_period": ["2026-06-01", "2026-08-31"],
        }
    )

    assert result["status"] == "degraded"
    assert result["data"]["change_type_hint"] == "no_significant_change"
