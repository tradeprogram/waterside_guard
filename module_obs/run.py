"""Module OBS — 관측 수집·전처리 (ARCHITECTURE.md §5 Module OBS).

Google Earth Engine의 `COPERNICUS/S2_SR_HARMONIZED` 컬렉션을 서버 사이드에서
집계해 AOI 단위 NDVI/NDMI 시계열을 만든다. 픽셀 래스터를 로컬로 내려받지
않고 `reduceRegion` 결과(장면별 평균)만 받아오므로 대역폭 비용이 낮다.

2026-08-29: 원래 Sentinel Hub Statistical API로 구현했으나, 사용자가 이미
보유한 Google Earth Engine 접근권한을 쓰는 쪽으로 전환(Copernicus Data
Space Ecosystem 대안도 검토했으나 GEE로 확정). 자격증명(GEE_PROJECT_ID
등)이 없거나 초기화에 실패하면 예외를 던지지 않고 degraded envelope을
반환한다 — ARCHITECTURE.md §0.5 "AI가 실패해도 서비스가 작동하는 설계"
원칙을 코드로 강제하는 지점.
"""
from __future__ import annotations

import os
from typing import Any

from common.envelope import error_envelope, make_envelope

CLOUD_SCL_CLASSES = [3, 8, 9, 10]  # 구름그림자/구름(중)/구름(고)/씨러스 — 이 값들은 유효 관측에서 제외
MAX_CLOUDY_PIXEL_PCT = 30  # 타일 전체 구름 30% 이상인 장면은 조회 단계에서 제외
REDUCE_SCALE_M = 10  # Sentinel-2 10m 밴드 기준

_ee_initialized = False


def _init_ee() -> str | None:
    """Earth Engine을 초기화한다. 실패하면 사람이 읽을 에러 메시지를 반환, 성공하면 None."""
    global _ee_initialized
    if _ee_initialized:
        return None

    project_id = os.environ.get("GEE_PROJECT_ID")
    if not project_id:
        return "GEE_PROJECT_ID가 .env에 없습니다 — .env.example 참조 (Earth Engine은 등록된 Cloud 프로젝트 ID가 필수)."

    try:
        import ee
    except ImportError:
        return "earthengine-api 패키지가 설치되지 않았습니다 (pip install earthengine-api)."

    sa_email = os.environ.get("GEE_SERVICE_ACCOUNT_EMAIL")
    sa_key_path = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH")

    try:
        if sa_email and sa_key_path:
            credentials = ee.ServiceAccountCredentials(sa_email, sa_key_path)
            ee.Initialize(credentials, project=project_id)
        else:
            # 로컬에서 `earthengine authenticate`로 이미 캐시된 사용자 자격증명을 사용한다.
            ee.Initialize(project=project_id)
    except Exception as e:  # noqa: BLE001
        return f"Earth Engine 초기화 실패: {e}"

    _ee_initialized = True
    return None


def _fetch_ee_timeseries(geometry_4326: dict, date_range: list[str]) -> list[dict[str, Any]]:
    import ee

    geom = ee.Geometry(geometry_4326)

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geom)
        .filterDate(date_range[0], date_range[1])
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUDY_PIXEL_PCT))
    )

    def add_stats(img: "ee.Image") -> "ee.Image":
        scl = img.select("SCL")
        valid_mask = scl.remap(CLOUD_SCL_CLASSES, [0] * len(CLOUD_SCL_CLASSES), defaultValue=1)
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(valid_mask)
        ndmi = img.normalizedDifference(["B8", "B11"]).rename("ndmi").updateMask(valid_mask)
        combined = ndvi.addBands(ndmi).addBands(valid_mask.rename("valid"))

        stats = combined.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geom,
            scale=REDUCE_SCALE_M,
            maxPixels=1_000_000_000,
            bestEffort=True,
        )
        return img.set(
            {
                "acq_date": img.date().format("YYYY-MM-dd"),
                "ndvi_mean": stats.get("ndvi"),
                "ndmi_mean": stats.get("ndmi"),
                "valid_ratio": stats.get("valid"),
            }
        )

    mapped = collection.map(add_stats)

    if mapped.size().getInfo() == 0:
        return []

    # aggregate_array 4번으로 전체 시계열을 한 번에 서버에서 가져온다(장면 수만큼 개별 getInfo 호출하지 않음)
    dates = mapped.aggregate_array("acq_date").getInfo()
    ndvi_means = mapped.aggregate_array("ndvi_mean").getInfo()
    ndmi_means = mapped.aggregate_array("ndmi_mean").getInfo()
    valid_ratios = mapped.aggregate_array("valid_ratio").getInfo()

    scenes = []
    for acq_date, ndvi_mean, ndmi_mean, valid_ratio in zip(dates, ndvi_means, ndmi_means, valid_ratios):
        if valid_ratio is None:
            continue  # AOI 전체가 구름 등으로 마스킹된 장면
        scenes.append(
            {
                "source": "sentinel2",
                "acquisition_date": acq_date,
                "cloud_cover_pct": round((1 - valid_ratio) * 100, 1),
                "indices": {
                    "ndvi_mean": round(ndvi_mean, 4) if ndvi_mean is not None else None,
                    "ndmi_mean": round(ndmi_mean, 4) if ndmi_mean is not None else None,
                },
            }
        )
    return scenes


def run(input: dict) -> dict:
    aoi_id = input.get("aoi_id", "unknown")
    date_range = input.get("date_range")
    geometry_4326 = input.get("aoi_geometry_4326")

    if not date_range or not geometry_4326:
        return error_envelope(
            f"[{aoi_id}] date_range 또는 aoi_geometry_4326이 없어 관측을 조회할 수 없습니다.",
            fallback_tier=3,
        )

    init_error = _init_ee()
    if init_error:
        return make_envelope(
            {"aoi_id": aoi_id, "scenes": [], "composite_ref": None},
            status="degraded",
            fallback_tier=3,
            warnings=[init_error],
        )

    try:
        scenes = _fetch_ee_timeseries(geometry_4326, date_range)
    except Exception as e:  # noqa: BLE001 — 모듈 경계에서는 모든 예외를 degraded로 흡수한다 (ARCHITECTURE.md §4.2)
        return error_envelope(f"[{aoi_id}] Earth Engine 조회 실패: {e}", fallback_tier=2)

    if not scenes:
        return make_envelope(
            {"aoi_id": aoi_id, "scenes": [], "composite_ref": None},
            status="degraded",
            fallback_tier=2,
            warnings=[f"[{aoi_id}] {date_range} 구간에 유효한 장면이 없습니다(구름 등)."],
        )

    return make_envelope(
        {"aoi_id": aoi_id, "scenes": scenes, "composite_ref": None},
        status="ok",
        fallback_tier=1,
    )
