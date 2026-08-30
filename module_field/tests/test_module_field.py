from module_field.run import run


def test_missing_required_field_returns_degraded():
    result = run({"site_id": "A1037"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_invalid_category_rejected():
    result = run(
        {
            "site_id": "A1037",
            "inspector_id": "staff_003",
            "inspected_at": "2026-09-02T10:15:00+09:00",
            "actual_anomaly_found": True,
            "anomaly_category": "외계인출현",
        }
    )
    assert result["status"] == "degraded"


def test_valid_input_produces_inspection_id():
    result = run(
        {
            "site_id": "A1037",
            "inspector_id": "staff_003",
            "inspected_at": "2026-09-02T10:15:00+09:00",
            "actual_anomaly_found": True,
            "anomaly_category": "vegetation_loss",
            "photo_refs": ["field/A1037/2026-09-02_01.jpg"],
            "note": "동측 사면 나지 노출 확인",
        }
    )
    assert result["status"] == "ok"
    assert result["data"]["inspection_id"] == "INSP-20260902-A1037"
    assert result["data"]["status"] == "완료"


def test_verdict_uncertain_is_accepted_and_distinct_from_negative():
    """'판단 보류'는 음성과 다른 사례다 — Backtest에서 따로 취급하려면 기록에 남아야 한다."""
    result = run(
        {
            "site_id": "A1037",
            "inspector_id": "staff_003",
            "inspected_at": "2026-09-02T10:15:00+09:00",
            "actual_anomaly_found": False,
            "verdict": "uncertain",
        }
    )
    assert result["status"] == "ok"


def test_invalid_verdict_is_rejected():
    result = run(
        {
            "site_id": "A1037",
            "inspector_id": "staff_003",
            "inspected_at": "2026-09-02T10:15:00+09:00",
            "actual_anomaly_found": False,
            "verdict": "maybe",
        }
    )
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_non_damage_change_types_are_valid_categories():
    """예초·계절변화도 유효한 분류여야 오탐 원인을 기록할 수 있다."""
    for category in ("mowing_agriculture", "natural_seasonal", "restoration_work"):
        result = run(
            {
                "site_id": "A1037",
                "inspector_id": "staff_003",
                "inspected_at": "2026-09-02T10:15:00+09:00",
                "actual_anomaly_found": True,
                "anomaly_category": category,
            }
        )
        assert result["status"] == "ok", category
