"""Module FIELD — 현장 피드백 (ARCHITECTURE.md §5 Module FIELD).

입력을 검증하고 inspection_id를 발급한다. 상태 저장(결과입력 단계로 전이)은
이 모듈의 일이 아니다 — Module O의 상태머신이 관리한다(§ Module O 구현 상태
참조). api_server.py가 이 모듈의 결과를 받은 뒤 `module_o.store.record_inspection`
을 호출해 실제로 저장한다.
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope

REQUIRED_FIELDS = ("site_id", "inspector_id", "inspected_at", "actual_anomaly_found")
VALID_CATEGORIES = {"식생교란", "침수흔적", "불법이용", "이상없음", "기타"}


def run(input: dict) -> dict:
    missing = [f for f in REQUIRED_FIELDS if input.get(f) is None]
    if missing:
        return error_envelope(f"필수 입력 누락: {missing}", fallback_tier=3)

    category = input.get("anomaly_category")
    if category is not None and category not in VALID_CATEGORIES:
        return error_envelope(f"anomaly_category '{category}'는 허용되지 않는 값입니다({VALID_CATEGORIES})", fallback_tier=3)

    site_id = input["site_id"]
    inspected_at = input["inspected_at"]
    inspection_id = f"INSP-{inspected_at[:10].replace('-', '')}-{site_id}"

    return make_envelope(
        {"site_id": site_id, "inspection_id": inspection_id, "status": "완료"},
        status="ok",
        fallback_tier=1,
    )
