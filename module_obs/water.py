"""수체 인접 여부 — JRC Global Surface Water (ARCHITECTURE.md §5 Module AGG
"site_attributes" 중 `adjacent_to_water`).

이 값은 지금까지 항상 `None`이었다(KECI 내부 자산 DB 접근 불가, § Module AGG
구현 상태) — 그런데 "수변"을 이름에 단 시스템이 정작 수변 인접 여부를
못 채우고 있는 건 어색한 공백이고, 사실 공개 데이터(JRC Global Surface
Water, 위성 관측 기반 전세계 수체 이력 지도)로 직접 계산 가능하다.

`occurrence` 밴드(0~100, 1984~현재 Landsat 기록상 해당 픽셀이 물로 관측된
비율)를 쓴다 — 계절에 따라서만 물이 차는 곳(농업용 저류지 등)까지 "수체"로
잡고 싶어서 25%라는 비교적 낮은 문턱을 초기값으로 잡았다(강 본류 등은
occurrence가 보통 90% 이상이라 이 문턱에 민감하지 않다).
"""
from __future__ import annotations

from module_obs.run import REDUCE_SCALE_M, _init_ee

WATER_PROXIMITY_BUFFER_M = 150  # module_obs/thumbnail.py의 BUFFER_M과 동일 — "인접"의 기준 거리
WATER_OCCURRENCE_THRESHOLD_PCT = 25  # JRC occurrence(0~100) 최댓값이 이 이상이면 "인접 수체 있음"(초기 가정치)


def is_adjacent_to_water(geometry_4326: dict) -> bool | None:
    """단일 site. 실패/자격증명 없음 -> None(모른다는 뜻 — Module RISK가 0 기여로 안전 처리)."""
    if _init_ee():
        return None
    try:
        import ee

        geom = ee.Geometry(geometry_4326).buffer(WATER_PROXIMITY_BUFFER_M)
        occurrence = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")
        stats = occurrence.reduceRegion(
            reducer=ee.Reducer.max(), geometry=geom, scale=REDUCE_SCALE_M, bestEffort=True
        )
        max_occurrence = stats.get("occurrence").getInfo()
        return max_occurrence is not None and max_occurrence >= WATER_OCCURRENCE_THRESHOLD_PCT
    except Exception:  # noqa: BLE001 — 부가 신호, 실패해도 나머지 파이프라인에 영향 없음
        return None


def is_adjacent_to_water_batch(sites: list[dict]) -> dict[str, bool | None]:
    """sites: [{"site_id": str, "geometry_4326": geometry}]. 이미지 하나(JRC 정적 이미지)에
    reduceRegions 한 번만 써서 site 수와 무관하게 단일 `getInfo()` 호출로 끝낸다(§ module_obs/batch.py
    와 동일한 배치 패턴)."""
    results: dict[str, bool | None] = {s["site_id"]: None for s in sites}
    if _init_ee():
        return results
    try:
        import ee

        features = [
            ee.Feature(ee.Geometry(s["geometry_4326"]).buffer(WATER_PROXIMITY_BUFFER_M), {"site_id": s["site_id"]})
            for s in sites
        ]
        fc = ee.FeatureCollection(features)
        occurrence = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")
        reduced = occurrence.reduceRegions(collection=fc, reducer=ee.Reducer.max(), scale=REDUCE_SCALE_M)
        for feat in reduced.getInfo()["features"]:
            props = feat["properties"]
            site_id = props.get("site_id")
            # 단일 밴드 이미지를 reduceRegions하면 출력 컬럼명이 밴드명("occurrence")이 아니라
            # reducer 출력명("max")이 된다 — module_obs/batch.py의 SAR 배치 조회에서 실측으로
            # confirmed된 함정과 동일(2026-08-30).
            max_occurrence = props.get("max")
            if site_id in results:
                results[site_id] = max_occurrence is not None and max_occurrence >= WATER_OCCURRENCE_THRESHOLD_PCT
    except Exception:  # noqa: BLE001
        pass
    return results
