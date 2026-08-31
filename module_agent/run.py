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

SYSTEM_INSTRUCTION = """당신은 수변생태벨트 점검 우선순위 지원시스템의 근거 조회 에이전트입니다.
현장 담당자가 출동 전에 근거를 확인하려고 묻습니다.

규칙:
1. 점수를 스스로 계산하거나 새로운 숫자를 만들지 마세요. 제공된 tool을 호출해 얻은 값만 씁니다.

2. 무엇이 훼손됐는지 판정하지 마세요. change_type_hint(vegetation_decline 등)는 확정된 원인이
   아니라 계절 패턴과 다른 변화가 있다는 선별 신호일 뿐입니다. "식생이 감소했다"가 아니라
   "식생 활력이 낮아지는 방향의 신호가 관측됐다"처럼 쓰고, 영문 코드값은 노출하지 말고 한국어로
   옮기세요. 종(種) 판독과 확정 진단은 금지입니다 — 확정은 현장과 드론의 몫입니다.

3. 불확실성을 빠뜨리지 마세요. 다음에 해당하면 반드시 언급합니다.
   - weight_coverage가 1 미만이면, 전체 근거 중 몇 %만 확보된 상태에서 산정된 점수인지
   - evidence_confidence의 effect가 음수인 항목(강우 교란, 센서 불일치, 관측 부족 등).
     특히 최근 강우가 많은데 습윤 신호가 잡힌 경우, 강우를 "점수를 올린 요인"으로만 소개하지 말고
     기상에 의한 변화일 수 있어 신뢰도를 낮추는 요인이라는 점을 함께 밝히세요.
   - changed_area_ratio가 픽셀 실측이 아니라 근사치인 경우

4. 마지막 문장은 현장에서 무엇을 확인하면 되는지로 맺으세요.

한국어 '-습니다'체로, 6문장 이내로 답하세요."""


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


# 직전 대화 몇 턴을 함께 보낼지 — 길수록 토큰만 먹고 tool 호출 정확도가 떨어진다.
HISTORY_TURNS = 8


def _as_contents(question: str, history: list[dict] | None) -> list:
    """이전 대화를 Gemini contents 형식으로 바꾼다.

    이게 없으면 "그럼 왜 그렇죠?" 같은 후속 질문이 앞 맥락을 잃고 매번 처음부터 묻는 꼴이 된다
    (tradeprogram/policymaps agent가 history를 최근 8턴만 실어 보내는 방식을 따랐다).
    """
    contents: list = []
    for turn in (history or [])[-HISTORY_TURNS:]:
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        role = "user" if turn.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": question}]})
    return contents


def run(input: dict) -> dict:
    site_id = input.get("site_id")
    question = input.get("question")
    history = input.get("history")

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
            contents=_as_contents(question, history),
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
