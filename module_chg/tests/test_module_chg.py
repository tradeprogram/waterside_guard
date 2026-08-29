from unittest.mock import patch

from module_chg.run import compute_change_from_scenes, run

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


def _obs_envelope(ndvi_mean: float, ndmi_mean: float, status="ok", fallback_tier=1, sar_vv_mean=None):
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
            "sar_vv_mean": sar_vv_mean,
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


@patch("module_chg.run.obs_run")
def test_sar_included_alongside_optical_when_both_available(mock_obs):
    # SAR는 광학 판정을 대체하지 않는다 — change_type_hint는 여전히 NDVI/NDMI 기준.
    mock_obs.side_effect = [
        _obs_envelope(ndvi_mean=0.70, ndmi_mean=0.30, sar_vv_mean=-12.0),
        _obs_envelope(ndvi_mean=0.40, ndmi_mean=0.28, sar_vv_mean=-9.5),
    ]

    result = run(
        {
            "aoi_id": "A1037",
            "site_geometry_5179": SITE_GEOMETRY_5179,
            "baseline_period": ["2024-06-01", "2024-08-31"],
            "current_period": ["2026-06-01", "2026-08-31"],
        }
    )

    assert result["data"]["change_type_hint"] == "vegetation_decline"  # 광학 기준 판정 그대로
    assert result["data"]["sar_vv_delta"] == 2.5
    assert result["data"]["sar_anomaly"] == round(min(2.5 / 3.0, 1.0), 3)


@patch("module_chg.run.obs_run")
def test_sar_only_fallback_when_optical_unavailable(mock_obs):
    # 구름으로 광학 scene이 전멸했지만(§module_obs 실측 사례) SAR는 all-weather라 살아있는 경우.
    cloudy = {
        "status": "degraded",
        "fallback_tier": 2,
        "data": {"scenes": [], "sar_vv_mean": None},
        "warnings": ["no optical scenes"],
    }
    cloudy_with_sar = dict(cloudy)
    cloudy_with_sar["data"] = {"scenes": [], "sar_vv_mean": -8.0}
    baseline = {**cloudy, "data": {"scenes": [], "sar_vv_mean": -12.0}}
    mock_obs.side_effect = [baseline, cloudy_with_sar]

    result = run(
        {
            "aoi_id": "A1037",
            "site_geometry_5179": SITE_GEOMETRY_5179,
            "baseline_period": ["2024-06-01", "2024-08-31"],
            "current_period": ["2026-06-01", "2026-08-31"],
        }
    )

    assert result["status"] == "degraded"  # SAR-only는 여전히 낮은 신뢰도로 표시
    assert result["data"]["change_type_hint"] == "possible_change_sar_only"
    assert result["data"]["source"] == "observed_sar_fallback"
    assert result["data"]["anomaly_score"] == round(min(4.0 / 3.0, 1.0), 3)


def test_compute_change_from_scenes_returns_none_when_nothing_available():
    assert compute_change_from_scenes([], [], baseline_sar_vv_mean=None, current_sar_vv_mean=None) is None


def test_real_changed_area_ratio_overrides_approximation():
    # 근사치(magnitude/0.3)와 다른 값을 넘겨서, 실제로 그 값이 쓰였는지(근사치가 아니라) 확인.
    result = compute_change_from_scenes(
        [{"indices": {"ndvi_mean": 0.70, "ndmi_mean": 0.30}}],
        [{"indices": {"ndvi_mean": 0.40, "ndmi_mean": 0.28}}],
        real_changed_area_ratio=0.123,
    )
    assert result["changed_area_ratio"] == 0.123
    assert result["changed_area_ratio_source"] == "pixel_diff"


def test_changed_area_ratio_falls_back_to_approximation_when_real_value_missing():
    result = compute_change_from_scenes(
        [{"indices": {"ndvi_mean": 0.70, "ndmi_mean": 0.30}}],
        [{"indices": {"ndvi_mean": 0.40, "ndmi_mean": 0.28}}],
    )
    assert result["changed_area_ratio_source"] == "approximated"
    assert result["changed_area_ratio"] == round(min(0.30 / 0.3, 1.0), 3)
