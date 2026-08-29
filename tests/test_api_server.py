"""api_server.py 통합 테스트. 실제 스냅샷 파일이나 GEE 자격증명에 의존하지
않도록 store를 직접 시드한다 — module_o.store가 프로세스 전역 싱글턴이라
api_server.py가 import하는 것과 동일한 인스턴스다.
"""
import pytest
from fastapi.testclient import TestClient

from api_server import app
from module_o.store import store


@pytest.fixture(autouse=True)
def _seed_store():
    store.reset()
    store.upsert_risk_result(
        "A1037",
        risk_score=54,
        risk_tier="2순위",
        contributing_factors=[{"factor": "anomaly_score_mean", "value": 0.72, "weight": 0.35}],
        extra={
            "pnu": "4146110500100780003",
            "addr": "경기도 용인시 처인구 유방동 78-3",
            "anomaly_score": 0.72,
            "change_type_hint": "vegetation_decline",
            "geometry_geojson": {"type": "Polygon", "coordinates": []},
            "baseline_scenes": [{"acquisition_date": "2024-06-10", "indices": {"ndvi_mean": 0.7}}],
            "current_scenes": [{"acquisition_date": "2026-06-10", "indices": {"ndvi_mean": 0.4}}],
        },
    )
    yield
    store.reset()


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["sites_loaded"] == 1


def test_list_sites():
    r = client.get("/sites")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["site_id"] == "A1037"


def test_get_site_404():
    r = client.get("/sites/NOPE")
    assert r.status_code == 404


def test_get_site_found():
    r = client.get("/sites/A1037")
    assert r.status_code == 200
    assert r.json()["risk_score"] == 54


def test_evidence():
    r = client.get("/sites/A1037/evidence")
    assert r.status_code == 200
    body = r.json()
    assert body["risk_tier"] == "2순위"
    assert body["contributing_factors"][0]["factor"] == "anomaly_score_mean"


def test_timeseries():
    r = client.get("/sites/A1037/timeseries")
    assert r.status_code == 200
    body = r.json()
    assert len(body["baseline_scenes"]) == 1
    assert len(body["current_scenes"]) == 1


def test_priority_queue():
    r = client.get("/priority-queue")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["priority_queue"][0]["site_id"] == "A1037"
    assert body["data"]["priority_queue"][0]["status"] == "미점검"


def test_create_inspection_updates_status():
    payload = {
        "site_id": "A1037",
        "inspector_id": "staff_003",
        "inspected_at": "2026-09-02T10:15:00+09:00",
        "actual_anomaly_found": True,
        "anomaly_category": "식생교란",
        "note": "동측 사면 나지 노출 확인",
    }
    r = client.post("/inspections", json=payload)
    assert r.status_code == 200
    assert r.json()["data"]["inspection_id"] == "INSP-20260902-A1037"

    r2 = client.get("/priority-queue")
    assert r2.json()["data"]["priority_queue"][0]["status"] == "점검완료"


def test_create_inspection_invalid_category_rejected():
    payload = {
        "site_id": "A1037",
        "inspector_id": "staff_003",
        "inspected_at": "2026-09-02T10:15:00+09:00",
        "actual_anomaly_found": True,
        "anomaly_category": "외계인출현",
    }
    r = client.post("/inspections", json=payload)
    assert r.status_code == 400
