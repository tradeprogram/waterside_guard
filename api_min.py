"""최소 백엔드 — 배포본에서 실시간 계산이 필요한 것만 남긴 API.

**왜 따로 두는가**: 조회용 응답(`/sites`, `/priority-queue`, `/verify/*`, `/route`,
필지별 근거·시계열·영상)은 전부 사전계산 결과라 `scripts/build_static_api.py`가 파일로
구워 `ui/public/api/` 아래에 두고 프론트가 직접 읽는다. 그러면 실제로 계산이 필요한 건
세 가지만 남는다.

  POST /sites/{id}/ask     AGENT 근거 조회 (Gemini, 30~40초)
  POST /reports/weekly     주간 보고서 종합 의견 (Gemini)
  POST /inspections        현장점검 결과 등록 (인메모리 상태 변경)

이 셋만 남기면 `api_server.py`가 끌고 오던 geopandas·pyproj·shapely·matplotlib·
earthengine-api가 전부 필요 없어진다(requirements-min.txt 참조). 컨테이너가 가벼워지고,
GEE 자격증명도 배포 환경에 둘 필요가 없다.

**상태 저장의 한계**: 점검 등록은 여전히 인메모리다(`module_o/store.py`). 프로세스가
재시작되면 사라진다 — 프로토타입 시연 범위에서는 의도된 동작이고, 실제 도입 시에는
이 자리에 기관 DB가 들어간다.

실행:
    ALLOWED_ORIGINS=https://<배포도메인> python -m uvicorn api_min:app --port 8001
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from module_agent.report import generate as agent_generate_report  # noqa: E402
from module_agent.run import run as agent_run  # noqa: E402
from module_field.run import run as field_run  # noqa: E402
from module_o.store import store  # noqa: E402

# build_static_api.py의 산출물. 이 파일들이 곧 이 서버의 데이터 소스다.
STATIC_DIR = Path(os.environ.get("STATIC_API_DIR", "ui/public/api"))


def _read(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — 일부가 없어도 나머지는 뜬다
        return None


def _load_static_snapshot() -> int:
    """정적 스냅샷을 store에 적재한다.

    AGENT tool이 읽는 값이 `/sites`에는 없고 필지별 evidence·timeseries에만 있어서
    (weight_coverage·evidence_confidence·scenes) 세 파일을 합쳐 한 entry로 만든다.
    이 병합을 빠뜨리면 Agent가 불확실성을 언급하지 못한다.
    """
    sites = _read(STATIC_DIR / "sites.json")
    if not isinstance(sites, list):
        return 0

    for site in sites:
        sid = site.get("site_id")
        if not sid:
            continue
        entry = dict(site)
        for name in ("evidence", "timeseries"):
            extra = _read(STATIC_DIR / "sites" / sid / f"{name}.json")
            if isinstance(extra, dict):
                entry.update({k: v for k, v in extra.items() if k != "site_id"})
        entry.setdefault("inspections", [])
        # store의 공개 진입점은 upsert_risk_result 하나다 — 나머지 필드는 extra로 넣는다.
        store.upsert_risk_result(
            sid,
            inspection_priority_score=entry.get("inspection_priority_score"),
            priority_tier=entry.get("priority_tier"),
            contributing_factors=entry.get("contributing_factors") or [],
            extra={k: v for k, v in entry.items() if k not in
                   ("site_id", "inspection_priority_score", "priority_tier", "contributing_factors")},
        )
    return len(sites)


@asynccontextmanager
async def lifespan(app: FastAPI):
    n = _load_static_snapshot()
    print(f"[api_min] 정적 스냅샷 적재: {n}필지 ({STATIC_DIR})")
    if n == 0:
        print(f"[api_min] 경고: {STATIC_DIR}/sites.json을 읽지 못했습니다 — AGENT가 근거를 찾지 못합니다.")
    yield


app = FastAPI(title="수변생태벨트 점검 우선순위 지원시스템 API (최소)", version="0.1.0", lifespan=lifespan)

# 배포 도메인은 ALLOWED_ORIGINS(쉼표 구분)로 넣는다. localhost는 개발용으로 항상 허용.
_allowed_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "min", "sites_loaded": len(store.all())}


class AskTurn(BaseModel):
    role: str
    text: str


class AskRequest(BaseModel):
    question: str
    history: list[AskTurn] | None = None


@app.post("/sites/{site_id}/ask")
def ask_site(site_id: str, payload: AskRequest) -> dict:
    if store.get(site_id) is None:
        raise HTTPException(404, f"site '{site_id}' not found")
    return agent_run(
        {
            "site_id": site_id,
            "question": payload.question,
            "history": [t.model_dump() for t in (payload.history or [])],
        }
    )


class WeeklyReportRequest(BaseModel):
    week_of: str


@app.post("/reports/weekly")
def create_weekly_report(payload: WeeklyReportRequest) -> dict:
    return agent_generate_report({"week_of": payload.week_of})


class InspectionRequest(BaseModel):
    site_id: str
    inspector_id: str
    inspected_at: str
    actual_anomaly_found: bool
    verdict: str | None = None
    anomaly_category: str | None = None
    photo_refs: list[str] = []
    note: str | None = None


@app.post("/inspections")
def create_inspection(payload: InspectionRequest) -> dict:
    result = field_run(payload.model_dump())
    if result["status"] != "ok":
        raise HTTPException(400, result["warnings"])
    store.record_inspection(payload.site_id, payload.model_dump())
    return result
