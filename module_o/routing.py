"""공간 군집화·방문 순서 — ARCHITECTURE.md §5 Module O 확장(2026-08-31, 리서치 P2).

**왜 필요한가**: 우선순위 큐는 "어디를 먼저 볼 것인가"를 알려주지만, 실제 현장직원은
하루에 여러 곳을 돌아야 한다. 1위가 여주, 2위가 가평이면 점수 순서대로 가는 건 비효율이다.
가까운 필지끼리 묶어 한 번의 출장으로 처리하면 같은 인력으로 더 많이 볼 수 있다.

**거리 기준 — 도로 실거리를 우선하고, 안 되면 직선거리로 정직하게 폴백한다(2026-09-02)**:
모든 site에 위경도(`lonlat`)가 있으면 `common/road_distance.py`로 OSRM 공개 데모 서버에
실제 도로망 기준 주행거리 행렬을 조회한다. 실패하거나(네트워크 장애 등) 좌표가 없으면
EPSG:5179 평면 직선거리로 자동 폴백한다 — 절대 일부만 도로거리, 일부만 직선거리로
뒤섞지 않는다. 어느 쪽을 썼는지는 `distance_basis`("driving" | "straight_line")로 항상
표시하고, UI가 그 값을 보고 문구를 바꾼다.

**군집 알고리즘**: single-linkage(연결 요소) — "서로 max_distance 안에 있으면 같은 군집".
DBSCAN 같은 밀도 기반이 아니라 단순 연결로 충분한 이유는, 우리 목적이 "밀집 구역 탐지"가
아니라 "한 번에 갈 수 있는 묶음"이라서다. sklearn 의존성 없이 union-find로 구현한다.

**경로**: nearest-neighbor로 초기 순서를 잡고 2-opt로 개선한다. 필지 수가 수십 개
수준이라 최적해를 구할 필요도, TSP 솔버를 들일 이유도 없다.
"""
from __future__ import annotations

import math

from common.envelope import error_envelope, make_envelope
from common.road_distance import fetch_road_distance_matrix_m

DEFAULT_CLUSTER_DISTANCE_M = 3000  # 이 거리 안이면 "한 번에 갈 만하다"(초기 가정치)
MAX_TWO_OPT_PASSES = 20  # 수십 개 규모에서 이 정도면 충분히 수렴한다


def _straight_line_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Distances:
    """두 site 사이 거리를 구한다 — 도로 실거리가 있으면 그걸, 없으면 직선거리를 쓴다.

    site_id 쌍으로 조회하므로 군집 전체에서 구한 행렬을 부분집합(개별 군집 안 순서
    재배열 등)에도 그대로 재사용할 수 있다.
    """

    def __init__(self, road_m: dict[tuple[str, str], float] | None = None):
        self._road = road_m or {}

    def between(self, a: dict, b: dict) -> float:
        key = (a["site_id"], b["site_id"])
        if key in self._road:
            return self._road[key]
        if (rkey := (b["site_id"], a["site_id"])) in self._road:
            return self._road[rkey]
        return _straight_line_m(a["xy"], b["xy"])


_STRAIGHT_LINE = Distances()  # distances 인자를 생략한 기존 호출부와 100% 동일하게 동작


def cluster_sites(
    sites: list[dict], max_distance_m: float = DEFAULT_CLUSTER_DISTANCE_M, distances: Distances = _STRAIGHT_LINE
) -> list[list[dict]]:
    """서로 max_distance_m 안에 있는 site들을 같은 군집으로 묶는다(single-linkage).

    sites: [{"site_id", "xy": (x_5179, y_5179), ...}]
    반환: 군집 리스트. 각 군집은 입력 dict 그대로(순서는 입력 순).
    """
    n = len(sites)
    if n == 0:
        return []

    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]  # 경로 압축
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if distances.between(sites[i], sites[j]) <= max_distance_m:
                union(i, j)

    groups: dict[int, list[dict]] = {}
    for i, site in enumerate(sites):
        groups.setdefault(find(i), []).append(site)
    return list(groups.values())


def route_length_m(ordered: list[dict], distances: Distances = _STRAIGHT_LINE) -> float:
    return sum(distances.between(ordered[i], ordered[i + 1]) for i in range(len(ordered) - 1))


def order_route(sites: list[dict], start_index: int = 0, distances: Distances = _STRAIGHT_LINE) -> list[dict]:
    """방문 순서를 정한다 — nearest-neighbor 후 2-opt 개선.

    시작점은 기본적으로 우선순위가 가장 높은 필지(호출부가 정렬해서 넘긴다) — 최단거리만
    보고 시작점을 정하면 "제일 급한 곳을 마지막에 가는" 결과가 나올 수 있다.
    """
    if len(sites) <= 2:
        return list(sites)

    remaining = list(sites)
    route = [remaining.pop(start_index)]
    while remaining:
        last = route[-1]
        nearest = min(range(len(remaining)), key=lambda i: distances.between(last, remaining[i]))
        route.append(remaining.pop(nearest))

    # 2-opt — 교차하는 구간을 뒤집어 총 거리를 줄인다. 시작점은 고정한다.
    improved = True
    passes = 0
    while improved and passes < MAX_TWO_OPT_PASSES:
        improved = False
        passes += 1
        for i in range(1, len(route) - 1):
            for j in range(i + 1, len(route)):
                candidate = route[:i] + route[i : j + 1][::-1] + route[j + 1 :]
                if route_length_m(candidate, distances) < route_length_m(route, distances) - 1e-6:
                    route = candidate
                    improved = True
    return route


