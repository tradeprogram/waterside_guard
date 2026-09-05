"""route/*.json 정적 스냅샷만 다시 굽는다 — 도로 실거리 전환 반영(2026-09-02).

scripts/build_static_api.py 전체를 다시 돌리면 GEE 썸네일까지 재조회해 할당량을
건드리고 시간도 오래 걸린다. 이번에 바뀐 건 module_o/routing.py(동선 거리 계산)뿐이므로
`/priority-queue/route`만 다시 구우면 충분하다.

사용법:
    python -m uvicorn api_server:app --port 8001   # 먼저 로컬 API를 띄운다
    python scripts/rebuild_route_snapshots.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

API_BASE = "http://localhost:8001"
OUT_DIR = Path("ui/public/api/route")
ROUTE_BUDGETS = range(1, 31)


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=60) as r:
        return json.load(r)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bases = set()
    for b in ROUTE_BUDGETS:
        payload = _get(f"/priority-queue/route?budget={b}")
        (OUT_DIR / f"{b}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        bases.add(payload.get("data", {}).get("distance_basis"))
        print(f"  route/{b}.json  distance_basis={payload.get('data', {}).get('distance_basis')}"
              f"  saved_pct={payload.get('data', {}).get('saved_pct')}")
    print(f"\n완료 — 사용된 distance_basis 종류: {bases}")


if __name__ == "__main__":
    main()
