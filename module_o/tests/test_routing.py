"""공간 군집화·경로 테스트 — 좌표를 직접 지정해 기하학적으로 검증한다."""
from module_o.routing import cluster_sites, order_route, route_length_m, run


def _s(sid, x, y, rank=None):
    return {"site_id": sid, "xy": (x, y), "rank": rank}


def test_clusters_split_by_distance_threshold():
    """1km 떨어진 둘은 한 군집, 10km 떨어진 셋째는 따로."""
    sites = [_s("A", 0, 0), _s("B", 1000, 0), _s("C", 10000, 0)]
    clusters = cluster_sites(sites, max_distance_m=3000)
    assert sorted(len(c) for c in clusters) == [1, 2]


def test_single_linkage_chains_through_intermediate():
    """A-B 2km, B-C 2km면 A-C가 4km라도 사슬로 이어져 한 군집이다 — 한 번에 도는 묶음이 목적이므로."""
    sites = [_s("A", 0, 0), _s("B", 2000, 0), _s("C", 4000, 0)]
    clusters = cluster_sites(sites, max_distance_m=3000)
    assert len(clusters) == 1 and len(clusters[0]) == 3


def test_route_starts_at_given_index_and_visits_all():
    sites = [_s("A", 0, 0), _s("B", 100, 0), _s("C", 50, 0)]
    route = order_route(sites, start_index=0)
    assert route[0]["site_id"] == "A"
    assert {s["site_id"] for s in route} == {"A", "B", "C"}


def test_two_opt_beats_naive_order_on_crossing_layout():
    """일부러 교차하는 순서를 주면 2-opt가 총 거리를 줄여야 한다."""
    square = [_s("A", 0, 0), _s("B", 0, 100), _s("C", 100, 100), _s("D", 100, 0)]
    crossing = [square[0], square[2], square[1], square[3]]
    optimized = order_route(square, start_index=0)
    assert route_length_m(optimized) < route_length_m(crossing)


def test_cluster_order_follows_priority_not_distance():
    """급한 필지가 있는 군집이 먼저 와야 한다 — 거리만 보면 한가한 군집을 먼저 가라고 하게 된다."""
    sites = [_s("FAR_URGENT", 50000, 0, rank=1), _s("NEAR_IDLE", 0, 0, rank=40)]
    result = run({"sites": sites, "max_distance_m": 1000})
    assert result["data"]["clusters"][0]["site_ids"] == ["FAR_URGENT"]


def test_radius_and_length_are_reported():
    sites = [_s("A", 0, 0, 1), _s("B", 1000, 0, 2)]
    c = run({"sites": sites})["data"]["clusters"][0]
    assert c["size"] == 2
    assert c["route_length_m"] == 1000
    assert c["radius_m"] == 500
    assert c["top_rank"] == 1


def test_sites_without_coordinates_are_skipped_with_warning():
    sites = [_s("A", 0, 0, 1), {"site_id": "NOGEO", "xy": None, "rank": 2}]
    result = run({"sites": sites})
    assert result["status"] == "degraded"
    assert any("좌표가 없어" in w for w in result["warnings"])
    assert result["data"]["cluster_count"] == 1


def test_distance_basis_is_declared_as_straight_line():
    """실제 도로 거리가 아니라는 사실이 데이터에 남아야 UI가 그대로 표기할 수 있다."""
    assert run({"sites": [_s("A", 0, 0, 1)]})["data"]["distance_basis"] == "straight_line"


def test_empty_input_returns_empty_clusters():
    assert run({"sites": []})["data"]["clusters"] == []


def test_reports_savings_versus_naive_rank_order():
    """순위대로 도는 것보다 군집을 고려한 순서가 짧아야 한다 —
    이 수치가 없으면 '군집을 만들었다'는 사실만 있고 그게 왜 좋은지는 말할 수 없다."""
    # 1위와 3위가 왼쪽, 2위와 4위가 오른쪽에 있어 순위대로 가면 좌우를 왕복하게 된다
    sites = [
        _s("L1", 0, 0, 1),
        _s("R1", 50000, 0, 2),
        _s("L2", 500, 0, 3),
        _s("R2", 50500, 0, 4),
    ]
    data = run({"sites": sites, "max_distance_m": 3000})["data"]
    assert data["cluster_count"] == 2
    assert data["clustered_order_length_m"] < data["naive_order_length_m"]
    assert data["saved_pct"] > 0
    # 방문 순서는 왼쪽 둘을 먼저 처리하고 오른쪽으로 넘어가야 한다
    assert [v["rank"] for v in data["visit_order"]] == [1, 3, 2, 4]
