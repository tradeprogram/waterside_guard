"""Module CHG — 변화탐지 (ARCHITECTURE.md §5 Module CHG).

Module OBS를 baseline_period·current_period 두 번 호출해 NDVI/NDMI 평균의
계절 정규화 이상도를 계산한다. 종(種) 단위 판독은 하지 않는다 — "정상
계절패턴과 다른 변화가 있다/없다"까지만 말한다(ARCHITECTURE.md §3.4).

MVP 범위 제한 — `changed_area_ratio`는 아직 픽셀 단위 변화면적이 아니라
scene 평균 지표의 이상도 크기로부터 근사한 값이다(§12 로드맵 B급 확장에서
Earth Engine `reduceRegion` histogram 기반 픽셀 diff로 교체 예정). 이 근사를
code에 명시해 과장하지 않는다.
"""
from __future__ import annotations

import statistics

from common.envelope import error_envelope, make_envelope
from common.geo import geometry_5179_to_4326
from module_obs.run import run as obs_run

ANOMALY_THRESHOLD_FOR_CHANGE = 0.15  # |z-score 정규화 편차|가 이 값 이상이면 "유의미한 변화"로 본다(초기 가정치)


def _mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return statistics.fmean(vals) if vals else None


def _classify_change(ndvi_delta: float | None, ndmi_delta: float | None) -> str:
    """ndvi_delta/ndmi_delta = 현재기간 평균 - 기준기간 평균. 힌트일 뿐 확정 판정이 아님."""
    if ndvi_delta is None and ndmi_delta is None:
        return "no_significant_change"

    ndvi_delta = ndvi_delta or 0.0
    ndmi_delta = ndmi_delta or 0.0

    if abs(ndvi_delta) < ANOMALY_THRESHOLD_FOR_CHANGE and abs(ndmi_delta) < ANOMALY_THRESHOLD_FOR_CHANGE:
        return "no_significant_change"
    if ndvi_delta <= -ANOMALY_THRESHOLD_FOR_CHANGE and ndvi_delta <= ndmi_delta:
        return "vegetation_decline"
    if ndmi_delta >= ANOMALY_THRESHOLD_FOR_CHANGE:
        return "moisture_increase"
    return "bare_ground_increase"


def run(input: dict) -> dict:
    aoi_id = input.get("aoi_id", "unknown")
    site_geometry_5179 = input.get("site_geometry_5179")
    baseline_period = input.get("baseline_period")
    current_period = input.get("current_period")

    if not site_geometry_5179 or not baseline_period or not current_period:
        return error_envelope(
            f"[{aoi_id}] site_geometry_5179/baseline_period/current_period가 필요합니다.",
            fallback_tier=3,
        )

    try:
        geometry_4326 = geometry_5179_to_4326(site_geometry_5179)
    except Exception as e:  # noqa: BLE001
        return error_envelope(f"[{aoi_id}] geometry 재투영 실패: {e}", fallback_tier=3)

    baseline_obs = obs_run(
        {"aoi_id": aoi_id, "date_range": baseline_period, "aoi_geometry_4326": geometry_4326}
    )
    current_obs = obs_run(
        {"aoi_id": aoi_id, "date_range": current_period, "aoi_geometry_4326": geometry_4326}
    )

    warnings: list[str] = list(baseline_obs.get("warnings", [])) + list(current_obs.get("warnings", []))

    if baseline_obs["status"] == "error" or current_obs["status"] == "error":
        return error_envelope(f"[{aoi_id}] Module OBS 조회 실패 — {warnings}", fallback_tier=2)

    baseline_scenes = baseline_obs["data"].get("scenes", [])
    current_scenes = current_obs["data"].get("scenes", [])

    if not baseline_scenes or not current_scenes:
        warnings.append(f"[{aoi_id}] 기준기간 또는 현재기간에 유효 관측이 없어 변화탐지를 건너뜁니다.")
        return make_envelope(
            {
                "aoi_id": aoi_id,
                "anomaly_score": None,
                "changed_area_ratio": None,
                "change_type_hint": "no_significant_change",
                "source": "observed",
                "confidence_interval": None,
            },
            status="degraded",
            fallback_tier=2,
            warnings=warnings,
        )

    baseline_ndvi = _mean([s["indices"].get("ndvi_mean") for s in baseline_scenes])
    baseline_ndmi = _mean([s["indices"].get("ndmi_mean") for s in baseline_scenes])
    current_ndvi = _mean([s["indices"].get("ndvi_mean") for s in current_scenes])
    current_ndmi = _mean([s["indices"].get("ndmi_mean") for s in current_scenes])

    ndvi_delta = (current_ndvi - baseline_ndvi) if (current_ndvi is not None and baseline_ndvi is not None) else None
    ndmi_delta = (current_ndmi - baseline_ndmi) if (current_ndmi is not None and baseline_ndmi is not None) else None

    magnitude = max(abs(ndvi_delta or 0.0), abs(ndmi_delta or 0.0))
    anomaly_score = round(min(magnitude / 0.5, 1.0), 3)  # 0.5 편차를 사실상 최대치로 정규화(초기 가정치, Backtest A로 보정)
    changed_area_ratio = round(min(magnitude / 0.3, 1.0), 3)  # scene 평균 이상도로부터의 근사치 — 픽셀 단위 아님(위 docstring 참조)

    ndvi_values = [s["indices"].get("ndvi_mean") for s in current_scenes if s["indices"].get("ndvi_mean") is not None]
    ci: list[float] | None = None
    if len(ndvi_values) >= 2:
        stdev = statistics.pstdev(ndvi_values)
        ci = [round(anomaly_score - stdev, 3), round(anomaly_score + stdev, 3)]

    fallback_tier = min(baseline_obs["fallback_tier"], current_obs["fallback_tier"])
    status = "ok" if fallback_tier == 1 else "degraded"

    return make_envelope(
        {
            "aoi_id": aoi_id,
            "anomaly_score": anomaly_score,
            "changed_area_ratio": changed_area_ratio,
            "change_type_hint": _classify_change(ndvi_delta, ndmi_delta),
            "source": "observed",
            "confidence_interval": ci,
        },
        status=status,
        fallback_tier=fallback_tier,
        warnings=warnings,
    )
