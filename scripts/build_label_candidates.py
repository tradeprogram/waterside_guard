"""Ground Truth 라벨링 후보 데이터셋 생성 — 중간점검 리서치 §Real Validation Pack.

**왜 이게 최우선인가**: 현재 프로젝트의 단일 최대 약점은 "실제 현장 라벨이 없다"는 것이다.
Module VERIFY의 Precision@K 함수가 테스트를 통과한다는 건 *계산 코드가 맞다*는 뜻이지
*수변가드의 실제 탐지 정확도가 높다*는 뜻이 아니다. 채점할 정답지가 없으면 검증 화면도
비어 있을 수밖에 없다.

**이 스크립트가 하는 일**: 사람이 판독해야 할 후보 필지를 **편향 없이** 뽑아, 판독에
필요한 Before/After 위성 이미지 URL과 함께 CSV/JSON으로 내보낸다. 판독 자체는 사람이
하고(`scripts/import_labels.py`로 되돌려 넣는다), 이 스크립트는 그 준비만 담당한다.

**표본 편향을 막는 설계 — 이게 이 스크립트의 핵심이다**:
점수 상위만 뽑아서 라벨링하면 Precision@K는 잴 수 있어도 Recall은 못 잰다(하위 구간에
실제 변화가 얼마나 숨어 있는지 모르므로). 그래서 우선순위 점수 구간별로 **층화추출**한다:
상위·중위·하위에서 고루 뽑아야 "상위 20%만 봤을 때 전체 변화의 몇 %를 잡았는가"를
계산할 수 있다(§module_verify/run.py `_coverage_curve`).

사용법:
    python scripts/build_label_candidates.py --n 60
    -> data/labels/label_candidates.csv (판독자용) + .json (재수입용)
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

from dotenv import load_dotenv

from module_o.store import store

SNAPSHOT_PATHS = [
    Path("data/processed/yongin_yubang_priority_queue.geojson"),
    Path("data/processed/hanriver_priority_queue.geojson"),
]
BASELINE_PERIOD = ["2024-06-01", "2024-08-31"]
CURRENT_PERIOD = ["2026-06-01", "2026-08-25"]

# 점수 구간별로 몇 건씩 뽑을지의 비율 — 상위에 쏠리지 않게 하되, 실제 변화가 몰려 있을
# 상위 구간을 조금 더 두껍게 본다(전부 균등하면 양성 표본이 너무 적어 Precision이 불안정).
STRATA = [
    ("상위", 0.40),
    ("중위", 0.35),
    ("하위", 0.25),
]
RANDOM_SEED = 20260831  # 재현 가능한 표본 — 판독 결과를 나중에 재검증할 수 있어야 한다


def _load_sites() -> list[dict]:
    import geopandas as gpd

    from api_server import _load_one_snapshot  # 스냅샷 로딩 규약을 한 곳에서만 관리

    for path in SNAPSHOT_PATHS:
        if path.exists():
            _load_one_snapshot(gpd.read_file(path))
    return [e for e in store.all() if e.get("inspection_priority_score") is not None]


def stratified_sample(sites: list[dict], n: int, seed: int = RANDOM_SEED) -> list[dict]:
    """점수 내림차순으로 3등분한 뒤 구간별 비율만큼 무작위 추출한다(순수 함수, 테스트 가능)."""
    if not sites:
        return []
    ordered = sorted(sites, key=lambda s: s["inspection_priority_score"], reverse=True)
    third = max(len(ordered) // 3, 1)
    buckets = {"상위": ordered[:third], "중위": ordered[third : third * 2], "하위": ordered[third * 2 :]}

    rng = random.Random(seed)
    picked: list[dict] = []
    for name, ratio in STRATA:
        pool = buckets.get(name) or []
        take = min(round(n * ratio), len(pool))
        for site in rng.sample(pool, take):
            picked.append({**site, "stratum": name})
    return picked


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=60, help="판독할 후보 필지 수(리서치 권장 50~100)")
    parser.add_argument("--out-dir", default="data/labels")
    args = parser.parse_args()

    load_dotenv()
    sites = _load_sites()
    if not sites:
        print("스냅샷에 site가 없습니다 — 먼저 scripts/run_priority_queue_*.py를 실행하세요.")
        return

    picked = stratified_sample(sites, args.n)
    print(f"전체 {len(sites)}건 중 {len(picked)}건 층화추출")

    from module_obs.thumbnail import run as thumbnail_run

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for i, site in enumerate(picked, start=1):
        geometry = site.get("geometry_geojson")
        before = after = ""
        if geometry:
            # 판독자가 실제로 눈으로 비교할 이미지 — 이게 없으면 라벨링 자체가 불가능하다.
            b = thumbnail_run({"site_id": site["site_id"], "aoi_geometry_4326": geometry, "date_range": BASELINE_PERIOD})
            a = thumbnail_run({"site_id": site["site_id"], "aoi_geometry_4326": geometry, "date_range": CURRENT_PERIOD})
            before = (b["data"].get("thumbnail") or {}).get("url", "")
            after = (a["data"].get("thumbnail") or {}).get("url", "")
        print(f"  [{i}/{len(picked)}] {site['site_id']} 썸네일 준비")

        rows.append(
            {
                "site_id": site["site_id"],
                "addr": site.get("addr", ""),
                "stratum": site["stratum"],
                # 판독자에게 점수를 보여주면 그 값에 끌려간다(anchoring) — 판독 후 대조용으로만
                # 남기고 CSV 컬럼 순서상 맨 뒤로 뺀다.
                "before_image_url": before,
                "after_image_url": after,
                # --- 판독자가 채울 칸 ---
                "verdict": "",  # yes | no | uncertain
                "change_type": "",  # module_field VALID_CATEGORIES 참조
                "reviewer": "",
                "reviewed_at": "",
                "note": "",
                # --- 대조용(판독 중에는 보지 말 것) ---
                "_priority_score": site.get("inspection_priority_score"),
                "_anomaly_score": site.get("anomaly_score"),
            }
        )

    csv_path = out_dir / "label_candidates.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:  # BOM — 엑셀에서 한글이 깨지지 않게
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = out_dir / "label_candidates.json"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    by_stratum: dict[str, int] = {}
    for r in rows:
        by_stratum[r["stratum"]] = by_stratum.get(r["stratum"], 0) + 1
    print(f"\n구간별 표본: {by_stratum}")
    print(f"완료 -> {csv_path}, {json_path}")
    print("\n다음 단계: CSV의 verdict/change_type/reviewer/reviewed_at을 채운 뒤")
    print("          python scripts/import_labels.py 로 되돌려 넣으세요.")


if __name__ == "__main__":
    main()
