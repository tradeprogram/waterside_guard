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
            "anomaly_category": "식생교란",
            "photo_refs": ["field/A1037/2026-09-02_01.jpg"],
            "note": "동측 사면 나지 노출 확인",
        }
    )
    assert result["status"] == "ok"
    assert result["data"]["inspection_id"] == "INSP-20260902-A1037"
    assert result["data"]["status"] == "완료"
