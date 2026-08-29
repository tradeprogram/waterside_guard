"""실제 픽셀 단위 변화면적 비율 (ARCHITECTURE.md §5 Module CHG `changed_area_ratio`).

기존 `module_chg.compute_change_from_scenes()`의 `changed_area_ratio`는 scene
평균 NDVI/NDMI 이상도 "크기"로부터의 근사치였다(코드 주석에 이미 명시된
MVP 한계, §12 로드맵 B급 확장 항목). 이 모듈은 그 근사치를 진짜 측정값으로
바꾼다: 기준기간·현재기간 각각의 NDVI 합성(median composite)을 픽셀 단위로
빼서 |변화|가 임계치를 넘는 픽셀의 "이진 마스크"를 만들고, 그 마스크를
`reduceRegion(mean)`하면 — 마스크가 0/1이므로 평균 자체가 곧 "변화 픽셀
비율"이 된다. 이게 이 모듈의 유일한 트릭이다.

**범위 제한**: 여기서도 "무엇이 바뀌었는지"는 판독하지 않는다 — 임계치를
넘은 픽셀의 비율만 잰다(§3.4 종 판독 금지 원칙과 동일 선상).
"""
from __future__ import annotations

from module_chg.run import ANOMALY_THRESHOLD_FOR_CHANGE
from module_obs.run import CLOUD_SCL_CLASSES, MAX_TILE_CLOUDY_PIXEL_PCT, REDUCE_SCALE_M, _init_ee


def _ndvi_composite(collection: "ee.ImageCollection") -> "ee.Image":  # noqa: F821
    def mask_and_ndvi(img: "ee.Image") -> "ee.Image":  # noqa: F821
        scl = img.select("SCL")
        valid_mask = scl.remap(CLOUD_SCL_CLASSES, [0] * len(CLOUD_SCL_CLASSES), defaultValue=1)
        return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(valid_mask)

    return collection.map(mask_and_ndvi).median()


def compute_changed_area_ratio(
    geometry_4326: dict, baseline_period: list[str], current_period: list[str]
) -> float | None:
    """단일 site. 실패/자격증명 없음 -> None(호출부가 근사치로 폴백)."""
    if _init_ee():
        return None
    try:
        import ee

        geom = ee.Geometry(geometry_4326)

        def collection_for(date_range: list[str]) -> "ee.ImageCollection":
            return (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(geom)
                .filterDate(date_range[0], date_range[1])
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_TILE_CLOUDY_PIXEL_PCT))
            )

        baseline_ndvi = _ndvi_composite(collection_for(baseline_period))
        current_ndvi = _ndvi_composite(collection_for(current_period))
        changed_mask = current_ndvi.subtract(baseline_ndvi).abs().gt(ANOMALY_THRESHOLD_FOR_CHANGE).rename("changed")

        stats = changed_mask.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geom, scale=REDUCE_SCALE_M, bestEffort=True
        )
        value = stats.get("changed").getInfo()
        return round(value, 4) if value is not None else None
    except Exception:  # noqa: BLE001
        return None


def compute_changed_area_ratio_batch(
    sites: list[dict], baseline_period: list[str], current_period: list[str]
) -> dict[str, float | None]:
    """sites: [{"site_id": str, "geometry_4326": geometry}]. 합성 이미지 2장(기준·현재)만
    만들고 reduceRegions 한 번으로 전체 site를 처리한다 — site 수와 무관하게 EE 왕복이
    거의 고정(§ module_obs/batch.py와 동일한 배치 패턴)."""
    results: dict[str, float | None] = {s["site_id"]: None for s in sites}
    if _init_ee():
        return results
    try:
        import ee

        features = [ee.Feature(ee.Geometry(s["geometry_4326"]), {"site_id": s["site_id"]}) for s in sites]
        fc = ee.FeatureCollection(features)

        def collection_for(date_range: list[str]) -> "ee.ImageCollection":
            return (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(fc.geometry())
                .filterDate(date_range[0], date_range[1])
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_TILE_CLOUDY_PIXEL_PCT))
            )

        baseline_ndvi = _ndvi_composite(collection_for(baseline_period))
        current_ndvi = _ndvi_composite(collection_for(current_period))
        changed_mask = current_ndvi.subtract(baseline_ndvi).abs().gt(ANOMALY_THRESHOLD_FOR_CHANGE).rename("changed")

        reduced = changed_mask.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=REDUCE_SCALE_M)
        for feat in reduced.getInfo()["features"]:
            props = feat["properties"]
            site_id = props.get("site_id")
            # 단일 밴드 + reduceRegions -> 출력 컬럼명은 밴드명이 아니라 reducer 출력명("mean")
            # (실측 확인된 함정, § module_obs/batch.py SAR 배치 참조).
            value = props.get("mean")
            if site_id in results and value is not None:
                results[site_id] = round(value, 4)
    except Exception:  # noqa: BLE001
        pass
    return results
