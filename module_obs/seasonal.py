"""동일 계절 다년 기준선 조회 — ARCHITECTURE.md §5 Module OBS 확장(2026-08-31).

**왜 필요한가**: 지금까지 변화탐지는 "기준기간(2024 여름) 평균 vs 현재기간(2026 여름) 평균"
단순 차분이었다. 이 방식은 심사에서 가장 흔한 공격을 못 막는다 —
*"작년 6월 녹음기와 올해 4월을 비교하면 NDVI가 떨어지는 게 당연한 것 아닌가?"*
설령 우리처럼 같은 계절끼리 비교하더라도, **그 해가 유난히 가물었는지 습했는지**를
구분할 기준이 없으면 "정상 범위를 벗어났다"고 말할 수 없다.

**해결**: 같은 계절(현재 관측일 기준 ±`WINDOW_DAYS`)의 **과거 여러 해**를 모아
median과 MAD(median absolute deviation)를 구한다. 그러면 현재값을
*"지난 N년 같은 시기의 정상 범위에서 몇 배나 벗어났는가"*로 말할 수 있다.

BFAST/CCDC처럼 trend·seasonal 성분을 분해하는 정식 시계열 모형은 쓰지 않는다 —
중간점검 리서치가 "한 달 기회비용이 너무 크고 Ground Truth 부재를 해결하지 못한다"고
명시적으로 권고한 대로, 그 문제의식(계절성 통제)만 경량으로 반영한다.

median/MAD를 쓰는 이유는 평균/표준편차보다 이상치에 강해서다 — 과거 3년 중 한 해에
구름 낀 장면이 섞여도 기준선이 통째로 흔들리지 않는다.
"""
from __future__ import annotations

import datetime as dt

from common.envelope import error_envelope, make_envelope
from module_obs.run import (
    CLOUD_SCL_CLASSES,
    MAX_TILE_CLOUDY_PIXEL_PCT,
    REDUCE_SCALE_M,
    _init_ee,
)

WINDOW_DAYS = 20  # 현재 관측일 기준 ±이 일수를 "같은 계절"로 본다(초기 가정치)
DEFAULT_LOOKBACK_YEARS = 3  # 과거 몇 해를 기준선으로 쓸 것인가
MIN_YEARS_FOR_BASELINE = 2  # 유효 관측이 이 해 수 미만이면 기준선을 신뢰하지 않는다


def _season_window(as_of_date: str, year: int) -> tuple[str, str]:
    """as_of_date와 같은 월/일을 `year`에 대응시켜 ±WINDOW_DAYS 구간을 만든다."""
    base = dt.date.fromisoformat(as_of_date)
    # 2월 29일 같은 날짜가 평년에 없을 수 있어 하루 당겨서 안전하게 만든다.
    try:
        anchor = base.replace(year=year)
    except ValueError:
        anchor = base.replace(year=year, day=base.day - 1)
    return (
        (anchor - dt.timedelta(days=WINDOW_DAYS)).isoformat(),
        (anchor + dt.timedelta(days=WINDOW_DAYS)).isoformat(),
    )


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _mad(values: list[float], center: float) -> float | None:
    """Median Absolute Deviation — 표준편차보다 이상치에 강하다."""
    if not values:
        return None
    return _median([abs(v - center) for v in values])


def summarize_seasonal_baseline(yearly: list[dict]) -> dict:
    """연도별 관측치 목록 -> {historical_median, historical_mad, years_used}.

    순수 함수 — GEE를 부르지 않으므로 테스트에서 그대로 쓸 수 있다.
    """
    values = [y["ndvi_median"] for y in yearly if y.get("ndvi_median") is not None]
    median = _median(values)
    return {
        "yearly": yearly,
        "historical_median": round(median, 4) if median is not None else None,
        "historical_mad": round(_mad(values, median), 4) if median is not None else None,
        "years_used": len(values),
    }


def fetch_seasonal_baseline_batch(
    sites: list[dict], as_of_date: str, lookback_years: int = DEFAULT_LOOKBACK_YEARS
) -> dict:
    """sites: [{"site_id", "geometry_4326"}] -> {site_id: summarize_seasonal_baseline(...)}

    연도마다 `reduceRegions` 한 번씩만 부른다 — site 수와 무관하게 왕복이 연도 수에만
    비례한다(§ module_obs/batch.py와 같은 배치 패턴).
    """
    empty = {s["site_id"]: summarize_seasonal_baseline([]) for s in sites}
    if not sites or not as_of_date:
        return error_envelope("sites/as_of_date가 필요합니다.", fallback_tier=3)

    init_error = _init_ee()
    if init_error:
        return make_envelope(
            {"seasonal_baseline_by_site": empty}, status="degraded", fallback_tier=3, warnings=[init_error]
        )

    try:
        import ee

        features = [ee.Feature(ee.Geometry(s["geometry_4326"]), {"site_id": s["site_id"]}) for s in sites]
        fc = ee.FeatureCollection(features)

        current_year = dt.date.fromisoformat(as_of_date).year
        yearly_by_site: dict[str, list[dict]] = {s["site_id"]: [] for s in sites}

        for year in range(current_year - lookback_years, current_year):
            start, end = _season_window(as_of_date, year)
            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(fc.geometry())
                .filterDate(start, end)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_TILE_CLOUDY_PIXEL_PCT))
            )
            scene_count = collection.size().getInfo()
            if scene_count == 0:
                for sid in yearly_by_site:
                    yearly_by_site[sid].append({"year": year, "ndvi_median": None, "scene_count": 0})
                continue

            def mask_and_ndvi(img: "ee.Image") -> "ee.Image":  # noqa: F821
                scl = img.select("SCL")
                valid = scl.remap(CLOUD_SCL_CLASSES, [0] * len(CLOUD_SCL_CLASSES), defaultValue=1)
                return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(valid)

            # 그 해 같은 계절 창 전체를 median 합성 — 구름 낀 장면이 섞여도 중앙값이 흡수한다.
            composite = collection.map(mask_and_ndvi).median()
            reduced = composite.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=REDUCE_SCALE_M)
            for feat in reduced.getInfo()["features"]:
                props = feat["properties"]
                sid = props.get("site_id")
                # 단일 밴드 + reduceRegions -> 컬럼명이 밴드명이 아니라 reducer 출력명("mean")
                # (§ module_obs/batch.py SAR 배치에서 실측 확인된 함정)
                value = props.get("mean")
                if sid in yearly_by_site:
                    yearly_by_site[sid].append(
                        {"year": year, "ndvi_median": round(value, 4) if value is not None else None, "scene_count": scene_count}
                    )
    except Exception as e:  # noqa: BLE001 — 모듈 경계에서는 모든 예외를 degraded로 흡수(§4.2)
        return make_envelope(
            {"seasonal_baseline_by_site": empty},
            status="degraded",
            fallback_tier=2,
            warnings=[f"계절 기준선 조회 실패: {e}"],
        )

    result = {sid: summarize_seasonal_baseline(yearly) for sid, yearly in yearly_by_site.items()}
    thin = [sid for sid, r in result.items() if r["years_used"] < MIN_YEARS_FOR_BASELINE]
    warnings = (
        [f"{len(thin)}개 site는 유효 관측 연도가 {MIN_YEARS_FOR_BASELINE}년 미만이라 계절 기준선을 신뢰할 수 없음"]
        if thin
        else []
    )
    return make_envelope(
        {"seasonal_baseline_by_site": result},
        status="ok" if not warnings else "degraded",
        fallback_tier=1 if not warnings else 2,
        warnings=warnings,
    )
