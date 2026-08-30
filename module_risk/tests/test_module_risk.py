from module_risk.run import run


def test_missing_features_returns_degraded():
    result = run({"site_id": "A1037"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_architecture_example_reproduces_score_51():
    # ARCHITECTURE.md §5 Module RISK 예시값 재현(2026-08-30, SAR·최근강우 요인 추가 후
    # 실제 코드 실행 결과로 문서를 맞춤 — 요인 추가 전에는 54점이었다)
    result = run(
        {
            "site_id": "A1037",
            "features": {
                "anomaly_score_mean": 0.72,
                "changed_area_ratio": 0.18,
                "sar_anomaly_mean": 0.4,
                "recent_rainfall_mm": 20.0,
                "adjacent_to_water": True,
                "restoration_elapsed_days": 420,
                "last_inspection_days_ago": 63,
                "past_anomaly_count": 1,
            },
        }
    )
    assert result["status"] == "ok"
    assert result["data"]["inspection_priority_score"] == 51
    assert result["data"]["priority_tier"] == "2순위"
    assert result["data"]["source"] == "rule_based"
    factors = {f["factor"] for f in result["data"]["contributing_factors"]}
    assert factors == {
        "anomaly_score_mean",
        "changed_area_ratio",
        "sar_anomaly_mean",
        "recent_rainfall_mm",
        "last_inspection_days_ago",
        "adjacent_to_water",
        "past_anomaly_count",
    }


def test_all_zero_features_yields_normal_tier():
    result = run(
        {
            "site_id": "A2000",
            "features": {
                "anomaly_score_mean": 0.0,
                "changed_area_ratio": 0.0,
                "adjacent_to_water": False,
                "restoration_elapsed_days": 100,
                "last_inspection_days_ago": 0,
                "past_anomaly_count": 0,
            },
        }
    )
    assert result["data"]["inspection_priority_score"] == 0
    assert result["data"]["priority_tier"] == "정상"


def test_missing_site_attribute_factors_degrade_but_still_score():
    result = run(
        {
            "site_id": "A3000",
            "features": {
                "anomaly_score_mean": 0.9,
                "changed_area_ratio": 0.5,
                "adjacent_to_water": None,
                "restoration_elapsed_days": None,
                "last_inspection_days_ago": None,
                "past_anomaly_count": None,
            },
        }
    )
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 2
    assert result["data"]["inspection_priority_score"] > 0  # anomaly/changed_area만으로도 부분 점수는 나온다
    factors = {f["factor"] for f in result["data"]["contributing_factors"]}
    assert factors == {"anomaly_score_mean", "changed_area_ratio"}
    # 결측 요인은 0으로 묻어버리지 않고 가중치에서 빼서 재정규화한다 — 남은 두 요인의
    # 가중치 합(0.30+0.15)이 coverage로 그대로 노출돼야 한다.
    assert result["data"]["weight_coverage"] == 0.45
    assert any("재정규화" in w for w in result["warnings"])


def test_missing_factors_are_renormalized_not_penalized():
    """2026-08-31 회귀 테스트 — 예전에는 결측 요인의 가중치를 그냥 빼먹어서, 가진 요인이
    전부 만점이어도 구조적으로 낮은 점수가 나왔다(60개 site 전부 1순위가 안 나오던 원인).
    이제는 남은 가중치로 재정규화하므로 두 경우가 같은 100점이어야 한다."""
    maxed = {
        "anomaly_score_mean": 1.0,
        "changed_area_ratio": 1.0,
        "sar_anomaly_mean": 1.0,
        "recent_rainfall_mm": 100.0,
        "last_inspection_days_ago": 365,
        "adjacent_to_water": True,
        "past_anomaly_count": 5,
    }
    full = run({"site_id": "FULL", "features": maxed})["data"]
    partial = run({"site_id": "PARTIAL", "features": {**maxed, "last_inspection_days_ago": None, "adjacent_to_water": None, "past_anomaly_count": None}})["data"]

    assert full["inspection_priority_score"] == 100
    assert partial["inspection_priority_score"] == 100  # 재정규화 전에는 65였다
    assert full["weight_coverage"] == 1.0
    assert partial["weight_coverage"] == 0.65  # 대신 근거가 65%뿐이라는 사실은 그대로 노출


def test_tier_boundaries():
    def score_for(anomaly):
        return run(
            {
                "site_id": "X",
                "features": {
                    "anomaly_score_mean": anomaly,
                    "changed_area_ratio": 0.0,
                    "adjacent_to_water": False,
                    "restoration_elapsed_days": 0,
                    "last_inspection_days_ago": 0,
                    "past_anomaly_count": 0,
                },
            }
        )["data"]

    # sar_anomaly_mean·recent_rainfall_mm이 없어 coverage 0.8로 재정규화 -> 0.30/0.80 = 38
    assert score_for(1.0)["priority_tier"] == "3순위"
    assert score_for(0.0)["priority_tier"] == "정상"
