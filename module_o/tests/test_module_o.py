import pytest

from module_o.run import run
from module_o.store import store


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_missing_input_returns_degraded():
    result = run({"week_of": "2026-09-01"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_queue_sorted_by_risk_score_descending():
    result = run(
        {
            "week_of": "2026-09-01",
            "risk_results": [
                {"site_id": "A", "risk_score": 30, "risk_tier": "3순위"},
                {"site_id": "B", "risk_score": 80, "risk_tier": "1순위"},
                {"site_id": "C", "risk_score": 55, "risk_tier": "2순위"},
            ],
        }
    )

    assert result["status"] == "ok"
    queue = result["data"]["priority_queue"]
    assert [q["site_id"] for q in queue] == ["B", "C", "A"]
    assert [q["rank"] for q in queue] == [1, 2, 3]
    assert all(q["status"] == "미점검" for q in queue)
    assert result["data"]["queue_size"] == 3


def test_site_without_id_is_skipped_with_warning():
    result = run(
        {
            "week_of": "2026-09-01",
            "risk_results": [{"risk_score": 50}],
        }
    )
    assert result["status"] == "degraded"
    assert result["data"]["queue_size"] == 0
    assert any("site_id" in w for w in result["warnings"])


def test_inspected_site_shows_as_checked_in_next_queue_run():
    run(
        {
            "week_of": "2026-09-01",
            "risk_results": [{"site_id": "A", "risk_score": 80, "risk_tier": "1순위"}],
        }
    )
    store.record_inspection("A", {"actual_anomaly_found": True})

    result = run(
        {
            "week_of": "2026-09-08",
            "risk_results": [{"site_id": "A", "risk_score": 40, "risk_tier": "3순위"}],
        }
    )
    assert result["data"]["priority_queue"][0]["status"] == "점검완료"


def test_upsert_preserves_inspection_history_across_runs():
    run({"week_of": "W1", "risk_results": [{"site_id": "A", "risk_score": 80, "risk_tier": "1순위"}]})
    store.record_inspection("A", {"actual_anomaly_found": True})
    run({"week_of": "W2", "risk_results": [{"site_id": "A", "risk_score": 20, "risk_tier": "정상"}]})

    entry = store.get("A")
    assert len(entry["inspections"]) == 1
    assert entry["stage"] == "결과입력"
