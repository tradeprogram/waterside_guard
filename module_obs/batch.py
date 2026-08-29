"""Module OBS — 배치 관측 조회 (다중 AOI 성능 최적화, §12 로드맵 B급 확장).

`run.py`의 단일 AOI 계약(§5 Module OBS)은 그대로 둔다 — 이 파일은 같은
결과를 "여러 site를 한 번에" 훨씬 적은 Earth Engine 왕복으로 얻기 위한
별도 진입점이다.

**왜 필요한가**: `run.py` 방식은 site마다 개별 `reduceRegion` +
`aggregate_array` 4회 호출이라, site가 많아지면(예: 한강유역 5,526필지)
왕복 수가 site 수에 비례해 폭증한다 — 82필지 전체를 이 방식으로 돌리면
Earth Engine 호출만 수백~수천 번이 된다. 이 파일은
`Image.reduceRegions(collection=<여러 site의 FeatureCollection>)`를
이미지(관측 장면)마다 한 번씩만 호출하고 `.flatten()`으로 합쳐 **전체를
단일 `getInfo()` 호출**로 가져온다 — 왕복 횟수가 site 수가 아니라 이미지
수에만 비례한다(site 100개든 1000개든 이미지가 3장이면 여전히 호출 3+1번).
"""
from __future__ import annotations

from typing import Any

from common.envelope import error_envelope, make_envelope
from module_obs.run import (
    CLOUD_SCL_CLASSES,
    MAX_TILE_CLOUDY_PIXEL_PCT,
    MIN_AOI_VALID_RATIO,
    REDUCE_SCALE_M,
    _init_ee,
)


def _fetch_batch_timeseries(sites: list[dict], date_range: list[str]) -> dict[str, list[dict[str, Any]]]:
    import ee

    features = [ee.Feature(ee.Geometry(s["geometry_4326"]), {"site_id": s["site_id"]}) for s in sites]
    fc = ee.FeatureCollection(features)

    # 단일 AOI 버전(run.py)과 동일한 이유로 넓은 예비필터만 걸고, 실제 채택 기준은
    # site별 valid_ratio(MIN_AOI_VALID_RATIO)로 판단한다.
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(fc.geometry())
        .filterDate(date_range[0], date_range[1])
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_TILE_CLOUDY_PIXEL_PCT))
    )

    def per_image(img: "ee.Image"):
        scl = img.select("SCL")
        valid_mask = scl.remap(CLOUD_SCL_CLASSES, [0] * len(CLOUD_SCL_CLASSES), defaultValue=1)
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(valid_mask)
        ndmi = img.normalizedDifference(["B8", "B11"]).rename("ndmi").updateMask(valid_mask)
        combined = ndvi.addBands(ndmi).addBands(valid_mask.rename("valid"))
        reduced = combined.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=REDUCE_SCALE_M)
        return reduced.map(lambda f: f.set("acq_date", img.date().format("YYYY-MM-dd")))

    if collection.size().getInfo() == 0:
        return {s["site_id"]: [] for s in sites}

    triplets = collection.map(per_image).flatten()
    info = triplets.getInfo()

    results: dict[str, list[dict[str, Any]]] = {s["site_id"]: [] for s in sites}
    for feat in info["features"]:
        props = feat["properties"]
        site_id = props.get("site_id")
        valid_ratio = props.get("valid")
        if site_id not in results or valid_ratio is None or valid_ratio < MIN_AOI_VALID_RATIO:
            continue
        ndvi_mean = props.get("ndvi")
        ndmi_mean = props.get("ndmi")
        results[site_id].append(
            {
                "source": "sentinel2",
                "acquisition_date": props.get("acq_date"),
                "cloud_cover_pct": round((1 - valid_ratio) * 100, 1),
                "indices": {
                    "ndvi_mean": round(ndvi_mean, 4) if ndvi_mean is not None else None,
                    "ndmi_mean": round(ndmi_mean, 4) if ndmi_mean is not None else None,
                },
            }
        )

    for scenes in results.values():
        scenes.sort(key=lambda s: s["acquisition_date"])
    return results


