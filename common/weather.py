"""최근 강우량 조회 (ARCHITECTURE.md §5 Module RISK "최근 기상" 요인).

KECI 내부 기상 데이터 접근권이 없어(개발_핸드오프_브리프 §2) Open-Meteo Archive
API(공개, API 키 불필요)로 대체한다 — 이 프로젝트가 지금까지 써온 "공개 데이터로만
진행" 원칙과 같은 선상. 실패해도 예외를 던지지 않고 None을 반환한다 — 이 요인이
없으면 Module RISK가 0으로 처리한다(§0.4 숫자를 지어내지 않는다 / §4.2 graceful
degradation, 이 프로젝트의 다른 관측 신호들과 동일한 원칙).
"""
from __future__ import annotations

import datetime as dt

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_WINDOW_DAYS = 14  # "최근 강우"의 기준 창 — 초기 가정치, Backtest B에서 재조정 가능


def fetch_recent_rainfall_mm(
    lat: float, lon: float, as_of_date: str, window_days: int = DEFAULT_WINDOW_DAYS
) -> float | None:
    """as_of_date(YYYY-MM-DD) 기준 최근 window_days일 누적 강우량(mm)을 반환한다."""
    try:
        end = dt.date.fromisoformat(as_of_date)
        start = end - dt.timedelta(days=window_days)
        resp = requests.get(
            ARCHIVE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily": "precipitation_sum",
                "timezone": "Asia/Seoul",
            },
            timeout=10,
        )
        resp.raise_for_status()
        values = [v for v in resp.json().get("daily", {}).get("precipitation_sum", []) if v is not None]
        return round(sum(values), 1) if values else None
    except Exception:  # noqa: BLE001 — best-effort 부가 요인, 실패해도 나머지 파이프라인은 계속 작동해야 한다
        return None
