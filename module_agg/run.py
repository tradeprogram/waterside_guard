"""Module AGG — GIS 공간 집계 (ARCHITECTURE.md §5 Module AGG).

Module CHG의 결과(들)와 관리대상지 속성(site_attributes)을 하나의 feature
벡터로 합친다. Module AGG 자신은 site_attributes를 계산하지 않는다 — 이건
계약상 입력으로 주어지는 값이다(§5). KECI 내부 자산 DB(복원경과일·점검이력
등)는 이 프로토타입에서 접근 불가하므로(개발_핸드오프_브리프 §2), 현재는
호출부가 알 수 있는 값만 채우고 나머지는 `None`으로 둔다 — Module RISK가
`None`을 "이 요인은 알 수 없음"으로 취급해 안전하게 처리한다(§4.2 graceful
degradation).
"""
from __future__ import annotations

import statistics

from common.envelope import error_envelope, make_envelope

SITE_ATTRIBUTE_KEYS = (
    "adjacent_to_water",
    "restoration_elapsed_days",
    "last_inspection_days_ago",
    "past_anomaly_count",
)


def run(input: dict) -> dict:
    site_id = input.get("site_id", "unknown")
    chg_results = input.get("chg_results")
    site_attributes = input.get("site_attributes") or {}

    if not chg_results:
        return error_envelope(f"[{site_id}] chg_results가 없어 집계할 수 없습니다.", fallback_tier=3)

    anomaly_scores = [r.get("anomaly_score") for r in chg_results if r.get("anomaly_score") is not None]
    changed_ratios = [r.get("changed_area_ratio") for r in chg_results if r.get("changed_area_ratio") is not None]

    warnings: list[str] = []
    if not anomaly_scores:
        warnings.append(f"[{site_id}] chg_results 전체에 anomaly_score가 없습니다.")
    if not changed_ratios:
        warnings.append(f"[{site_id}] chg_results 전체에 changed_area_ratio가 없습니다.")

    missing_attrs = [k for k in SITE_ATTRIBUTE_KEYS if k not in site_attributes]
    if missing_attrs:
        warnings.append(f"[{site_id}] site_attributes 누락: {missing_attrs} — Module RISK가 해당 요인을 0으로 처리합니다.")

    features = {
        "anomaly_score_mean": round(statistics.fmean(anomaly_scores), 4) if anomaly_scores else None,
        "changed_area_ratio": round(statistics.fmean(changed_ratios), 4) if changed_ratios else None,
        "adjacent_to_water": site_attributes.get("adjacent_to_water"),
        "restoration_elapsed_days": site_attributes.get("restoration_elapsed_days"),
        "last_inspection_days_ago": site_attributes.get("last_inspection_days_ago"),
        "past_anomaly_count": site_attributes.get("past_anomaly_count"),
    }

    status = "ok" if not warnings else "degraded"
    fallback_tier = 1 if not warnings else 2

    return make_envelope(
        {"site_id": site_id, "features": features},
        status=status,
        fallback_tier=fallback_tier,
        warnings=warnings,
    )
