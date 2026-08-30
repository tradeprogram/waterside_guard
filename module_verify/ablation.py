"""방법 기여도·안정성 검증 — 현장 라벨 없이도 낼 수 있는 근거.

**왜 이 모듈이 따로 있는가**: `module_verify/run.py`는 실제 현장 결과(라벨)와 대조해
Precision@K를 채점한다. 그런데 이 프로토타입은 KECI 내부 점검 데이터에 접근할 수 없고,
0.5m급 실사 영상으로도 수변녹지의 훼손 *유형*(예초 vs 식생 소실, 자연 고사 vs 인위적 훼손)은
판별되지 않는다 — 그래서 제출자가 눈대중으로 정답지를 만드는 것 자체가 부적절하다
(2026-08-31 실측 판단, §ARCHITECTURE.md 검증 전략).

라벨이 없어도 **정직하게 말할 수 있는 것**이 두 가지 있다:

1. **기여도(ablation)** — 계절 기준선을 켰을 때와 껐을 때 순위가 어떻게 달라지는가.
   두 기간 차분만 쓰면 상위권이었는데 계절 기준선에서는 밀려난 필지가 있다면, 그건
   "해마다 반복되는 정상 변동을 변화로 오인했던" 건이다. 이건 라벨 없이 증명된다 —
   과거 3년 같은 계절 범위 안에 있다는 사실 자체가 근거이기 때문이다.

2. **안정성(negative check)** — 과거 3년 정상 범위를 벗어나지 않은 필지가 상위권에
   섞여 있는지. 섞여 있다면 우선순위가 오염된 것이다.

**이건 정확도가 아니다.** "우리 시스템이 훼손을 몇 % 맞혔다"는 주장은 여전히 할 수 없고,
해서도 안 된다. 여기서 말할 수 있는 건 "이 방법이 저 방법보다 이런 종류의 오탐을 걸러냈다"
까지다(§9 불확실성 표기 원칙).
"""
from __future__ import annotations

from common.envelope import make_envelope

# |robust_z|가 이 값 미만이면 "과거 같은 계절 정상 범위 안"으로 본다.
# 2는 정규분포에서 약 95% 구간에 해당하는 관행적 경계다(초기 가정치).
WITHIN_NORMAL_RANGE_Z = 2.0


def _rank_map(scored: list[tuple[str, float]]) -> dict[str, int]:
    """(site_id, score) -> {site_id: 1부터 시작하는 순위}. 점수 내림차순."""
    ordered = sorted(scored, key=lambda x: x[1], reverse=True)
    return {site_id: i for i, (site_id, _) in enumerate(ordered, start=1)}


def compare_methods(sites: list[dict], k: int = 10) -> dict:
    """계절 기준선 유무로 순위가 어떻게 달라지는지 비교한다.

    sites: [{"site_id", "seasonal_score", "two_period_score", "robust_z"}]
      - seasonal_score / two_period_score 중 하나라도 없으면 그 site는 비교에서 빠진다.
    """
    comparable = [
        s
        for s in sites
        if s.get("seasonal_score") is not None and s.get("two_period_score") is not None
    ]
    if not comparable:
        return {
            "comparable_site_count": 0,
            "k": k,
            "dropped_out_of_top_k": [],
            "entered_top_k": [],
            "within_normal_range_count": 0,
            "top_k_within_normal_range": [],
        }

    seasonal_rank = _rank_map([(s["site_id"], s["seasonal_score"]) for s in comparable])
    two_period_rank = _rank_map([(s["site_id"], s["two_period_score"]) for s in comparable])
    by_id = {s["site_id"]: s for s in comparable}

    dropped, entered = [], []
    for site_id in by_id:
        was_top = two_period_rank[site_id] <= k
        is_top = seasonal_rank[site_id] <= k
        entry = {
            "site_id": site_id,
            "two_period_rank": two_period_rank[site_id],
            "seasonal_rank": seasonal_rank[site_id],
            "robust_z": by_id[site_id].get("robust_z"),
            # 계절 기준선에서 밀려난 이유가 "정상 범위 안이라서"인지 표시 — 이게 있어야
            # "오탐을 걸러냈다"는 주장이 근거를 갖는다.
            "within_normal_range": _is_within_normal(by_id[site_id].get("robust_z")),
        }
        if was_top and not is_top:
            dropped.append(entry)
        elif is_top and not was_top:
            entered.append(entry)

    dropped.sort(key=lambda e: e["two_period_rank"])
    entered.sort(key=lambda e: e["seasonal_rank"])

    within_normal = [s["site_id"] for s in comparable if _is_within_normal(s.get("robust_z"))]
    top_k_within_normal = [
        s["site_id"] for s in comparable if seasonal_rank[s["site_id"]] <= k and _is_within_normal(s.get("robust_z"))
    ]

    return {
        "comparable_site_count": len(comparable),
        "k": k,
        # 두 기간 차분에서는 상위 K였는데 계절 기준선에서 밀려난 필지
        "dropped_out_of_top_k": dropped,
        # 반대로 계절 기준선 덕분에 상위 K로 올라온 필지
        "entered_top_k": entered,
        "within_normal_range_count": len(within_normal),
        # 상위 K 안에 "정상 범위 필지"가 섞여 있는지 — 비어 있어야 건강하다
        "top_k_within_normal_range": top_k_within_normal,
    }


def _is_within_normal(robust_z: float | None) -> bool:
    return robust_z is not None and abs(robust_z) < WITHIN_NORMAL_RANGE_Z


def run(input: dict) -> dict:
    sites = input.get("sites")
    if sites is None:
        return make_envelope(
            {"comparable_site_count": 0},
            status="degraded",
            fallback_tier=3,
            warnings=["sites가 필요합니다."],
        )

    k = input.get("k", 10)
    result = compare_methods(sites, k=k)

    warnings: list[str] = []
    if result["comparable_site_count"] == 0:
        warnings.append("두 방식을 모두 계산할 수 있는 site가 없어 비교할 수 없습니다.")
    if result["top_k_within_normal_range"]:
        warnings.append(
            f"상위 {k}위 안에 과거 정상 범위를 벗어나지 않은 필지가 "
            f"{len(result['top_k_within_normal_range'])}건 있습니다 — 우선순위가 오염됐을 수 있습니다."
        )

    return make_envelope(
        result,
        status="ok" if not warnings else "degraded",
        fallback_tier=1 if not warnings else 2,
        warnings=warnings,
    )
