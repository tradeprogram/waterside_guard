from unittest.mock import MagicMock, patch

import pytest

from module_agent.report import generate
from module_o.store import store


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    store.upsert_risk_result("A", risk_score=80, risk_tier="1순위")
    store.upsert_risk_result("B", risk_score=10, risk_tier="정상")
    store.record_inspection("A", {"actual_anomaly_found": True})
    yield
    store.reset()


def test_missing_week_of_returns_degraded():
    result = generate({})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


@patch("module_agent.report.init_client")
def test_no_gemini_key_falls_back_to_template(mock_init):
    mock_init.return_value = (None, "no key")
    result = generate({"week_of": "2026-09-01"})
    assert result["status"] == "degraded"
    assert "2" in result["data"]["report_text"]  # total_sites=2가 문장에 들어감


@patch("module_agent.report.init_client")
def test_successful_call_returns_llm_text(mock_init):
    mock_client = MagicMock()

    def fake_generate_content(model, contents, config):
        for tool_fn in config.tools:
            tool_fn()
        response = MagicMock()
        response.text = "이번 주 고위험 1개소 중 1개소 점검 완료, 1건 실제 이상 확인."
        return response

    mock_client.models.generate_content.side_effect = fake_generate_content
    mock_init.return_value = (mock_client, None)

    result = generate({"week_of": "2026-09-01"})
    assert result["status"] == "ok"
    assert "고위험" in result["data"]["report_text"]
    assert "get_weekly_summary" in result["data"]["tools_used"]
