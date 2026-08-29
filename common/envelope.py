"""공통 봉투(envelope) 규약 — ARCHITECTURE.md §4.2.

모든 모듈의 run(input) -> dict는 이 형식을 반환한다:
    {"status": "ok"|"degraded"|"error", "fallback_tier": int, "data": {...}, "warnings": [...]}

모듈은 예외를 밖으로 던지지 않는다 — 실패해도 degraded envelope으로 감싸서
Module O가 나머지 모듈을 계속 진행할 수 있게 한다.
"""
from __future__ import annotations

from typing import Any, Literal

Status = Literal["ok", "degraded", "error"]


def make_envelope(
    data: dict[str, Any],
    *,
    status: Status = "ok",
    fallback_tier: int = 1,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """표준 envelope을 만든다. 값 검증은 하지 않는다 — 호출부 책임."""
    return {
        "status": status,
        "fallback_tier": fallback_tier,
        "data": data,
        "warnings": warnings or [],
    }


def error_envelope(warning: str, *, fallback_tier: int = 3) -> dict[str, Any]:
    """모듈 내부에서 예외를 잡았을 때 쓰는 최종 폴백 envelope.

    status를 "error"가 아니라 "degraded"로 두는 이유: Module O가 이 결과를
    받아도 파이프라인을 계속 진행해야 하기 때문(§4.2 graceful degradation
    원칙). 완전히 복구 불가능한 치명적 상황에서만 status="error"를 쓴다.
    """
    return make_envelope({}, status="degraded", fallback_tier=fallback_tier, warnings=[warning])
