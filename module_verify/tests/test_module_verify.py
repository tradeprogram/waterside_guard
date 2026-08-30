from module_verify.run import run


def test_missing_input_returns_degraded():
    result = run({"period": ["2026-09-01", "2026-09-30"]})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_no_labeled_sites_returns_degraded():
    result = run(
        {
            "period": ["2026-09-01", "2026-09-30"],
            "predictions": [{"site_id": "A", "inspection_priority_score": 90}],
            "field_results": [],
        }
    )
    assert result["status"] == "degraded"
    assert result["data"]["labeled_site_count"] == 0


def test_perfect_ranking_gives_precision_1():
    # 5개 라벨: 상위 2개(A,B)가 실제 양성, 나머지 3개는 음성. proposed가 정확히 그 순서로 랭킹.
    predictions = [
        {"site_id": "A", "inspection_priority_score": 90},
        {"site_id": "B", "inspection_priority_score": 80},
        {"site_id": "C", "inspection_priority_score": 70},
        {"site_id": "D", "inspection_priority_score": 60},
        {"site_id": "E", "inspection_priority_score": 50},
    ]
    field_results = [
        {"site_id": "A", "actual_anomaly_found": True},
        {"site_id": "B", "actual_anomaly_found": True},
        {"site_id": "C", "actual_anomaly_found": False},
        {"site_id": "D", "actual_anomaly_found": False},
        {"site_id": "E", "actual_anomaly_found": False},
    ]
    result = run(
        {"period": ["2026-09-01", "2026-09-30"], "predictions": predictions, "field_results": field_results, "k": 2}
    )

    assert result["status"] == "ok"
    assert result["data"]["precision_at_k"]["value"] == 1.0
    assert result["data"]["labeled_site_count"] == 5
    assert result["data"]["positive_count"] == 2
    # random baseline 기대 precision = 양성비율 = 2/5 = 0.4
    random_entry = next(b for b in result["data"]["baseline_comparison"] if b["baseline"] == "random")
    assert random_entry["precision_at_k"] == 0.4


def test_inverted_ranking_gives_precision_0():
    predictions = [
        {"site_id": "A", "inspection_priority_score": 10},
        {"site_id": "B", "inspection_priority_score": 20},
        {"site_id": "C", "inspection_priority_score": 90},
        {"site_id": "D", "inspection_priority_score": 80},
    ]
    field_results = [
        {"site_id": "A", "actual_anomaly_found": True},
        {"site_id": "B", "actual_anomaly_found": True},
        {"site_id": "C", "actual_anomaly_found": False},
        {"site_id": "D", "actual_anomaly_found": False},
    ]
    result = run(
        {"period": ["2026-09-01", "2026-09-30"], "predictions": predictions, "field_results": field_results, "k": 2}
    )
    assert result["data"]["precision_at_k"]["value"] == 0.0
    assert result["data"]["recall_at_top20pct"] == 0.0


def test_baseline_predictions_are_scored():
    predictions = [
        {"site_id": "A", "inspection_priority_score": 90},
        {"site_id": "B", "inspection_priority_score": 10},
    ]
    field_results = [
        {"site_id": "A", "actual_anomaly_found": True},
        {"site_id": "B", "actual_anomaly_found": False},
    ]
    result = run(
        {
            "period": ["2026-09-01", "2026-09-30"],
            "predictions": predictions,
            "field_results": field_results,
            "k": 1,
            "baseline_predictions": {
                "ndvi_threshold": [{"site_id": "A", "score": 1}, {"site_id": "B", "score": 2}],
            },
        }
    )
    baselines = {b["baseline"]: b["precision_at_k"] for b in result["data"]["baseline_comparison"]}
    assert baselines["proposed"] == 1.0
    assert baselines["ndvi_threshold"] == 0.0  # B가 1위인데 실제로는 음성
    assert "random" in baselines


def test_data_leakage_flagged_as_warning():
    predictions = [{"site_id": "A", "inspection_priority_score": 90, "predicted_at": "2026-09-05"}]
    field_results = [
        {"site_id": "A", "actual_anomaly_found": True, "inspected_at": "2026-09-01"}  # 예측보다 이전 관측
    ]
    result = run({"period": ["2026-09-01", "2026-09-30"], "predictions": predictions, "field_results": field_results})
    assert result["status"] == "degraded"
    assert any("data leakage" in w for w in result["warnings"])


def test_no_leakage_when_inspection_after_prediction():
    predictions = [{"site_id": "A", "inspection_priority_score": 90, "predicted_at": "2026-09-01"}]
    field_results = [{"site_id": "A", "actual_anomaly_found": True, "inspected_at": "2026-09-05"}]
    result = run({"period": ["2026-09-01", "2026-09-30"], "predictions": predictions, "field_results": field_results})
    assert result["status"] == "ok"
    assert result["warnings"] == []
