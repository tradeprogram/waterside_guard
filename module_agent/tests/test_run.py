from unittest.mock import MagicMock, patch

import pytest

from module_agent.run import run
from module_o.store import store


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    store.upsert_risk_result(
        "A1037",
        inspection_priority_score=54,
        priority_tier="2순위",
        contributing_factors=[{"factor": "anomaly_score_mean", "value": 0.72, "weight": 0.35}],
        extra={"anomaly_score": 0.72, "change_type_hint": "vegetation_decline"},
    )
    yield
    store.reset()


def test_missing_input_returns_degraded():
    result = run({"site_id": "A1037"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


@patch("module_agent.run.init_client")
def test_no_gemini_key_falls_back_to_template(mock_init):
    mock_init.return_value = (None, "GEMINI_API_KEY가 .env에 없습니다")
    result = run({"site_id": "A1037", "question": "왜 1위야?"})

    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 2
    assert "54" in result["data"]["answer"]
    assert result["data"]["tools_used"] == []


@patch("module_agent.run.init_client")
def test_gemini_failure_falls_back_to_template(mock_init):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("network down")
    mock_init.return_value = (mock_client, None)

    result = run({"site_id": "A1037", "question": "왜 1위야?"})

    assert result["status"] == "degraded"
    assert any("network down" in w for w in result["warnings"])
    assert "54" in result["data"]["answer"]


@patch("module_agent.run.init_client")
def test_successful_call_invokes_bound_tools_and_returns_answer(mock_init):
    mock_client = MagicMock()

    def fake_generate_content(model, contents, config):
        # SDK의 automatic function calling을 흉내: 전달된 tool을 실제로 한 번 호출해본다.
        for tool_fn in config.tools:
            tool_fn()
        response = MagicMock()
        response.text = "이 대상지는 anomaly_score 0.72로 위험점수 54점(2순위)입니다."
        return response

    mock_client.models.generate_content.side_effect = fake_generate_content
    mock_init.return_value = (mock_client, None)

    result = run({"site_id": "A1037", "question": "왜 1위야?"})

    assert result["status"] == "ok"
    assert result["fallback_tier"] == 1
    assert "54" in result["data"]["answer"]
    assert "get_risk_evidence" in result["data"]["tools_used"]


@patch("module_agent.run.init_client")
def test_empty_response_falls_back_to_template(mock_init):
    mock_client = MagicMock()
    response = MagicMock()
    response.text = ""
    mock_client.models.generate_content.return_value = response
    mock_init.return_value = (mock_client, None)

    result = run({"site_id": "A1037", "question": "왜 1위야?"})
    assert result["status"] == "degraded"
    assert "54" in result["data"]["answer"]
