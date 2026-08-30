"""Module CHG — 변화탐지 (ARCHITECTURE.md §5 Module CHG).

Module OBS를 baseline_period·current_period 두 번 호출해 NDVI/NDMI 평균의
계절 정규화 이상도를 계산한다. 종(種) 단위 판독은 하지 않는다 — "정상
계절패턴과 다른 변화가 있다/없다"까지만 말한다(ARCHITECTURE.md §3.4).

2026-08-30: `changed_area_ratio`가 원래는 scene 평균 지표의 이상도 크기로부터
근사한 값이었다(§12 로드맵 B급 확장 항목) — 이제 `module_obs/pixel_diff.py`의
실제 픽셀 단위 측정값(기준·현재 NDVI 합성을 픽셀별로 빼서 임계치 넘는 비율)을
우선 쓰고, 그 GEE 호출이 실패했을 때만 기존 근사치로 폴백한다. `changed_area_ratio_source`
필드로 어느 쪽인지 항상 구분해 표시한다 — 근사치를 실측인 것처럼 과장하지 않는다.

2026-08-30: Sentinel-1 SAR(`sar_vv_mean`, Module OBS가 제공)를 두 번째
독립 신호로 추가했다. 원 리서치(수상전략 리포트)의 "기술적 해자 1번:
Multisensor Fusion" 및 Top1 개념의 "핵심 기술: S1/S2 변화탐지"가 처음부터
요구한 신호인데 최초 구현에서 광학(NDVI/NDMI)만 넣고 빠뜨렸던 것을 보완한다.
**범위 제한**: SAR backscatter 변화로 "무엇이 바뀌었는지"(식생/토양/구조물)를
판독하지 않는다 — 그건 SCL 이상으로 도메인 지식이 필요한 해석이다(§ 리서치
"매우 중요한 범위 제한" 참조). 여기서는 딱 두 가지 역할만 준다: (1) 광학
관측이 아예 없을 때(구름) 대체 이상도 신호, (2) 광학 이상도와 나란히 보여주는
보조 근거(§ Evidence 표시용) — 판정 자체는 여전히 NDVI/NDMI 기준이다.
"""
from __future__ import annotations

import statistics

from common.envelope import error_envelope, make_envelope
from common.geo import geometry_5179_to_4326
from module_chg.confidence import compute_evidence_confidence
from module_obs.run import run as obs_run

ANOMALY_THRESHOLD_FOR_CHANGE = 0.15  # |z-score 정규화 편차|가 이 값 이상이면 "유의미한 변화"로 본다(초기 가정치)
SAR_VV_DELTA_NORMALIZATION_DB = 3.0  # |VV backscatter 변화|(dB)가 이 값이면 이상도 1.0으로 정규화(초기 가정치)
ROBUST_Z_NORMALIZATION = 3.0  # robust z-score가 이 값이면 이상도 1.0(3-sigma 관행, 초기 가정치)
# MAD 하한 — 단순히 0으로 나누는 걸 막는 값이 아니라 **센서 자체의 측정 노이즈**다.
# Sentinel-2 NDVI는 대기보정·BRDF·관측각 차이로 대략 ±0.02~0.05의 불확실성이 있어서,
# 그보다 미세한 차이를 "정상범위를 벗어났다"고 주장하면 과잉해석이 된다. 실측(용인 유방동)에서
# 동일계절 3년 MAD가 0.009까지 작게 나오는데, 이걸 그대로 쓰면 0.05 변화도 3.7-sigma가 돼
# 대부분의 site가 최대점으로 포화되고 우선순위 변별력이 사라진다(2026-08-31 확인).
MIN_MAD_FLOOR = 0.03


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


def _sar_anomaly(sar_vv_delta: float | None) -> float | None:
    if sar_vv_delta is None:
        return None
    return round(min(abs(sar_vv_delta) / SAR_VV_DELTA_NORMALIZATION_DB, 1.0), 3)