def _fetch_batch_sar_vv_mean(sites: list[dict], date_range: list[str]) -> dict[str, float | None]:
    """`run.py`의 `_fetch_sar_vv_mean`을 여러 site에 대해 한 번에 처리하는 배치 버전.
    기간 전체를 mean composite 하나로 합성한 뒤 site들을 한 번의 `reduceRegions`로
    처리하므로, `_fetch_batch_timeseries`처럼 이미지 수만큼 반복할 필요조차 없다
    (Sentinel-2 시계열보다도 가볍다)."""
    import ee

    features = [ee.Feature(ee.Geometry(s["geometry_4326"]), {"site_id": s["site_id"]}) for s in sites]
    fc = ee.FeatureCollection(features)

    collection = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(fc.geometry())
        .filterDate(date_range[0], date_range[1])
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .select("VV")
    )

    results: dict[str, float | None] = {s["site_id"]: None for s in sites}
    if collection.size().getInfo() == 0:
        return results

    # 밴드가 하나뿐인 이미지를 reduceRegions하면 출력 컬럼명이 밴드명("VV")이 아니라
    # reducer 기본 출력명인 "mean"이 된다(다중 밴드였던 S2 배치 조회와 다른 부분 —
    # 실측으로 확인, 2026-08-30: 처음엔 "VV"로 읽어서 전부 None이 나왔었다).
    reduced = collection.mean().reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=REDUCE_SCALE_M)
    for feat in reduced.getInfo()["features"]:
        props = feat["properties"]
        site_id = props.get("site_id")
        vv_mean = props.get("mean")
        if site_id in results and vv_mean is not None:
            results[site_id] = round(vv_mean, 3)
    return results


def run_batch_sar(input: dict) -> dict:
    """input: {"sites": [{"site_id": str, "geometry_4326": GeoJSON geometry}], "date_range": [start, end]}
    output(data): {"sar_vv_mean_by_site": {site_id: float | None}}

    `run_batch`(Sentinel-2)과 완전히 독립된 진입점이다 — 구름으로 광학 관측이
    전멸해도 SAR는 살아있을 수 있다는 게 이 신호의 존재 이유라서, 실패를 같이
    묶으면 안 된다.
    """
    sites = input.get("sites")
    date_range = input.get("date_range")

    if not sites or not date_range:
        return error_envelope("sites/date_range가 필요합니다.", fallback_tier=3)

    init_error = _init_ee()
    if init_error:
        return make_envelope(
            {"sar_vv_mean_by_site": {s["site_id"]: None for s in sites}},
            status="degraded",
            fallback_tier=3,
            warnings=[init_error],
        )

    try:
        sar_vv_mean_by_site = _fetch_batch_sar_vv_mean(sites, date_range)
    except Exception as e:  # noqa: BLE001 — 모듈 경계에서는 모든 예외를 degraded로 흡수(§4.2)
        return make_envelope(
            {"sar_vv_mean_by_site": {s["site_id"]: None for s in sites}},
            status="degraded",
            fallback_tier=2,
            warnings=[f"Sentinel-1 SAR 배치 조회 실패: {e}"],
        )

    empty_sites = [sid for sid, v in sar_vv_mean_by_site.items() if v is None]
    warnings = (
        [f"{len(empty_sites)}개 site에 SAR 관측 없음: {empty_sites[:5]}{'...' if len(empty_sites) > 5 else ''}"]
        if empty_sites
        else []
    )

    return make_envelope(
        {"sar_vv_mean_by_site": sar_vv_mean_by_site},
        status="ok" if not warnings else "degraded",
        fallback_tier=1 if not warnings else 2,
        warnings=warnings,
    )


def run_batch(input: dict) -> dict:
    """input: {"sites": [{"site_id": str, "geometry_4326": GeoJSON geometry}], "date_range": [start, end]}
    output(data): {"scenes_by_site": {site_id: [scene, ...]}}
    """
    sites = input.get("sites")
    date_range = input.get("date_range")

    if not sites or not date_range:
        return error_envelope("sites/date_range가 필요합니다.", fallback_tier=3)

    init_error = _init_ee()
    if init_error:
        return make_envelope(
            {"scenes_by_site": {s["site_id"]: [] for s in sites}},
            status="degraded",
            fallback_tier=3,
            warnings=[init_error],
        )

    try:
        scenes_by_site = _fetch_batch_timeseries(sites, date_range)
    except Exception as e:  # noqa: BLE001 — 모듈 경계에서는 모든 예외를 degraded로 흡수(§4.2)
        return error_envelope(f"Earth Engine 배치 조회 실패: {e}", fallback_tier=2)

    empty_sites = [sid for sid, scenes in scenes_by_site.items() if not scenes]
    warnings = (
        [f"{len(empty_sites)}개 site에 유효 관측 없음: {empty_sites[:5]}{'...' if len(empty_sites) > 5 else ''}"]
        if empty_sites
        else []
    )

    return make_envelope(
        {"scenes_by_site": scenes_by_site},
        status="ok" if not warnings else "degraded",
        fallback_tier=1 if not warnings else 2,
        warnings=warnings,
    )
