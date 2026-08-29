"""Module RISK — 위험도 산정 (ARCHITECTURE.md §5·§6 Module RISK).

1단계 규칙기반 baseline만 구현한다 — DNN은 물론 LightGBM도 아직 쓰지 않는다
(§6 "처음부터 DNN을 사용할 필요가 없다"). label(Module FIELD의 실제 현장
결과)이 충분히 쌓이면 2단계로 ML ranking을 얹는다.

`features`의 값이 `None`(Module AGG가 site_attributes를 못 채운 경우, §5
Module AGG 참조)이면 해당 가중항은 0으로 처리하고 `contributing_factors`에서
빠진다 — 숫자를 지어내지 않는다는 원칙(§0.4)을 결측치에도 그대로 적용한다.
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope

# ARCHITECTURE.md §5 Module RISK의 risk_score 산출식 — 초기 가정 가중치.
# Backtest B(§10)에서 baseline 대비 성능을 보고 재조정할 것.
WEIGHTS = {
    "anomaly_score_mean": 0.35,
    "changed_area_ratio": 0.20,
    "last_inspection_days_ago": 0.15,  # min(value/180, 1.0)로 정규화
    "adjacent_to_water": 0.15,  # bool -> 0|1
    "past_anomaly_count": 0.15,  # min(value/3, 1.0)로 정규화
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
    if factor == "last_inspection_days_ago":
        return min(float(value) / 180.0, 1.0)
    if factor == "adjacent_to_water":
        return 1.0 if bool(value) else 0.0
    if factor == "past_anomaly_count":
        return min(float(value) / 3.0, 1.0)
    raise ValueError(f"알 수 없는 factor: {factor}")


def _risk_tier(score: int) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "정상"


def run(input: dict) -> dict:
    site_id = input.get("site_id", "unknown")
    features = input.get("features")

    if features is None:
        return error_envelope(f"[{site_id}] features가 없어 위험도를 산정할 수 없습니다.", fallback_tier=3)

    contributing_factors = []
    weighted_sum = 0.0
    missing_factors = []

    for factor, weight in WEIGHTS.items():
        raw_value = features.get(factor)
        normalized = _normalize(factor, raw_value)
        if normalized is None:
            missing_factors.append(factor)
            continue
        weighted_sum += weight * normalized
        contributing_factors.append({"factor": factor, "value": raw_value, "weight": weight})

    risk_score = round(100 * max(0.0, min(weighted_sum, 1.0)))
    contributing_factors.sort(key=lambda f: f["weight"], reverse=True)

    warnings = []
    if missing_factors:
        warnings.append(f"[{site_id}] 다음 요인이 없어 0으로 처리됨(risk_score가 과소평가될 수 있음): {missing_factors}")

    return make_envelope(
        {
            "site_id": site_id,
            "risk_score": risk_score,
            "risk_tier": _risk_tier(risk_score),
            "contributing_factors": contributing_factors,
            "model_version": "rule_v1",
            "source": "rule_based",
        },
        status="ok" if not missing_factors else "degraded",
        fallback_tier=1 if not missing_factors else 2,
        warnings=warnings,
    )