def compute_seasonal_anomaly(current_ndvi: float | None, seasonal_baseline: dict | None) -> dict | None:
    """현재 NDVI가 **같은 계절 과거 N년의 정상 범위**에서 얼마나 벗어났는지(robust z-score).

    기존 anomaly_score가 "기준기간 평균과 얼마나 다른가"였다면, 이건 "그 차이가 해마다
    있는 자연스러운 흔들림 범위 안인가, 밖인가"를 본다 — 계절성·연도별 기후 변동을
    통제하는 지점이다(§module_obs/seasonal.py).

    MAD 기반이라 과거 한 해가 이상해도 기준선이 통째로 흔들리지 않는다. 기준선 연도가
    부족하면(§MIN_YEARS_FOR_BASELINE) None을 반환해 호출부가 기존 방식으로 폴백하게 한다.
    """
    if current_ndvi is None or not seasonal_baseline:
        return None
    median = seasonal_baseline.get("historical_median")
    mad = seasonal_baseline.get("historical_mad")
    years_used = seasonal_baseline.get("years_used", 0)
    if median is None or mad is None or years_used < 2:
        return None

    # 1.4826은 정규분포에서 MAD를 표준편차로 환산하는 관행적 상수다.
    scale = max(1.4826 * mad, MIN_MAD_FLOOR)
    robust_z = (current_ndvi - median) / scale
    return {
        "robust_z": round(robust_z, 3),
        "seasonal_anomaly_score": round(min(abs(robust_z) / ROBUST_Z_NORMALIZATION, 1.0), 3),
        "historical_median": median,
        "historical_mad": mad,
        "years_used": years_used,
        "current_ndvi": round(current_ndvi, 4),
        # 화면이 연도별 점을 찍을 수 있게 원자료도 함께 넘긴다(§ui/SeasonalBaselineChart.tsx)
        "yearly": seasonal_baseline.get("yearly", []),
    }


