"""Module RISK — 현장점검 우선순위 산정 (ARCHITECTURE.md §5·§6 Module RISK).

1단계 규칙기반 baseline만 구현한다 — DNN은 물론 LightGBM도 아직 쓰지 않는다
(§6 "처음부터 DNN을 사용할 필요가 없다"). label(Module FIELD의 실제 현장
결과)이 충분히 쌓이면 2단계로 ML ranking을 얹는다.

**이 점수는 "환경 위험 확률"이 아니다**(2026-08-31 명칭 정리). `inspection_priority_score`는
0~100으로 정규화된 **운영상 ranking 값**이지, "82점 = 훼손 확률 82%"처럼 통계적으로
calibration된 값이 아니다. 중간점검 리서치(§ Red-Team "82점이면 82% 위험인가?")가
지적한 대로, `risk_score`라는 이름을 쓰면 확률적·과학적 의미를 요구받게 되므로
`inspection_priority_score`(현장점검 우선순위 점수)로 바꿨다.

**결측 요인 처리(2026-08-31 수정)**: `features`의 값이 `None`이면(Module AGG가
site_attributes를 못 채운 경우, §5 Module AGG 참조) 그 요인을 빼고 **남은 가중치를
재정규화**한다. 예전에는 재정규화 없이 그냥 더해서, KECI 내부 DB 접근이 안 되는
필지는 실제 위험과 무관하게 구조적으로 낮은 점수를 받았다(실측: 결측 3개면 4개
요인이 전부 만점이어도 65점이 천장 — 60개 site 전부 1순위가 안 나오던 원인).
대신 `weight_coverage`로 "몇 %의 근거로 계산된 점수인지"를 항상 함께 노출해,
재정규화로 점수가 올라간 사실을 숨기지 않는다(§9 불확실성 표기 원칙).
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope

# ARCHITECTURE.md §5 Module RISK의 산출식 — 초기 가정 가중치.
# Backtest B(§10)에서 baseline 대비 성능을 보고 재조정할 것.
WEIGHTS = {
    "anomaly_score_mean": 0.30,
    "changed_area_ratio": 0.15,
    "sar_anomaly_mean": 0.10,  # 이미 0~1 정규화됨(Module CHG) — 광학 이상도의 보조 근거
    "recent_rainfall_mm": 0.10,  # min(value/50, 1.0)로 정규화
    "last_inspection_days_ago": 0.15,  # min(value/180, 1.0)로 정규화
    "adjacent_to_water": 0.10,  # bool -> 0|1
    "past_anomaly_count": 0.10,  # min(value/3, 1.0)로 정규화
}

TIER_THRESHOLDS = [
    (70, "1순위"),
    (50, "2순위"),
    (30, "3순위"),
]


def _normalize(factor: str, value) -> float | None:
    if value is None:
        return None
    if factor == "anomaly_score_mean":
        return max(0.0, min(float(value), 1.0))
    if factor == "changed_area_ratio":
        return max(0.0, min(float(value), 1.0))
    if factor == "sar_anomaly_mean":
        return max(0.0, min(float(value), 1.0))
    if factor == "recent_rainfall_mm":
        return min(float(value) / 50.0, 1.0)  # 최근 14일 누적강우 50mm 이상이면 최대치로 취급(초기 가정치)
    if factor == "last_inspection_days_ago":
        return min(float(value) / 180.0, 1.0)
    if factor == "adjacent_to_water":
        return 1.0 if bool(value) else 0.0
    if factor == "past_anomaly_count":
        return min(float(value) / 3.0, 1.0)
    raise ValueError(f"알 수 없는 factor: {factor}")


def _priority_tier(score: int) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "정상"


def run(input: dict) -> dict:
    site_id = input.get("site_id", "unknown")
    features = input.get("features")

    if features is None:
        return error_envelope(f"[{site_id}] features가 없어 우선순위를 산정할 수 없습니다.", fallback_tier=3)

    contributing_factors = []
    weighted_sum = 0.0
    available_weight = 0.0
    missing_factors = []

    for factor, weight in WEIGHTS.items():
        raw_value = features.get(factor)
        normalized = _normalize(factor, raw_value)
        if normalized is None:
            missing_factors.append(factor)
            continue
        weighted_sum += weight * normalized
        available_weight += weight
        contributing_factors.append({"factor": factor, "value": raw_value, "weight": weight})

    # 결측 요인의 가중치를 빼고 남은 것만으로 재정규화한다 — 그래야 "요인 4개가 전부
    # 만점인 필지"가 "요인 7개가 전부 만점인 필지"와 같은 100점을 받는다(§ 모듈 docstring).
    normalized_sum = (weighted_sum / available_weight) if available_weight > 0 else 0.0
    inspection_priority_score = round(100 * max(0.0, min(normalized_sum, 1.0)))
    contributing_factors.sort(key=lambda f: f["weight"], reverse=True)

    warnings = []
    if missing_factors:
        warnings.append(
            f"[{site_id}] 다음 요인이 없어 남은 가중치로 재정규화해 산정함"
            f"(weight_coverage={round(available_weight, 2)}): {missing_factors}"
        )

    return make_envelope(
        {
            "site_id": site_id,
            "inspection_priority_score": inspection_priority_score,
            "priority_tier": _priority_tier(inspection_priority_score),
            "contributing_factors": contributing_factors,
            # 이 점수가 전체 가중치 중 몇 %의 근거로 계산됐는지 — 재정규화로 점수가
            # 올라간 사실을 숨기지 않기 위해 항상 함께 노출한다(§9).
            "weight_coverage": round(available_weight, 2),
            "model_version": "rule_v1",
            "source": "rule_based",
        },
        status="ok" if not missing_factors else "degraded",
        fallback_tier=1 if not missing_factors else 2,
        warnings=warnings,
    )
