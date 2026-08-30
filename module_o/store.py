"""관리대상지 상태 저장소 — ARCHITECTURE.md §2.1의 8단계 상태머신을 메모리에서
추적한다. MVP는 프로세스 인메모리 dict다(Aquaguard의 `AlertStore` 패턴
재사용) — 재시작하면 초기화된다. 실제 서비스에서는 PostGIS 등으로 교체
(§ARCHITECTURE 기술스택), 이 클래스의 메서드 시그니처만 유지하면 된다.

담당자 승인 게이트는 없다(§5 Module O) — 그래서 Aquaguard의
`auto_approve_timeout_min` 같은 승인 상태머신은 여기 없다.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

STAGES = (
    "관측",
    "변화탐지",
    "집계",
    "우선순위산정",
    "우선순위큐등록",
    "현장점검등록",
    "결과입력",
    "검증완료",  # Module VERIFY 구현 전까지는 도달하지 않는다(§ Module FIELD 구현 상태 참조)
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class SiteStateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sites: dict[str, dict] = {}

    def reset(self) -> None:
        """테스트 전용 — 프로세스 전역 싱글턴 상태를 초기화한다."""
        with self._lock:
            self._sites.clear()

    def upsert_risk_result(
        self,
        site_id: str,
        *,
        inspection_priority_score: int | None,
        priority_tier: str | None,
        contributing_factors: list | None = None,
        extra: dict | None = None,
    ) -> dict:
        """Module RISK 결과가 새로 나올 때마다 호출 — 우선순위큐등록 단계로 전이."""
        with self._lock:
            entry = self._sites.setdefault(
                site_id, {"site_id": site_id, "stage": "관측", "inspections": []}
            )
            entry["inspection_priority_score"] = inspection_priority_score
            entry["priority_tier"] = priority_tier
            entry["contributing_factors"] = contributing_factors or []
            if entry["stage"] in ("관측", "변화탐지", "집계", "우선순위산정"):
                entry["stage"] = "우선순위큐등록"
            if extra:
                entry.update(extra)
            entry["updated_at"] = _now_iso()
            return dict(entry)

    def get(self, site_id: str) -> dict | None:
        entry = self._sites.get(site_id)
        return dict(entry) if entry else None

    def all(self) -> list[dict]:
        return [dict(e) for e in self._sites.values()]

    def record_inspection(self, site_id: str, inspection: dict) -> dict:
        """Module FIELD 결과를 저장 — 결과입력 단계로 전이.

        검증완료로 바로 넘기지 않는다 — Module VERIFY(예측 vs 실측 backtest)가
        아직 구현되지 않았으므로, 여기서 "검증됐다"고 주장하면 거짓말이 된다.
        """
        with self._lock:
            entry = self._sites.setdefault(
                site_id, {"site_id": site_id, "stage": "관측", "inspections": []}
            )
            entry["inspections"].append(inspection)
            entry["stage"] = "결과입력"
            entry["updated_at"] = _now_iso()
            return dict(entry)


store = SiteStateStore()  # 프로세스 전역 싱글턴 — api_server.py와 공유
