"""Module VERIFY — 검증/Backtest 엔진 (ARCHITECTURE.md §5 Module VERIFY, §10 Backtest).

"예측 정확도는 어디 있습니까?"라는 심사질문에 답하는 유일한 모듈. Module
RISK와 동급 우선순위(§5).

**설계 결정**: Module VERIFY는 "recency"·"ndvi_threshold" 같은 baseline을
스스로 계산하지 않는다 — 그건 GIS·NDVI 세부사항을 알아야 하는 도메인
로직이고, 이 모듈의 책임 밖이다(§0.4 "위험도를 계산하지 않는다"와 같은
경계 원칙을 검증에도 적용). 대신 `baseline_predictions`로 이미 계산된
대체 랭킹을 받아 채점만 한다 — "random"만 분석적으로 계산해 항상 제공한다
(무작위 랭킹의 기대 정밀도는 양성 비율과 같다는 사실 자체가 계산이지,
도메인 지식이 아니기 때문).

**data leakage 금지 가드**: `predictions[].predicted_at`과
`field_results[].inspected_at`이 둘 다 있으면 inspected_at이 predicted_at
이전(또는 같음)인 사이트는 사후 확보된 관측이 예측에 새어 들어갔을 수 있다는
경고를 낸다(§10 "엄격히 지킬 것" 참조). 둘 중 하나라도 없으면 검사하지
않는다 — 못 하는 검증을 하는 척하지 않는다.
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope


def _labeled_ranking(ranking: list[tuple[str, float]], labels: dict[str, bool]) -> list[tuple[str, float]]:
    """라벨(ground truth)이 있는 site만 남기고 점수 내림차순 정렬한다."""
    labeled = [(sid, score) for sid, score in ranking if sid in labels]
    labeled.sort(key=lambda x: x[1], reverse=True)
    return labeled


def _precision_at_k(ranking: list[tuple[str, float]], labels: dict[str, bool], k: int) -> float | None:
    top = _labeled_ranking(ranking, labels)[:k]
    if not top:
        return None
    hits = sum(1 for sid, _ in top if labels[sid])
    return round(hits / len(top), 3)


def _recall_at_top_pct(ranking: list[tuple[str, float]], labels: dict[str, bool], pct: float) -> float | None:
    labeled = _labeled_ranking(ranking, labels)
    positives_total = sum(1 for v in labels.values() if v)
    if positives_total == 0 or not labeled:
        return None
    n_top = max(1, round(len(labeled) * pct))
    hits = sum(1 for sid, _ in labeled[:n_top] if labels[sid])
    return round(hits / positives_total, 3)


def run(input: dict) -> dict:
    period = input.get("period")
    predictions = input.get("predictions")
    field_results = input.get("field_results")

    if not period or predictions is None or field_results is None:
        return error_envelope("period/predictions/field_results가 필요합니다.", fallback_tier=3)

    labels: dict[str, bool] = {}
    inspected_at_by_site: dict[str, str] = {}
    for fr in field_results:
        sid = fr.get("site_id")
        if sid is None:
            continue
        labels[sid] = bool(fr.get("actual_anomaly_found"))
        if fr.get("inspected_at"):
            inspected_at_by_site[sid] = fr["inspected_at"]

    if not labels:
        return make_envelope(
            {
                "precision_at_k": {"k": 0, "value": None},
                "recall_at_top20pct": None,
                "baseline_comparison": [],
                "labeled_site_count": 0,
                "positive_count": 0,
            },
            status="degraded",
            fallback_tier=2,
            warnings=["field_results에 site_id가 있는 항목이 없어 backtest를 수행할 수 없습니다."],
        )

    warnings: list[str] = []
    for p in predictions:
        sid = p.get("site_id")
        predicted_at = p.get("predicted_at")
        inspected_at = inspected_at_by_site.get(sid)
        if predicted_at and inspected_at and inspected_at <= predicted_at:
            warnings.append(
                f"[{sid}] inspected_at({inspected_at}) <= predicted_at({predicted_at}) — data leakage 의심, §10 참조"
            )

    k = input.get("k", 10)
    proposed_ranking = [(p["site_id"], p.get("risk_score") or 0) for p in predictions if p.get("site_id")]

    positive_count = sum(1 for v in labels.values() if v)
    baseline_comparison = [
        {"baseline": "random", "precision_at_k": round(positive_count / len(labels), 3)}
    ]

    for name, preds in (input.get("baseline_predictions") or {}).items():
        ranking = [(p["site_id"], p.get("score") or 0) for p in preds if p.get("site_id")]
        baseline_comparison.append({"baseline": name, "precision_at_k": _precision_at_k(ranking, labels, k)})

    prec_k = _precision_at_k(proposed_ranking, labels, k)
    baseline_comparison.append({"baseline": "proposed", "precision_at_k": prec_k})

    return make_envelope(
        {
            "precision_at_k": {"k": k, "value": prec_k},
            "recall_at_top20pct": _recall_at_top_pct(proposed_ranking, labels, 0.2),
            "baseline_comparison": baseline_comparison,
            "labeled_site_count": len(labels),
            "positive_count": positive_count,
        },
        status="ok" if not warnings else "degraded",
        fallback_tier=1 if not warnings else 2,
        warnings=warnings,
    )
