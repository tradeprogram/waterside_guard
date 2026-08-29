"""Module AGENT가 호출하는 tool 함수 — 전부 이미 계산된 값을 store에서 읽기만
한다. 새 숫자를 계산하지 않는다(§0.4 "위험도를 계산하지 않는다"를 Agent에도
동일 적용). Gemini function calling이 이 함수들의 시그니처·docstring에서
스키마를 추론하므로 타입 힌트와 docstring을 정확히 유지할 것.
"""
from __future__ import annotations

from module_o.store import store


def get_risk_evidence(site_id: str) -> dict:
    """이 대상지의 현재 위험점수·등급·근거 요인(contributing_factors)을 반환한다."""
    entry = store.get(site_id)
    if entry is None:
        return {"error": f"site '{site_id}' not found"}
    return {
        "site_id": site_id,
        "risk_score": entry.get("risk_score"),
        "risk_tier": entry.get("risk_tier"),
        "contributing_factors": entry.get("contributing_factors", []),
        "anomaly_score": entry.get("anomaly_score"),
        "change_type_hint": entry.get("change_type_hint"),
    }


def get_timeseries_summary(site_id: str) -> dict:
    """이 대상지의 기준기간(2024)·현재기간(2026) 위성 관측치(날짜별 NDVI/NDMI)를 반환한다."""
    entry = store.get(site_id)
    if entry is None:
        return {"error": f"site '{site_id}' not found"}
    return {
        "site_id": site_id,
        "baseline_scenes": entry.get("baseline_scenes", []),
        "current_scenes": entry.get("current_scenes", []),
    }


def get_inspection_history(site_id: str) -> dict:
    """이 대상지의 과거 현장점검 이력(날짜·이상발견 여부·메모)을 반환한다."""
    entry = store.get(site_id)
    if entry is None:
        return {"error": f"site '{site_id}' not found"}
    return {"site_id": site_id, "inspections": entry.get("inspections", [])}


def get_weekly_summary() -> dict:
    """전체 대상지 현황 요약 — 총 대상지 수, 고위험(1·2순위) 수, 현장점검 완료 수,
    실제 이상이 확인된 점검 건수를 반환한다."""
    entries = store.all()
    high_risk = [e for e in entries if e.get("risk_tier") in ("1순위", "2순위")]
    inspected = [e for e in entries if e.get("inspections")]
    confirmed = [
        e for e in inspected if any(i.get("actual_anomaly_found") for i in e["inspections"])
    ]
    return {
        "total_sites": len(entries),
        "high_risk_count": len(high_risk),
        "inspected_count": len(inspected),
        "confirmed_anomaly_count": len(confirmed),
    }


TOOL_FUNCTIONS = [get_risk_evidence, get_timeseries_summary, get_inspection_history]
