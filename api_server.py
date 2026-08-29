"""FastAPI 서버 — ARCHITECTURE.md §7 API 설계.

각 모듈을 import해서 순서대로 호출한다(REST로 쪼개지 않음, §4.2). 서버 시작
시 `data/processed/yongin_yubang_priority_queue.geojson`(§Module RISK 조기
실증 결과)을 읽어 Module O의 인메모리 store를 채운다 — 매 요청마다 Earth
Engine을 다시 부르지 않는다(배치 계산 → 빠른 조회 API라는 §2.2 원칙).

`POST /reports/weekly`는 아직 없다 — Module AGENT가 구현되지 않았다(§12
로드맵). 없는 기능을 있는 척 노출하지 않는다.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.geo import geometry_5179_to_4326
from module_field.run import run as field_run
from module_o.run import run as o_run
from module_o.store import store
from module_verify.run import run as verify_run

SNAPSHOT_PATH = Path("data/processed/yongin_yubang_priority_queue.geojson")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_snapshot()
    yield


app = FastAPI(title="Waterside Guard API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # 개발 서버(Next.js)가 매번 다른 포트로 뜰 수 있어(autoPort) localhost 전 포트를 허용한다.
    # 프로토타입 범위 — 실제 배포 시 특정 origin으로 좁힐 것.
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _json_field(value) -> list:
    """GeoJSON 드라이버가 JSON처럼 보이는 문자열 속성을 이미 list/dict로 파싱해 돌려주는 경우가
    있어(값에 따라 str 또는 list/dict) 양쪽 다 받아준다."""
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    return json.loads(value)


def _load_snapshot() -> None:
    """스냅샷 GeoJSON(EPSG:5179)을 읽어 store를 채운다. 파일이 없으면 빈 상태로 시작한다
    (Module RISK를 아직 안 돌렸다는 뜻 — 예외를 던지지 않고 조용히 넘어간다, §4.2)."""
    if not SNAPSHOT_PATH.exists():
        return

    import geopandas as gpd

    gdf = gpd.read_file(SNAPSHOT_PATH)  # EPSG:5179
    for row in gdf.itertuples():
        geometry_4326 = geometry_5179_to_4326(row.geometry.__geo_interface__)
        store.upsert_risk_result(
            row.site_id,
            risk_score=row.risk_score,
            risk_tier=row.risk_tier,
            contributing_factors=_json_field(row.contributing_factors_json),
            extra={
                "pnu": row.pnu,
                "jibun": row.jibun,
                "addr": row.addr,
                "anomaly_score": row.anomaly_score,
                "change_type_hint": row.change_type_hint,
                "geometry_geojson": geometry_4326,
                "baseline_scenes": _json_field(row.baseline_scenes_json),
                "current_scenes": _json_field(row.current_scenes_json),
            },
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "sites_loaded": len(store.all())}


@app.get("/sites")
def list_sites() -> list[dict]:
    return store.all()


@app.get("/sites/{site_id}")
def get_site(site_id: str) -> dict:
    entry = store.get(site_id)
    if entry is None:
        raise HTTPException(404, f"site '{site_id}' not found")
    return entry


@app.get("/sites/{site_id}/timeseries")
def get_timeseries(site_id: str) -> dict:
    entry = store.get(site_id)
    if entry is None:
        raise HTTPException(404, f"site '{site_id}' not found")
    return {
        "site_id": site_id,
        "baseline_scenes": entry.get("baseline_scenes", []),
        "current_scenes": entry.get("current_scenes", []),
    }


@app.get("/sites/{site_id}/evidence")
def get_evidence(site_id: str) -> dict:
    entry = store.get(site_id)
    if entry is None:
        raise HTTPException(404, f"site '{site_id}' not found")
    return {
        "site_id": site_id,
        "risk_score": entry.get("risk_score"),
        "risk_tier": entry.get("risk_tier"),
        "contributing_factors": entry.get("contributing_factors", []),
        "anomaly_score": entry.get("anomaly_score"),
        "change_type_hint": entry.get("change_type_hint"),
    }


@app.get("/priority-queue")
def get_priority_queue(week_of: str = "current") -> dict:
    entries = store.all()
    risk_results = [
        {
            "site_id": e["site_id"],
            "risk_score": e.get("risk_score"),
            "risk_tier": e.get("risk_tier"),
            "contributing_factors": e.get("contributing_factors", []),
        }
        for e in entries
    ]
    result = o_run({"week_of": week_of, "risk_results": risk_results})
    if result["status"] == "error":
        raise HTTPException(500, result["warnings"])
    return result


@app.get("/verify/backtest")
def get_backtest(period: str = "current", k: int = 10) -> dict:
    """모든 site의 '현재' risk_score를 predictions로, 등록된 현장점검 이력을
    field_results로 써서 Module VERIFY를 돌린다.

    **한계**: 진짜 leakage-free backtest가 아니다 — predictions가 "그 예측
    시점 이전 데이터로만 재실행한 결과"가 아니라 지금 store에 있는 최신
    risk_score를 그대로 쓴다. 과거 특정 시점의 예측을 재현하려면 예측
    스냅샷을 시계열로 저장하는 인프라가 필요한데 아직 없다(§12 TODO). 그래도
    Module VERIFY의 leakage 경고(§ Module VERIFY 구현 상태)는 그대로
    작동한다 — inspected_at이 있는 field_result에 한해 확인된다.
    """
    entries = store.all()
    predictions = [{"site_id": e["site_id"], "risk_score": e.get("risk_score")} for e in entries]
    field_results = []
    for e in entries:
        if not e.get("inspections"):
            continue
        latest = e["inspections"][-1]
        field_results.append(
            {
                "site_id": e["site_id"],
                "actual_anomaly_found": latest.get("actual_anomaly_found"),
                "inspected_at": latest.get("inspected_at"),
            }
        )

    result = verify_run({"period": [period, period], "predictions": predictions, "field_results": field_results, "k": k})
    if result["status"] == "error":
        raise HTTPException(500, result["warnings"])
    return result


class InspectionRequest(BaseModel):
    site_id: str
    inspector_id: str
    inspected_at: str
    actual_anomaly_found: bool
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
