"""기여도·안정성 검증 테스트 — 라벨 없이 낼 수 있는 근거가 실제로 계산되는지."""
from module_verify.ablation import compare_methods, run


def _site(sid, seasonal, two_period, z):
    return {"site_id": sid, "seasonal_score": seasonal, "two_period_score": two_period, "robust_z": z}


def test_detects_site_dropped_by_seasonal_baseline():
    """두 기간 차분에서는 1위인데 계절 기준선에서는 밀려나고, 그 이유가 '정상 범위 안'인 경우 —
    이게 계절 오탐을 걸러냈다는 직접 증거다."""
    sites = [
        _site("SEASONAL_ARTIFACT", 0.05, 0.99, 0.4),  # 변화량은 크지만 해마다 있는 변동
        _site("REAL_CHANGE", 0.95, 0.30, -8.0),
        _site("C", 0.10, 0.10, 0.5),
    ]
    result = compare_methods(sites, k=1)
    dropped = result["dropped_out_of_top_k"]
    assert [d["site_id"] for d in dropped] == ["SEASONAL_ARTIFACT"]
    assert dropped[0]["within_normal_range"] is True  # 밀려난 이유가 근거로 남는다
    assert [e["site_id"] for e in result["entered_top_k"]] == ["REAL_CHANGE"]


def test_flags_normal_range_site_polluting_top_k():
    """상위권에 '과거 정상 범위를 벗어나지 않은' 필지가 있으면 경고해야 한다."""
    sites = [_site("A", 0.9, 0.9, 0.3), _site("B", 0.1, 0.1, -9.0)]
    result = run({"sites": sites, "k": 1})
    assert result["data"]["top_k_within_normal_range"] == ["A"]
    assert result["status"] == "degraded"
    assert any("오염" in w for w in result["warnings"])


def test_clean_top_k_produces_no_warning():
    sites = [_site("A", 0.9, 0.9, -7.0), _site("B", 0.1, 0.1, 0.2)]
    result = run({"sites": sites, "k": 1})
    assert result["data"]["top_k_within_normal_range"] == []
    assert result["status"] == "ok"


def test_sites_missing_either_score_are_excluded():
    sites = [_site("A", None, 0.9, -5.0), _site("B", 0.8, None, -5.0), _site("C", 0.7, 0.7, -5.0)]
    result = compare_methods(sites, k=1)
    assert result["comparable_site_count"] == 1


def test_empty_input_does_not_crash():
    result = run({"sites": []})
    assert result["data"]["comparable_site_count"] == 0
    assert result["status"] == "degraded"
