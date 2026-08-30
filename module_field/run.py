"""Module FIELD — 현장 피드백 (ARCHITECTURE.md §5 Module FIELD).

입력을 검증하고 inspection_id를 발급한다. 상태 저장(결과입력 단계로 전이)은
이 모듈의 일이 아니다 — Module O의 상태머신이 관리한다(§ Module O 구현 상태
참조). api_server.py가 이 모듈의 결과를 받은 뒤 `module_o.store.record_inspection`
을 호출해 실제로 저장한다.
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope

REQUIRED_FIELDS = ("site_id", "inspector_id", "inspected_at", "actual_anomaly_found")

# 2026-08-31: 중간점검 리서치 §Field Verification Loop의 taxonomy로 교체했다.
# 예전 분류("식생교란/침수흔적/불법이용/이상없음/기타")는 훼손 여부만 구분해서, 오탐이 났을 때
# *왜* 났는지(예초였는지, 계절 변화였는지)를 되짚을 수 없었다. 새 분류는 "변화는 있었지만
# 훼손이 아닌" 경우(mowing_agriculture·natural_seasonal·restoration_work)를 따로 받아
# false positive의 원인을 분석할 수 있게 한다 — 이게 향후 ML label의 기반이 된다.
VALID_CATEGORIES = {
    "vegetation_loss",
    "bare_ground",
    "construction_earthwork",
    "flooding_water_level",
    "mowing_agriculture",
    "restoration_work",
    "natural_seasonal",
    "other",
}

# "판단 보류"를 actual_anomaly_found=false와 구분해 기록한다 — Backtest에서 보류는
# 양성도 음성도 아니라 별도 취급해야 하는데, 불리언 하나로는 그 구분이 사라진다.
VALID_VERDICTS = {"yes", "no", "uncertain"}


def run(input: dict) -> dict:
    missing = [f for f in REQUIRED_FIELDS if input.get(f) is None]
    if missing:
        return error_envelope(f"필수 입력 누락: {missing}", fallback_tier=3)

    category = input.get("anomaly_category")
    if category is not None and category not in VALID_CATEGORIES:
        return error_envelope(f"anomaly_category '{category}'는 허용되지 않는 값입니다({VALID_CATEGORIES})", fallback_tier=3)

    verdict = input.get("verdict")
    if verdict is not None and verdict not in VALID_VERDICTS:
        return error_envelope(f"verdict '{verdict}'는 허용되지 않는 값입니다({VALID_VERDICTS})", fallback_tier=3)

    site_id = input["site_id"]
    inspected_at = input["inspected_at"]
    inspection_id = f"INSP-{inspected_at[:10].replace('-', '')}-{site_id}"

    return make_envelope(
        {"site_id": site_id, "inspection_id": inspection_id, "status": "완료"},
        status="ok",
        fallback_tier=1,
    )
