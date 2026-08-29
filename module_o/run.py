"""Module O — 오케스트레이션 (ARCHITECTURE.md §5 Module O).

전체 AOI의 Module RISK 결과를 모아 Top-N 우선순위 큐를 생성한다. 위험도를
계산하지 않는다 — 그건 Module RISK의 일이다(§0.4). 여기서는 정렬·순번 부여·
상태 조회만 한다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from common.envelope import error_envelope, make_envelope
from module_o.store import store


def _status_for(entry: dict) -> str:
    return "점검완료" if entry.get("inspections") else "미점검"


def run(input: dict) -> dict:
    week_of = input.get("week_of")
    risk_results = input.get("risk_results")

    if not week_of or risk_results is None:
        return error_envelope("week_of 또는 risk_results가 없어 우선순위 큐를 만들 수 없습니다.", fallback_tier=3)

    entries = []
    warnings: list[str] = []
    for r in risk_results:
        site_id = r.get("site_id")
        if not site_id:
            warnings.append("site_id 없는 risk_result를 건너뜀")
            continue
        entry = store.upsert_risk_result(
            site_id,
            risk_score=r.get("risk_score"),
            risk_tier=r.get("risk_tier"),
            contributing_factors=r.get("contributing_factors"),
        )
        entries.append(entry)

    entries.sort(key=lambda e: e.get("risk_score") or 0, reverse=True)

    priority_queue = [
        {
            "rank": i,
            "site_id": e["site_id"],
            "risk_score": e.get("risk_score"),
            "status": _status_for(e),
        }
        for i, e in enumerate(entries, start=1)
    ]

    return make_envelope(
        {
            "week_of": week_of,
            "priority_queue": priority_queue,
            "queue_size": len(priority_queue),
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        },
        status="ok" if not warnings else "degraded",
        fallback_tier=1 if not warnings else 2,
        warnings=warnings,
    )
