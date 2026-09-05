"""도로 실거리(주행거리) 조회 — module_o/routing.py 확장.

**배경**: routing.py는 지금까지 EPSG:5179 평면 직선거리로만 군집·동선을 계산했다.
산·강을 사이에 둔 두 필지는 직선으로 가까워도 실제로는 크게 돌아가야 할 수 있다 —
그 사실을 데이터에 `distance_basis: "straight_line"`으로 정직하게 표기해 왔다
(원래는 "외부 의존성이 늘어난다"는 이유로 범위 밖에 뒀다, ARCHITECTURE.md §Module O).

**이 모듈이 하는 일**: OSRM(Open Source Routing Machine)의 공개 데모 서버로 실제
도로망 기준 주행거리 행렬을 받아온다. API 키가 필요 없고 OpenStreetMap 도로망만
쓰므로, 이 프로젝트가 지금까지 지켜온 "무상 공개 자료만 쓴다" 원칙과 같은 선상이다.

**정직하게 밝혀둘 한계**: router.project-osrm.org는 데모·공익 목적으로 무상 운영되는
서버이지 상용 SLA가 있는 서비스가 아니다. 트래픽이 몰리거나 일시 장애가 있을 수
있으므로, 실패하면 예외를 던지지 않고 None을 반환해 호출부가 직선거리로 폴백하게
한다 — common/weather.py와 동일한 graceful degradation 패턴이다.
"""
from __future__ import annotations

import requests

OSRM_TABLE_URL = "https://router.project-osrm.org/table/v1/driving/{coords}"
REQUEST_TIMEOUT_S = 12
MAX_POINTS = 100  # OSRM 공개 데모 서버의 관행적 상한 — 이 프로젝트의 주간 배정 규모(최대 30곳)면 충분


def fetch_road_distance_matrix_m(points_lonlat: list[tuple[float, float]]) -> list[list[float]] | None:
    """점 목록(lon, lat 순서)에 대응하는 pairwise 도로 주행거리(m) 행렬을 반환한다.

    반환값은 입력과 같은 순서의 n×n 행렬. 좌표가 2개 미만이거나, 요청이 실패하거나,
    행렬 일부에 경로를 찾지 못한 칸(null)이 있으면 전부 포기하고 None을 반환한다 —
    일부만 도로거리이고 나머지는 직선거리인 뒤섞인 결과를 만들지 않기 위해서다
    (distance_basis 하나로 전체를 정직하게 표시할 수 있게).
    """
    if len(points_lonlat) < 2 or len(points_lonlat) > MAX_POINTS:
        return None
    try:
        coords = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in points_lonlat)
        resp = requests.get(
            OSRM_TABLE_URL.format(coords=coords),
            params={"annotations": "distance"},
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != "Ok":
            return None
        distances = payload.get("distances")
        if not distances or any(cell is None for row in distances for cell in row):
            return None
        return distances
    except Exception:  # noqa: BLE001 — best-effort 부가 조회, 실패해도 나머지 파이프라인은 계속 작동해야 한다
        return None
