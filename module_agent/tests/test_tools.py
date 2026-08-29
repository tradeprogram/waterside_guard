import pytest

from module_agent.tools import get_inspection_history, get_risk_evidence, get_timeseries_summary, get_weekly_summary
from module_o.store import store


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_get_risk_evidence_missing_site():
    assert get_risk_evidence("NOPE")["error"]


def test_get_risk_evidence_returns_stored_values():
    store.upsert_risk_result(
        "A1037", risk_score=54, risk_tier="2순위",
        contributing_factors=[{"factor": "anomaly_score_mean", "value": 0.72, "weight": 0.35}],
        extra={"anomaly_score": 0.72, "change_type_hint": "vegetation_decline"},
    )
    evidence = get_risk_evidence("A1037")
    assert evidence["risk_score"] == 54
    assert evidence["risk_tier"] == "2순위"
    assert evidence["contributing_factors"][0]["factor"] == "anomaly_score_mean"


def test_get_timeseries_summary():
    store.upsert_risk_result(
        "A1037", risk_score=10, risk_tier="정상",
        extra={"baseline_scenes": [{"acquisition_date": "2024-06-10"}], "current_scenes": []},
    )
    ts = get_timeseries_summary("A1037")
    assert len(ts["baseline_scenes"]) == 1
    assert ts["current_scenes"] == []


def test_get_inspection_history():
    store.upsert_risk_result("A1037", risk_score=10, risk_tier="정상")
    store.record_inspection("A1037", {"actual_anomaly_found": True})
    history = get_inspection_history("A1037")
    assert len(history["inspections"]) == 1


def test_get_weekly_summary_counts():
    store.upsert_risk_result("A", risk_score=80, risk_tier="1순위")
    store.upsert_risk_result("B", risk_score=55, risk_tier="2순위")
    store.upsert_risk_result("C", risk_score=10, risk_tier="정상")
    store.record_inspection("A", {"actual_anomaly_found": True})
    store.record_inspection("C", {"actual_anomaly_found": False})

    summary = get_weekly_summary()
    assert summary["total_sites"] == 3
    assert summary["high_risk_count"] == 2
    assert summary["inspected_count"] == 2
    assert summary["confirmed_anomaly_count"] == 1
