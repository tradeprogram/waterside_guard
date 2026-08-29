"""Module AGENT — 주간보고서 생성 (ARCHITECTURE.md §7 POST /reports/weekly).

`run.py`(1개 대상지 Q&A)와 같은 원칙: LLM은 `get_weekly_summary()`가 반환한
숫자만 인용해 문장으로 풀어쓴다. 새 숫자를 계산하지 않는다.
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope
from module_agent.gemini_client import init_client, model_name
from module_agent.tools import get_weekly_summary

SYSTEM_INSTRUCTION = (
    "당신은 수변가드 AI의 Evidence Agent입니다. get_weekly_summary tool을 호출해 얻은 "
    "숫자만 근거로 현장 담당자에게 보낼 주간보고서를 3~5문장으로 작성하세요. "
    "숫자를 지어내지 말고, 한국어로 담담하게 쓰세요."
)


def _template_report(week_of: str) -> str:
    s = get_weekly_summary()
    return (
        f"{week_of} 주간보고: 전체 대상지 {s['total_sites']}개 중 고위험(1·2순위) "
        f"{s['high_risk_count']}개, 이번 주 현장점검 완료 {s['inspected_count']}개, "
        f"그 중 실제 이상이 확인된 건수는 {s['confirmed_anomaly_count']}건입니다."
    )


def generate(input: dict) -> dict:
    week_of = input.get("week_of")
    if not week_of:
        return error_envelope("week_of가 필요합니다.", fallback_tier=3)

    client, init_error = init_client()
    if client is None:
        return make_envelope(
            {"week_of": week_of, "report_text": _template_report(week_of), "tools_used": []},
            status="degraded",
            fallback_tier=2,
            warnings=[init_error],
        )

    tools_used: list[str] = []

    def get_weekly_summary_tool() -> dict:
        """이번 주 전체 대상지 현황 요약(총 대상지·고위험·점검완료·실제이상확인 건수)을 반환한다."""
        tools_used.append("get_weekly_summary")
        return get_weekly_summary()

    try:
        from google.genai import types

        response = client.models.generate_content(
            model=model_name(),
            contents=f"{week_of} 주간보고서를 작성해주세요.",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[get_weekly_summary_tool],
            ),
        )
        report_text = response.text
    except Exception as e:  # noqa: BLE001
        return make_envelope(
            {"week_of": week_of, "report_text": _template_report(week_of), "tools_used": []},
            status="degraded",
            fallback_tier=2,
            warnings=[f"Gemini 호출 실패, 템플릿으로 대체: {e}"],
        )

    if not report_text:
        return make_envelope(
            {"week_of": week_of, "report_text": _template_report(week_of), "tools_used": tools_used},
            status="degraded",
            fallback_tier=2,
            warnings=["Gemini가 빈 응답을 반환해 템플릿으로 대체"],
        )

    return make_envelope(
        {"week_of": week_of, "report_text": report_text, "tools_used": tools_used},
        status="ok",
        fallback_tier=1,
    )
