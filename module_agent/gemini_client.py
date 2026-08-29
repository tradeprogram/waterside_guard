"""Gemini 클라이언트 초기화 — run.py(Q&A)와 report.py(주간보고서)가 공유한다."""
from __future__ import annotations

import os


def init_client():
    """(client, None) 또는 (None, 사람이 읽을 에러 메시지)를 반환한다. 예외를 던지지 않는다."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None, "GEMINI_API_KEY가 .env에 없습니다 — .env.example 참조."
    try:
        from google import genai
    except ImportError:
        return None, "google-genai 패키지가 설치되지 않았습니다 (pip install google-genai)."
    try:
        return genai.Client(api_key=api_key), None
    except Exception as e:  # noqa: BLE001
        return None, f"Gemini 클라이언트 초기화 실패: {e}"


def model_name() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
