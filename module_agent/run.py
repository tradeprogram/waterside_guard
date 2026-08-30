"""Module AGENT — Evidence Agent (ARCHITECTURE.md §5 Module AGENT).

LLM은 우선순위 점수를 계산하지 않는다(§0.4) — Module RISK/CHG/FIELD가 이미 계산해둔
tool 결과만 읽어서 자연어로 설명한다. Gemini function calling으로 구현:
모델이 필요한 tool을 스스로 호출하고, tool이 반환한 숫자만 인용해 답한다.

`GEMINI_API_KEY`가 없거나 API 호출이 실패하면 예외 대신 템플릿 기반
폴백으로 전환한다(§4.3 AGENT 폴백 계층: LLM tool-calling → 템플릿 →
원자료 노출 — 이 모듈은 앞 두 단계를 구현).
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope
from module_agent.gemini_client import init_client, model_name
from module_agent.tools import get_inspection_history, get_risk_evidence, get_timeseries_summary

SYSTEM_INSTRUCTION = (
    "당신은 수변생태벨트 점검 우선순위 지원시스템의 근거 조회 에이전트입니다. 점검 우선순위 점수를 스스로 계산하거나 새로운 숫자를 "
    "만들어내지 마세요 — 제공된 tool을 호출해 얻은 값만 근거로 답하세요. 종(種) 판독(어떤 "
    "식물·현상인지 확정)이나 확정 진단은 하지 말고, 관측된 변화를 있는 그대로 담당자에게 "
    "설명하세요. 한국어로, 현장 담당자가 바로 이해할 수 있게 6문장 이내로 답하세요."
)


def _template_answer(site_id: str) -> str:
    """LLM 없이도 항상 동작하는 최소기능(§4.3 3순위 폴백) — tool 결과를 그대로 문장으로 짜맞춘다."""
    evidence = get_risk_evidence(site_id)
    if evidence.get("error"):
        return f"{site_id}에 대한 데이터가 없습니다."
    factors = evidence.get("contributing_factors", [])
    factor_text = ", ".join(f"{f['factor']}={f['value']}" for f in factors) or "근거 요인 없음"
    return f"{site_id}의 점검 우선순위 점수는 {evidence.get('inspection_priority_score')}점({evidence.get('priority_tier')})입니다. 근거: {factor_text}."


def _bound_tools(site_id: str, tools_used: list[str]) -> list:
    """Q&A 대상 site_id에 고정된 인자 없는 tool 함수들을 만든다 — 모델이 site_id를
    잘못 부르거나 지어내는 것을 원천 차단한다."""

    def get_risk_evidence_for_this_site() -> dict:
        """이 질문이 가리키는 대상지의 현재 점검 우선순위 점수·등급·근거 요인을 반환한다."""
        tools_used.append("get_risk_evidence")
        return get_risk_evidence(site_id)

    def get_timeseries_summary_for_this_site() -> dict:
        """이 질문이 가리키는 대상지의 기준기간·현재기간 위성 관측치를 반환한다."""
        tools_used.append("get_timeseries_summary")
        return get_timeseries_summary(site_id)

    def get_inspection_history_for_this_site() -> dict:
        """이 질문이 가리키는 대상지의 과거 현장점검 이력을 반환한다."""
        tools_used.append("get_inspection_history")
        return get_inspection_history(site_id)

    return [
        get_risk_evidence_for_this_site,
        get_timeseries_summary_for_this_site,
        get_inspection_history_for_this_site,
    ]


def run(input: dict) -> dict:
    site_id = input.get("site_id")
    question = input.get("question")

    if not site_id or not question:
        return error_envelope("site_id/question이 필요합니다.", fallback_tier=3)

    client, init_error = init_client()
    if client is None:
        return make_envelope(
            {"site_id": site_id, "question": question, "answer": _template_answer(site_id), "tools_used": []},
            status="degraded",
            fallback_tier=2,
            warnings=[init_error],
        )

    tools_used: list[str] = []

    try:
        from google.genai import types

        response = client.models.generate_content(
            model=model_name(),
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=_bound_tools(site_id, tools_used),
            ),
        )
        answer = response.text
    except Exception as e:  # noqa: BLE001 — 모듈 경계에서는 모든 예외를 degraded로 흡수(§4.2)
        return make_envelope(
            {"site_id": site_id, "question": question, "answer": _template_answer(site_id), "tools_used": []},
            status="degraded",
            fallback_tier=2,
            warnings=[f"Gemini 호출 실패, 템플릿으로 대체: {e}"],
        )

    if not answer:
        return make_envelope(
            {"site_id": site_id, "question": question, "answer": _template_answer(site_id), "tools_used": tools_used},
            status="degraded",
            fallback_tier=2,
            warnings=["Gemini가 빈 응답을 반환해 템플릿으로 대체"],
        )

    return make_envelope(
        {"site_id": site_id, "question": question, "answer": answer, "tools_used": tools_used},
        status="ok",
        fallback_tier=1,
    )