def compute_change_from_scenes(
    baseline_scenes: list[dict],
    current_scenes: list[dict],
    baseline_sar_vv_mean: float | None = None,
    current_sar_vv_mean: float | None = None,
    real_changed_area_ratio: float | None = None,
    recent_rainfall_mm: float | None = None,
    seasonal_baseline: dict | None = None,
) -> dict | None:
    """순수 함수 — Module OBS가 이미 반환한 scene 리스트(+SAR 평균)만으로 anomaly_score
    등을 계산한다. OBS를 부르지 않는다. `run()`(단일 site)과 배치 파이프라인(`scripts/`)이
    이 함수를 공유해서 분류 임계치·정규화 상수가 두 곳에서 따로 놀지 않게 한다.

    광학(NDVI/NDMI) scene이 둘 다 있으면 그것을 판정 기준으로 쓰고, SAR는 근거로만
    같이 반환한다. 광학 scene이 하나라도 없는데 SAR 평균은 둘 다 있으면(구름으로 광학이
    전멸한 경우) SAR만으로 이상도를 근사한다 — 그래서 다른 신호들과 달리, scene이
    비어 있어도 SAR만 있으면 None을 반환하지 않는다(§ 모듈 docstring 2026-08-30).

    `real_changed_area_ratio`는 호출부가 `module_obs/pixel_diff.py`로 미리 계산해 넘기는
    실제 픽셀 단위 값이다(이 함수 자체는 여전히 GEE를 부르지 않는 순수 함수로 남긴다) —
    주어지면 그걸 쓰고, 없으면(GEE 실패 등) 기존 이상도 근사치로 폴백한다.

    `recent_rainfall_mm`은 증거 신뢰도 판정에만 쓴다(§module_chg/confidence.py) — 강우 직후의
    습윤 신호는 훼손이 아니라 기상 현상일 수 있으므로 신뢰도를 깎는 confounder로 취급한다.
    """
    has_optical = bool(baseline_scenes) and bool(current_scenes)

    sar_vv_delta = (
        (current_sar_vv_mean - baseline_sar_vv_mean)
        if (current_sar_vv_mean is not None and baseline_sar_vv_mean is not None)
        else None
    )
    sar_anomaly = _sar_anomaly(sar_vv_delta)

    if not has_optical:
        if sar_anomaly is None:
            return None
        changed_area_ratio = real_changed_area_ratio if real_changed_area_ratio is not None else sar_anomaly
        return {
            "anomaly_score": sar_anomaly,
            "changed_area_ratio": changed_area_ratio,
            "changed_area_ratio_source": "pixel_diff" if real_changed_area_ratio is not None else "approximated",
            "change_type_hint": "possible_change_sar_only",
            "source": "observed_sar_fallback",
            "anomaly_method": "sar_only",
            "seasonal_anomaly": None,
            "two_period_anomaly_score": None,
            "signal_variability": None,
            "evidence_confidence": compute_evidence_confidence(
                baseline_scenes,
                current_scenes,
                ndvi_delta=None,
                ndmi_delta=None,
                sar_vv_delta=sar_vv_delta,
                changed_area_ratio_source="pixel_diff" if real_changed_area_ratio is not None else "approximated",
                recent_rainfall_mm=recent_rainfall_mm,
            ),
            "sar_vv_delta": round(sar_vv_delta, 3),
            "sar_anomaly": sar_anomaly,
        }

    baseline_ndvi = _mean([s["indices"].get("ndvi_mean") for s in baseline_scenes])
    baseline_ndmi = _mean([s["indices"].get("ndmi_mean") for s in baseline_scenes])
    current_ndvi = _mean([s["indices"].get("ndvi_mean") for s in current_scenes])
    current_ndmi = _mean([s["indices"].get("ndmi_mean") for s in current_scenes])

    ndvi_delta = (current_ndvi - baseline_ndvi) if (current_ndvi is not None and baseline_ndvi is not None) else None
    ndmi_delta = (current_ndmi - baseline_ndmi) if (current_ndmi is not None and baseline_ndmi is not None) else None

    magnitude = max(abs(ndvi_delta or 0.0), abs(ndmi_delta or 0.0))
    two_period_score = round(min(magnitude / 0.5, 1.0), 3)  # 두 기간 차분 방식(계절 기준선이 없을 때의 폴백)

    # 계절 정합 기준선이 있으면 그쪽을 우선한다 — "지난 N년 같은 계절의 정상 범위를
    # 벗어났는가"가 "두 기간이 다른가"보다 훨씬 방어력이 높다(§compute_seasonal_anomaly).
    seasonal = compute_seasonal_anomaly(current_ndvi, seasonal_baseline)
    anomaly_score = seasonal["seasonal_anomaly_score"] if seasonal else two_period_score
    anomaly_method = "season_matched" if seasonal else "two_period_diff"
    approximated_ratio = round(min(magnitude / 0.3, 1.0), 3)  # scene 평균 이상도로부터의 근사치 — real_changed_area_ratio가 없을 때만 씀
    changed_area_ratio = round(real_changed_area_ratio, 4) if real_changed_area_ratio is not None else approximated_ratio

    # 통계적 신뢰구간이 아니라 "현재기간 장면들 사이의 흔들림 폭"이다 — 이름을
    # confidence_interval로 두면 95% CI냐는 공격을 받는다(2026-08-31 명칭 정리).
    ndvi_values = [s["indices"].get("ndvi_mean") for s in current_scenes if s["indices"].get("ndvi_mean") is not None]
    signal_variability: list[float] | None = None
    if len(ndvi_values) >= 2:
        stdev = statistics.pstdev(ndvi_values)
        signal_variability = [round(anomaly_score - stdev, 3), round(anomaly_score + stdev, 3)]

    return {
        "anomaly_score": anomaly_score,
        "changed_area_ratio": changed_area_ratio,
        "changed_area_ratio_source": "pixel_diff" if real_changed_area_ratio is not None else "approximated",
        "change_type_hint": _classify_change(ndvi_delta, ndmi_delta),
        "source": "observed",
        # 이상도를 어떤 방식으로 냈는지 항상 명시 — 계절 기준선 확보 여부에 따라 달라진다.
        "anomaly_method": anomaly_method,
        "seasonal_anomaly": seasonal,
        "two_period_anomaly_score": two_period_score,
        "signal_variability": signal_variability,
        "evidence_confidence": compute_evidence_confidence(
            baseline_scenes,
            current_scenes,
            ndvi_delta=ndvi_delta,
            ndmi_delta=ndmi_delta,
            sar_vv_delta=sar_vv_delta,
            changed_area_ratio_source="pixel_diff" if real_changed_area_ratio is not None else "approximated",
            recent_rainfall_mm=recent_rainfall_mm,
        ),
        "sar_vv_delta": round(sar_vv_delta, 3) if sar_vv_delta is not None else None,
        "sar_anomaly": sar_anomaly,
    }


