"""Module AGENT — 주간보고서 생성 (ARCHITECTURE.md §7 POST /reports/weekly).

`run.py`(1개 대상지 Q&A)와 같은 원칙: LLM은 `get_weekly_summary()`가 반환한
숫자만 인용해 문장으로 풀어쓴다. 새 숫자를 계산하지 않는다.
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope
from module_agent.gemini_client import init_client, model_name
from module_agent.tools import get_weekly_summary

SYSTEM_INSTRUCTION = (
    "당신은 수변가드 AI의 근거 조회 에이전트입니다. get_weekly_summary tool을 호출해 얻은 "
    "숫자만 근거로, 공공기관 주간 점검현황 보고서의 '종합 의견'란에 들어갈 3~5문장을 작성하세요. "
    "숫자를 지어내지 말고, '-습니다'체의 담담한 실무 문어로 쓰세요. 단위는 필지를 쓰고, "
    "'고위험'처럼 훼손 발생 확률을 단정하는 표현 대신 '우선 확인 대상'처럼 점검 순서를 "
    "가리키는 표현을 쓰세요."
)


def _template_report(week_of: str) -> str:
    s = get_weekly_summary()
    return (
        f"{week_of} 기준 점검 대상은 전체 {s['total_sites']}필지이며, 이 중 우선 확인 대상"
        f"(1·2순위)은 {s['high_risk_count']}필지입니다. "
        f"금주 현장점검이 완료된 필지는 {s['inspected_count']}필지이고, "
        f"그 중 변화가 실제로 확인된 필지는 {s['confirmed_anomaly_count']}필지입니다. "
        "우선 확인 대상은 훼손 발생 확률이 아니라 점검 배정 순서를 나타내는 구분입니다."
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
        """금주 점검 대상 현황 요약(총 필지·우선 확인 대상·점검완료·변화확인 필지 수)을 반환한다."""
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