def _road_distances_or_fallback(sites: list[dict]) -> tuple[Distances, str, str | None]:
    """모든 site에 lonlat이 있으면 도로 실거리 행렬을 시도한다.

    반환: (Distances, distance_basis, warning|None). 좌표 결측·조회 실패 어느 쪽이든
    직선거리로 조용히, 그러나 distance_basis에는 정직하게 남기고 폴백한다.
    """
    if len(sites) < 2:
        return _STRAIGHT_LINE, "straight_line", None
    if not all(s.get("lonlat") for s in sites):
        return _STRAIGHT_LINE, "straight_line", None

    matrix = fetch_road_distance_matrix_m([s["lonlat"] for s in sites])
    if matrix is None:
        return _STRAIGHT_LINE, "straight_line", "도로 실거리 조회에 실패해 직선거리로 대체함"

    road_m = {
        (si["site_id"], sj["site_id"]): matrix[i][j]
        for i, si in enumerate(sites)
        for j, sj in enumerate(sites)
        if i != j
    }
    return Distances(road_m), "driving", None


def run(input: dict) -> dict:
    """input: {"sites": [{"site_id", "xy", ...}], "max_distance_m": int}

    output(data): {"clusters": [{cluster_id, site_ids, route, size, route_length_m, radius_m}], ...}
    """
    sites = input.get("sites")
    if sites is None:
        return error_envelope("sites가 필요합니다.", fallback_tier=3)

    usable = [s for s in sites if s.get("xy") is not None]
    skipped = len(sites) - len(usable)

    distances, distance_basis, distance_warning = _road_distances_or_fallback(usable)

    max_distance_m = input.get("max_distance_m", DEFAULT_CLUSTER_DISTANCE_M)
    clusters = cluster_sites(usable, max_distance_m, distances)

    # 군집 순서는 "그 안에서 가장 급한 필지"의 우선순위를 따른다 — 거리만 보고 정렬하면
    # 한가한 군집을 먼저 가라고 말하게 된다.
    def cluster_rank(group: list[dict]) -> int:
        return min(s.get("rank", 10**6) for s in group)

    clusters.sort(key=cluster_rank)

    out = []
    for i, group in enumerate(clusters, start=1):
        ordered = sorted(group, key=lambda s: s.get("rank", 10**6))
        route = order_route(ordered, start_index=0, distances=distances)
        cx = sum(s["xy"][0] for s in group) / len(group)
        cy = sum(s["xy"][1] for s in group) / len(group)
        out.append(
            {
                "cluster_id": i,
                "size": len(group),
                "site_ids": [s["site_id"] for s in group],
                "route": [{"site_id": s["site_id"], "rank": s.get("rank")} for s in route],
                "route_length_m": round(route_length_m(route, distances)),
                # 군집이 얼마나 지리적으로 퍼져 있는지 — 늘 직선거리다("반경 2km 안 6곳"은
                # 도로를 도는 거리가 아니라 지도 위 퍼짐 정도를 말하는 것이라서 바꾸지 않는다)
                "radius_m": round(max(_straight_line_m((cx, cy), s["xy"]) for s in group)),
                "top_rank": cluster_rank(group),
            }
        )

    # 이 기능의 가치는 군집 목록 자체가 아니라 **얼마나 덜 움직이는가**다.
    # 비교 대상: 우선순위 순서대로 그냥 도는 경우(1위 -> 2위 -> ... -> N위).
    by_rank = sorted(usable, key=lambda s: s.get("rank", 10**6))
    naive_length = route_length_m(by_rank, distances)

    # 군집 순서(급한 군집 먼저)로 돌되 군집 안에서는 최적 순서를 쓰는 경우
    clustered_order: list[dict] = []
    for group in clusters:
        ordered = sorted(group, key=lambda s: s.get("rank", 10**6))
        clustered_order.extend(order_route(ordered, start_index=0, distances=distances))
    clustered_length = route_length_m(clustered_order, distances)
    saved = naive_length - clustered_length

    warnings = []
    if skipped:
        warnings.append(f"{skipped}개 site는 좌표가 없어 군집에서 제외됨")
    if distance_warning:
        warnings.append(distance_warning)

    return make_envelope(
        {
            "clusters": out,
            "cluster_count": len(out),
            "max_distance_m": max_distance_m,
            "total_route_length_m": sum(c["route_length_m"] for c in out),
            # 순위대로 도는 경우 vs 군집을 고려한 경우 — 이 비교가 기능의 근거다
            "naive_order_length_m": round(naive_length),
            "clustered_order_length_m": round(clustered_length),
            "saved_length_m": round(saved),
            "saved_pct": round(saved / naive_length * 100, 1) if naive_length > 0 else 0.0,
            "visit_order": [{"site_id": s["site_id"], "rank": s.get("rank")} for s in clustered_order],
            # 도로 실거리를 썼는지 직선거리로 폴백했는지 — UI가 이 값을 보고 문구를 띄운다
            "distance_basis": distance_basis,
        },
        status="ok" if not warnings else "degraded",
        fallback_tier=1 if not warnings else 2,
        warnings=warnings,
    )