def run(input: dict) -> dict:
    aoi_id = input.get("aoi_id", "unknown")
    site_geometry_5179 = input.get("site_geometry_5179")
    baseline_period = input.get("baseline_period")
    current_period = input.get("current_period")
    recent_rainfall_mm = input.get("recent_rainfall_mm")  # 선택 — 증거 신뢰도의 기상 confounder 판정용

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

    # 픽셀 단위 실측 — 실패해도(구름 등) None으로 남아 근사치 폴백이 자동으로 작동한다
    # (compute_change_from_scenes 참조). obs_run과 별개의 GEE 호출이라 여기서만 예외를 흡수한다.
    # module_obs.pixel_diff가 이 모듈의 ANOMALY_THRESHOLD_FOR_CHANGE를 참조하므로(순환 임포트
    # 방지) 함수 안에서만 지연 임포트한다.
    real_changed_area_ratio = None
    try:
        from module_obs.pixel_diff import compute_changed_area_ratio as pixel_diff_run

        real_changed_area_ratio = pixel_diff_run(geometry_4326, baseline_period, current_period)
    except Exception as e:  # noqa: BLE001
        warnings.append(f"[{aoi_id}] 픽셀 단위 변화면적 계산 실패, 근사치로 대체: {e}")

    # 동일 계절 과거 N년 기준선 — 호출부가 미리 넘겼으면 그걸 쓰고, 없으면 여기서 조회한다
    # (배치 파이프라인은 site 전체를 한 번에 받아 넘기므로 재조회하지 않는다).
    seasonal_baseline = input.get("seasonal_baseline")
    if seasonal_baseline is None:
        try:
            from module_obs.seasonal import fetch_seasonal_baseline_batch

            result = fetch_seasonal_baseline_batch(
                [{"site_id": aoi_id, "geometry_4326": geometry_4326}], as_of_date=current_period[1]
            )
            seasonal_baseline = result["data"]["seasonal_baseline_by_site"].get(aoi_id)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"[{aoi_id}] 계절 기준선 조회 실패, 두 기간 차분으로 대체: {e}")

    computed = compute_change_from_scenes(
        baseline_scenes,
        current_scenes,
        baseline_sar_vv_mean=baseline_obs["data"].get("sar_vv_mean"),
        current_sar_vv_mean=current_obs["data"].get("sar_vv_mean"),
        real_changed_area_ratio=real_changed_area_ratio,
        recent_rainfall_mm=recent_rainfall_mm,
        seasonal_baseline=seasonal_baseline,
    )
    if computed is None:
        warnings.append(f"[{aoi_id}] 기준기간 또는 현재기간에 유효 관측이 없어 변화탐지를 건너뜁니다.")
        return make_envelope(
            {
                "aoi_id": aoi_id,
                "anomaly_score": None,
                "changed_area_ratio": None,
                "changed_area_ratio_source": None,
                "change_type_hint": "no_significant_change",
                "source": "observed",
                "anomaly_method": None,
                "seasonal_anomaly": None,
                "two_period_anomaly_score": None,
                "signal_variability": None,
                "evidence_confidence": None,
                "sar_vv_delta": None,
                "sar_anomaly": None,
            },
            status="degraded",
            fallback_tier=2,
            warnings=warnings,
        )

    fallback_tier = min(baseline_obs["fallback_tier"], current_obs["fallback_tier"])
    status = "ok" if fallback_tier == 1 else "degraded"

    return make_envelope(
        {"aoi_id": aoi_id, **computed},
        status=status,
        fallback_tier=fallback_tier,
        warnings=warnings,
    )
