"""FastAPI 서버 — ARCHITECTURE.md §7 API 설계.

각 모듈을 import해서 순서대로 호출한다(REST로 쪼개지 않음, §4.2). 서버 시작
시 `data/processed/yongin_yubang_priority_queue.geojson`(§Module RISK 조기
실증 결과)을 읽어 Module O의 인메모리 store를 채운다 — 매 요청마다 Earth
Engine을 다시 부르지 않는다(배치 계산 → 빠른 조회 API라는 §2.2 원칙).

`POST /sites/{site_id}/ask`, `POST /reports/weekly`는 §7 원안에 없던
Module AGENT 연동 엔드포인트다 — §5 Module AGENT의 Q&A 계약을 실제로 쓰려면
필요해서 추가했다(§12 로드맵 참조).
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # GEMINI_API_KEY 등 — 다른 모듈을 import하기 전에 먼저 로드해야 한다

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.geo import geometry_5179_to_4326, point_4326_to_5179
from module_agent.report import generate as agent_generate_report
from module_agent.run import run as agent_run
from module_chg.run import compute_change_from_scenes as chg_compute
from module_field.run import run as field_run
from module_o.routing import run as routing_run
from module_o.run import run as o_run
from module_o.store import store
from module_obs.thumbnail import run as thumbnail_run
from common.wayback import DEFAULT_ZOOM, TILE_URL, deg2num, find_epochs, num2deg
from module_verify.ablation import run as ablation_run
from module_verify.run import run as verify_run

# 영상 판독으로 만든 Ground Truth 라벨(§scripts/import_labels.py) — 있으면 서버 시작 시
# 현장점검 기록으로 함께 적재해 Backtest가 실제 정답지로 채점할 수 있게 한다.
REVIEWED_LABELS_PATH = Path("data/labels/reviewed_labels.json")

SNAPSHOT_PATHS = [
    Path("data/processed/yongin_yubang_priority_queue.geojson"),  # 실증 앵커(용인시 유방동, §3.1)
    Path("data/processed/hanriver_priority_queue.geojson"),  # 다른 시/군/구 표본(§12 B급 확장)
]

# scripts/run_priority_queue_demo.py·run_priority_queue_batch.py와 반드시 동일해야 한다 —
# 썸네일이 배치 파이프라인이 실제로 비교한 기간과 다른 기간의 영상을 보여주면 안 되므로.
BASELINE_PERIOD = ["2024-06-01", "2024-08-31"]
CURRENT_PERIOD = ["2026-06-01", "2026-08-25"]


def _load_reviewed_labels() -> None:
    """판독 라벨을 현장점검 기록으로 적재한다. 파일이 없으면 조용히 넘어간다(§4.2)."""
    if not REVIEWED_LABELS_PATH.exists():
        return
    try:
        records = json.loads(REVIEWED_LABELS_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — 라벨은 부가 자료, 깨져도 서버는 떠야 한다
        return
    for rec in records:
        if store.get(rec.get("site_id")) is not None:
            store.record_inspection(rec["site_id"], rec)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_snapshot()
    _load_reviewed_labels()
    yield


app = FastAPI(title="수변생태벨트 점검 우선순위 지원시스템 API", version="0.1.0", lifespan=lifespan)

# 개발 서버(Next.js)는 매번 다른 포트로 뜰 수 있어(autoPort) localhost 전 포트를 허용한다.
# 배포본은 그것만으로는 부족하므로 ALLOWED_ORIGINS(쉼표 구분)로 실제 도메인을 더한다.
# 예: ALLOWED_ORIGINS=https://waterside-guard.vercel.app
_allowed_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
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
    """스냅샷 GeoJSON(EPSG:5179) 여러 개를 읽어 store를 채운다. 파일이 하나도 없으면 빈
    상태로 시작한다(Module RISK를 아직 안 돌렸다는 뜻 — 예외를 던지지 않고 조용히
    넘어간다, §4.2). site_id 접두어(YUBANG_/HANRIVER_)가 달라 겹치지 않는다."""
    import geopandas as gpd

    for snapshot_path in SNAPSHOT_PATHS:
        if not snapshot_path.exists():
            continue
        _load_one_snapshot(gpd.read_file(snapshot_path))  # EPSG:5179


def _load_one_snapshot(gdf) -> None:
    for row in gdf.itertuples():
        geometry_4326 = geometry_5179_to_4326(row.geometry.__geo_interface__)
        store.upsert_risk_result(
            row.site_id,
            inspection_priority_score=row.inspection_priority_score,
            priority_tier=row.priority_tier,
            contributing_factors=_json_field(row.contributing_factors_json),
            extra={
                "pnu": row.pnu,
                "jibun": row.jibun,
                "addr": row.addr,
                "anomaly_score": row.anomaly_score,
                "change_type_hint": row.change_type_hint,
                "weight_coverage": row.weight_coverage,
                "changed_area_ratio_source": row.changed_area_ratio_source,
                "adjacent_to_water": row.adjacent_to_water,
                "evidence_confidence": _json_field(row.evidence_confidence_json) or None,
                "anomaly_method": row.anomaly_method,
                "seasonal_anomaly": _json_field(row.seasonal_anomaly_json) or None,
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


@app.get("/sites/{site_id}/thumbnails")
def get_thumbnails(site_id: str) -> dict:
    """선택된 대상지 1건에 대해서만 on-demand로 NDVI 썸네일을 생성한다(§ module_obs/thumbnail.py
    구현 상태 참조) — 60개 전부를 미리 만들지 않는다. Earth Engine 호출이라 응답이
    다른 엔드포인트보다 느릴 수 있다(보통 1~3초)."""
    entry = store.get(site_id)
    if entry is None:
        raise HTTPException(404, f"site '{site_id}' not found")
    geometry_4326 = entry.get("geometry_geojson")
    if geometry_4326 is None:
        raise HTTPException(404, f"site '{site_id}' has no geometry")

    baseline = thumbnail_run(
        {"site_id": site_id, "aoi_geometry_4326": geometry_4326, "date_range": BASELINE_PERIOD}
    )
    current = thumbnail_run(
        {"site_id": site_id, "aoi_geometry_4326": geometry_4326, "date_range": CURRENT_PERIOD}
    )
    return {
        "site_id": site_id,
        "baseline": baseline["data"]["thumbnail"],
        "current": current["data"]["thumbnail"],
        "warnings": baseline["warnings"] + current["warnings"],
    }


HIGHRES_GRID = 3  # 3x3 타일 = 약 360m — 필지(수십 m)와 주변 맥락이 함께 보이는 크기
HIGHRES_MAX_EPOCHS = 4  # 최신 시기 우선. 너무 많으면 화면이 무거워진다


def _polygon_centroid(geometry: dict) -> tuple[float, float] | None:
    """꼭짓점 평균 — 타일 중심을 잡는 용도라 정밀할 필요 없다."""
    pts: list[tuple[float, float]] = []

    def walk(coords):
        if not coords:
            return
        if isinstance(coords[0], (int, float)):
            pts.append((coords[0], coords[1]))
            return
        for c in coords:
            walk(c)

    walk(geometry.get("coordinates"))
    if not pts:
        return None
    return sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)


@app.get("/sites/{site_id}/highres")
def get_highres_history(site_id: str) -> dict:
    """Esri Wayback 고해상도(서브미터) 실사 영상을 시기별로 반환한다.

    **왜 필요한가**: Evidence Card의 NDVI 썸네일은 Sentinel-2 10m라, 필지 중앙값
    883㎡(약 3×3 픽셀)를 육안으로 확인할 수 없다. 현장직원이 출동 전에 "이건 갈 만한가"를
    판단하려면 실제로 보이는 영상이 필요하다.

    **서버가 이미지를 합성하지 않는다** — 타일 URL과 지리 범위만 내려주고 브라우저가
    3×3으로 배치한다. 서버에서 합치면 site 하나당 36회 왕복이 응답 시간에 그대로 얹힌다.

    **주의**: `date`는 Esri 배포일이지 촬영일이 아니다(Esri가 촬영일을 공개하지 않는다).
    시기마다 촬영 계절이 달라 초록/갈색 차이가 날 수 있으므로 UI에서 그 점을 안내한다.
    """
    entry = store.get(site_id)
    if entry is None:
        raise HTTPException(404, f"site '{site_id}' not found")
    geometry = entry.get("geometry_geojson")
    if geometry is None:
        raise HTTPException(404, f"site '{site_id}' has no geometry")

    center = _polygon_centroid(geometry)
    if center is None:
        raise HTTPException(404, f"site '{site_id}' geometry has no coordinates")
    lat, lon = center

    epochs_meta = find_epochs(lat, lon)[-HIGHRES_MAX_EPOCHS:]
    cx, cy = deg2num(lat, lon, DEFAULT_ZOOM)
    half = HIGHRES_GRID // 2
    north, west = num2deg(cx - half, cy - half, DEFAULT_ZOOM)
    south, east = num2deg(cx + half + 1, cy + half + 1, DEFAULT_ZOOM)

    epochs = [
        {
            "date": ep["date"],
            "tiles": [
                [
                    TILE_URL.format(release=ep["release"], z=DEFAULT_ZOOM, x=cx + dx, y=cy + dy)
                    for dx in range(-half, half + 1)
                ]
                for dy in range(-half, half + 1)
            ],
        }
        for ep in epochs_meta
    ]

    return {
        "site_id": site_id,
        "grid": HIGHRES_GRID,
        # [서, 북, 동, 남] — 프론트가 필지 폴리곤을 픽셀로 옮길 때 쓴다
        "bounds": [west, north, east, south],
        "geometry_geojson": geometry,
        "epochs": epochs,
    }


@app.get("/sites/{site_id}/evidence")
def get_evidence(site_id: str) -> dict:
    entry = store.get(site_id)
    if entry is None:
        raise HTTPException(404, f"site '{site_id}' not found")
    return {
        "site_id": site_id,
        "inspection_priority_score": entry.get("inspection_priority_score"),
        "priority_tier": entry.get("priority_tier"),
        "contributing_factors": entry.get("contributing_factors", []),
        "anomaly_score": entry.get("anomaly_score"),
        "change_type_hint": entry.get("change_type_hint"),
        # 점수의 신뢰도 맥락 — 이 값들이 없으면 "82점"이 몇 %의 근거로 나온 건지 알 수 없다(§9).
        "weight_coverage": entry.get("weight_coverage"),
        "changed_area_ratio_source": entry.get("changed_area_ratio_source"),
        "evidence_confidence": entry.get("evidence_confidence"),
        "anomaly_method": entry.get("anomaly_method"),
        "seasonal_anomaly": entry.get("seasonal_anomaly"),
    }


@app.get("/priority-queue")
def get_priority_queue(week_of: str = "current") -> dict:
    entries = store.all()
    risk_results = [
        {
            "site_id": e["site_id"],
            "inspection_priority_score": e.get("inspection_priority_score"),
            "priority_tier": e.get("priority_tier"),
            "contributing_factors": e.get("contributing_factors", []),
        }
        for e in entries
    ]
    result = o_run({"week_of": week_of, "risk_results": risk_results})
    if result["status"] == "error":
        raise HTTPException(500, result["warnings"])
    return result


@app.get("/priority-queue/route")
def get_route(budget: int = 10, max_distance_m: int = 3000) -> dict:
    """상위 `budget`곳을 가까운 것끼리 묶고 방문 순서를 정한다(§module_o/routing.py).

    우선순위 큐는 "어디를 먼저 볼 것인가"만 알려주는데, 현장직원은 하루에 여러 곳을 돌아야
    한다 — 1위가 여주, 2위가 가평이면 점수 순서대로 가는 건 비효율이다.

    **거리는 직선거리다**(EPSG:5179 평면). 실제 도로 주행거리가 아니므로 응답의
    `distance_basis`가 "straight_line"으로 표시되고 UI가 그대로 안내한다.
    """
    queue_result = o_run(
        {
            "week_of": "current",
            "risk_results": [
                {
                    "site_id": e["site_id"],
                    "inspection_priority_score": e.get("inspection_priority_score"),
                    "priority_tier": e.get("priority_tier"),
                    "contributing_factors": e.get("contributing_factors", []),
                }
                for e in store.all()
            ],
        }
    )
    top = queue_result["data"]["priority_queue"][:budget]

    sites = []
    for item in top:
        entry = store.get(item["site_id"])
        geometry = entry.get("geometry_geojson") if entry else None
        center = _polygon_centroid(geometry) if geometry else None
        # 거리 계산은 내부 규약대로 EPSG:5179 평면에서 한다(§4.1) — 위경도로 재면 위도에 따라
        # 1도의 실제 거리가 달라져 군집 경계가 지역마다 뒤틀린다.
        xy = None
        if center:
            lat, lon = center
            xy = point_4326_to_5179(lon, lat)
        sites.append(
            {
                "site_id": item["site_id"],
                "rank": item["rank"],
                "xy": xy,
                "addr": entry.get("addr") if entry else None,
                "inspection_priority_score": item.get("inspection_priority_score"),
                "status": item.get("status"),
            }
        )

    result = routing_run({"sites": sites, "max_distance_m": max_distance_m})
    if result["status"] == "error":
        raise HTTPException(500, result["warnings"])

    # 화면이 지도에 선을 그리고 목록을 만들 수 있도록 site 상세를 함께 실어 보낸다
    by_id = {s["site_id"]: s for s in sites}
    for cluster in result["data"]["clusters"]:
        cluster["stops"] = [
            {
                **by_id[stop["site_id"]],
                "xy": None,  # 내부 좌표계는 응답에 노출하지 않는다(§4.1 출력은 4326)
                "lonlat": _lonlat_of(by_id[stop["site_id"]]),
            }
            for stop in cluster["route"]
        ]
    return result


def _lonlat_of(site: dict) -> list[float] | None:
    entry = store.get(site["site_id"])
    geometry = entry.get("geometry_geojson") if entry else None
    center = _polygon_centroid(geometry) if geometry else None
    return [center[1], center[0]] if center else None


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
    predictions = [{"site_id": e["site_id"], "inspection_priority_score": e.get("inspection_priority_score")} for e in entries]
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

    # 비교 baseline — Module VERIFY는 "recency"·"ndvi_only"가 무엇인지 모른다(§ 경계 설계).
    # 도메인을 아는 여기(호출부)가 랭킹을 만들어 넘기고, VERIFY는 채점만 한다.
    # 이 세 가지를 함께 보여줘야 "우선순위화가 실제로 기여했는가"를 말할 수 있다:
    #   - ndvi_only: 위성 이상도 하나만 보고 줄 세우면? (다요인 결합의 가치 검증)
    #   - recency: 마지막 점검일만 보고 줄 세우면? (위성 없이 관리대장만으로 되는지 검증)
    baseline_predictions = {
        "ndvi_only": [
            {"site_id": e["site_id"], "score": e.get("anomaly_score") or 0} for e in entries
        ],
        "recency": [
            {
                "site_id": e["site_id"],
                "score": next(
                    (f["value"] or 0 for f in e.get("contributing_factors", []) if f["factor"] == "last_inspection_days_ago"),
                    0,
                ),
            }
            for e in entries
        ],
    }

    result = verify_run(
        {
            "period": [period, period],
            "predictions": predictions,
            "field_results": field_results,
            "baseline_predictions": baseline_predictions,
            "k": k,
        }
    )
    if result["status"] == "error":
        raise HTTPException(500, result["warnings"])
    return result


@app.get("/verify/ablation")
def get_ablation(k: int = 10) -> dict:
    """계절 기준선의 기여도와 상위권 오염 여부 — **라벨 없이도 낼 수 있는 근거**.

    `/verify/backtest`는 실제 현장 결과와 대조하는데, 이 프로토타입은 그 라벨이 없다.
    이 엔드포인트는 대신 "방법을 켰을 때와 껐을 때 순위가 어떻게 달라지는가"를 비교한다 —
    정확도가 아니라 **기여도**다(§module_verify/ablation.py).

    두 기간 차분 점수는 저장돼 있지 않으므로 스냅샷의 scene 원자료로 다시 계산한다 —
    실제 파이프라인과 같은 함수(`compute_change_from_scenes`)를 쓰므로 값이 어긋날 수 없다.
    """
    sites = []
    for entry in store.all():
        seasonal = entry.get("seasonal_anomaly") or {}
        baseline_scenes = entry.get("baseline_scenes") or []
        current_scenes = entry.get("current_scenes") or []
        # 계절 기준선을 빼고 같은 함수를 다시 돌려 "그 방법이 없었다면" 점수를 얻는다
        without_seasonal = chg_compute(baseline_scenes, current_scenes)
        sites.append(
            {
                "site_id": entry["site_id"],
                "seasonal_score": seasonal.get("seasonal_anomaly_score"),
                "two_period_score": without_seasonal.get("anomaly_score") if without_seasonal else None,
                "robust_z": seasonal.get("robust_z"),
            }
        )

    result = ablation_run({"sites": sites, "k": k})
    if result["status"] == "error":
        raise HTTPException(500, result["warnings"])
    return result


class InspectionRequest(BaseModel):
    site_id: str
    inspector_id: str
    inspected_at: str
    actual_anomaly_found: bool
    verdict: str | None = None  # "yes" | "no" | "uncertain" — 보류를 음성과 구분(§module_field)
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


class AskTurn(BaseModel):
    role: str
    text: str


class AskRequest(BaseModel):
    question: str
    # 직전 대화 — 후속 질문이 앞 맥락을 잃지 않게 클라이언트가 함께 보낸다.
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
