"""Ground Truth 판독 자료 생성 — 중간점검 리서치 §Real Validation Pack (Silver-A).

**왜 이게 최우선인가**: 현재 프로젝트의 단일 최대 약점은 "실제 라벨이 없다"는 것이다.
Module VERIFY의 Precision@K 함수가 테스트를 통과한다는 건 *계산 코드가 맞다*는 뜻이지
*수변가드의 실제 탐지 정확도가 높다*는 뜻이 아니다.

**이 스크립트가 하는 일**: 판독할 필지를 편향 없이 뽑고, 각 필지의 **고해상도 실사 영상**을
시기별로 이어붙여 필지 경계를 표시한 뒤, 브라우저에서 바로 판독할 수 있는 HTML을 만든다.
판독 자체는 사람이 하고(`import_labels.py`로 되돌려 넣는다), 여기서는 그 준비만 한다.

**설계 결정 세 가지**:

1. **NDVI가 아니라 Esri Wayback 실사 영상을 쓴다.** NDVI로 판독하면 알고리즘이 쓴 신호를
   사람이 다시 확인하는 순환논리가 되고, 애초에 Sentinel-2 10m로는 필지(중앙값 883㎡,
   약 3×3 픽셀)를 육안 판독할 수 없다. Wayback은 서브미터급이라 z18 3×3 모자이크에서
   필지와 주변이 또렷하게 보인다(§common/wayback.py).

2. **점수 구간별 층화추출.** 상위만 라벨링하면 Precision@K는 재도 **Recall은 못 잰다**
   (하위 구간에 실제 변화가 얼마나 숨어 있는지 모르므로). 상위·중위·하위에서 고루 뽑아야
   "상위 20%만 봤을 때 전체 변화의 몇 %를 잡았는가"를 계산할 수 있다.

3. **계절 차이를 훼손으로 오판하지 않도록 설계했다.** Wayback의 날짜는 배포일이지 촬영일이
   아니어서(Esri가 촬영일을 공개하지 않는다) 어떤 시기 영상은 여름, 어떤 것은 휴면기다.
   그래서 판독 지침을 **"구조적 변화만 판정하고 초록/갈색 차이는 natural_seasonal로 기록"**
   으로 못박았다. 이건 타협이 아니라 오히려 더 나은 정답지다 — 우리 모델의 알려진 약점이
   계절 오탐인데, 사람이 "이건 계절 변화일 뿐"이라고 표시해주면 그 오탐이 그대로 측정된다.

사용법:
    python scripts/build_label_candidates.py --n 60
    -> data/labels/review/index.html (브라우저로 열어 판독)
       data/labels/label_candidates.csv (판독 결과 입력)
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import random
import sys
from pathlib import Path

from dotenv import load_dotenv

from common.wayback import draw_parcel, fetch_mosaic, find_epochs
from module_o.store import store

SNAPSHOT_PATHS = [
    Path("data/processed/yongin_yubang_priority_queue.geojson"),
    Path("data/processed/hanriver_priority_queue.geojson"),
]

# 점수 구간별 표본 비율 — 균등하게 나누되 상위를 조금 두껍게 본다(전부 균등하면 양성
# 표본이 너무 적어 Precision이 불안정해진다).
STRATA = [("상위", 0.40), ("중위", 0.35), ("하위", 0.25)]
RANDOM_SEED = 20260831  # 재현 가능한 표본 — 판독 결과를 나중에 재검증할 수 있어야 한다

CHANGE_TYPES = [
    ("vegetation_loss", "식생 소실"),
    ("bare_ground", "나지 노출"),
    ("construction_earthwork", "공사·토공"),
    ("flooding_water_level", "침수·수위 변화"),
    ("mowing_agriculture", "예초·영농 활동"),
    ("restoration_work", "복원사업 시공"),
    ("natural_seasonal", "자연·계절 변화(오탐)"),
    ("other", "기타"),
]


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


def _centroid(geometry: dict) -> tuple[float, float] | None:
    """폴리곤 꼭짓점 평균 — 모자이크 중심을 잡는 용도라 정밀할 필요 없다."""
    pts: list[tuple[float, float]] = []

    def walk(coords):
        if not coords:
            return
        if isinstance(coords[0], (int, float)):
            pts.append((coords[0], coords[1]))
            return
        for c in coords:
            walk(c)

    walk(geometry.get("coordinates"))
    if not pts:
        return None
    return sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)


def _render_html(cards: list[dict], out_dir: Path) -> Path:
    """판독용 HTML — 시기별 영상을 나란히 놓고, 판정 기준을 화면에 항상 띄워둔다."""
    options = "".join(f'<option value="{v}">{label}</option>' for v, label in CHANGE_TYPES)

    body = []
    for i, card in enumerate(cards, start=1):
        imgs = "".join(
            f'<figure><img src="{html.escape(im["file"])}" alt="{html.escape(im["date"])}">'
            f'<figcaption>{html.escape(im["date"])} 배포본</figcaption></figure>'
            for im in card["images"]
        )
        if not card["images"]:
            imgs = '<p class="warn">이 위치의 고해상도 영상을 찾지 못했습니다 — 판독 대상에서 제외하세요.</p>'
        body.append(
            f"""
<section class="card" id="site-{i}">
  <header>
    <span class="idx">{i} / {len(cards)}</span>
    <strong>{html.escape(card["addr"] or card["site_id"])}</strong>
    <code>{html.escape(card["site_id"])}</code>
    <span class="stratum">{html.escape(card["stratum"])} 구간</span>
  </header>
  <div class="images">{imgs}</div>
  <div class="entry">
    <label>판정
      <select data-field="verdict" data-site="{html.escape(card["site_id"])}">
        <option value="">— 선택 —</option>
        <option value="yes">변화 확인됨</option>
        <option value="no">변화 없음</option>
        <option value="uncertain">판단 보류</option>
      </select>
    </label>
    <label>변화 유형
      <select data-field="change_type" data-site="{html.escape(card["site_id"])}">
        <option value="">— 선택 —</option>{options}
      </select>
    </label>
    <label>메모 <input type="text" data-field="note" data-site="{html.escape(card["site_id"])}"></label>
  </div>
</section>"""
        )

    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>수변가드 Ground Truth 판독</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 0; background: #fafafa; color: #171717; }}
 .guide {{ position: sticky; top: 0; z-index: 10; background: #fff; border-bottom: 2px solid #171717;
          padding: 12px 20px; box-shadow: 0 1px 6px rgba(0,0,0,.06); }}
 .guide h1 {{ font-size: 16px; margin: 0 0 6px; }}
 .guide ul {{ margin: 4px 0 0 18px; padding: 0; font-size: 13px; line-height: 1.6; }}
 .guide .critical {{ color: #b91c1c; font-weight: 600; }}
 .card {{ background: #fff; margin: 16px 20px; padding: 14px; border: 1px solid #e5e5e5; border-radius: 8px; }}
 .card header {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; margin-bottom: 10px; }}
 .idx {{ background: #171717; color: #fff; border-radius: 10px; padding: 1px 9px; font-size: 12px; }}
 code {{ background: #f5f5f5; padding: 1px 5px; border-radius: 3px; font-size: 11px; color: #737373; }}
 .stratum {{ font-size: 11px; color: #737373; border: 1px solid #d4d4d4; border-radius: 3px; padding: 1px 6px; }}
 .images {{ display: flex; gap: 10px; overflow-x: auto; }}
 figure {{ margin: 0; flex: 0 0 auto; }}
 figure img {{ width: 340px; height: 340px; object-fit: cover; border-radius: 4px; display: block; }}
 figcaption {{ font-size: 12px; color: #525252; margin-top: 3px; text-align: center; }}
 .entry {{ display: flex; gap: 14px; margin-top: 10px; flex-wrap: wrap; align-items: center; }}
 .entry label {{ font-size: 13px; display: flex; gap: 5px; align-items: center; }}
 .entry input[type=text] {{ width: 260px; padding: 3px 6px; }}
 .warn {{ color: #b91c1c; font-size: 13px; }}
 #export {{ position: fixed; right: 20px; bottom: 20px; padding: 12px 18px; background: #171717;
            color: #fff; border: 0; border-radius: 22px; cursor: pointer; font-size: 14px;
            box-shadow: 0 3px 10px rgba(0,0,0,.25); }}
</style></head><body>
<div class="guide">
  <h1>수변가드 Ground Truth 판독 — {len(cards)}건</h1>
  <ul>
    <li>빨간 테두리 안 <strong>필지만</strong> 보고 판정하세요. 주변은 맥락 참고용입니다.</li>
    <li class="critical">초록↔갈색(잎이 있고 없고)은 변화가 <u>아닙니다</u>. 영상마다 촬영 계절이 달라서 생기는 차이입니다.
        계절 차이로 보이면 &ldquo;변화 확인됨 + 자연·계절 변화(오탐)&rdquo;로 기록하세요.</li>
    <li><strong>구조적 변화</strong>를 보세요: 건물·비닐하우스 신축/철거, 흙을 판 자국, 새 도로·포장, 나무가 잘려나간 자국, 물이 찬 자국.</li>
    <li>애매하면 억지로 정하지 말고 <strong>판단 보류</strong>를 고르세요 — 보류는 음성과 따로 집계됩니다.</li>
    <li>가능하면 <strong>두 사람이 각자 판독</strong>하고 어긋난 건만 다시 보세요.</li>
  </ul>
</div>
{"".join(body)}
<button id="export">판독 결과 CSV 내려받기</button>
<script>
document.getElementById('export').addEventListener('click', function () {{
  const rows = [['site_id','verdict','change_type','note']];
  document.querySelectorAll('.card').forEach(function (card) {{
    const get = f => card.querySelector('[data-field="' + f + '"]');
    const siteId = get('verdict').dataset.site;
    const verdict = get('verdict').value;
    if (!verdict) return;  // 판독 안 한 건은 내보내지 않는다
    rows.push([siteId, verdict, get('change_type').value, (get('note').value || '').replace(/[",\\n]/g, ' ')]);
  }});
  if (rows.length === 1) {{ alert('판정한 항목이 없습니다.'); return; }}
  const csv = '\\ufeff' + rows.map(r => r.map(v => '"' + v + '"').join(',')).join('\\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {{ type: 'text/csv' }}));
  a.download = 'reviewed.csv';
  a.click();
  alert((rows.length - 1) + '건을 내려받았습니다.\\n이 파일 내용을 label_candidates.csv에 옮겨 붙인 뒤\\npython scripts/import_labels.py 를 실행하세요.');
}});
</script>
</body></html>"""

    path = out_dir / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=60, help="판독할 후보 필지 수(리서치 권장 50~100)")
    parser.add_argument("--out-dir", default="data/labels")
    parser.add_argument("--max-epochs", type=int, default=4, help="필지당 보여줄 시기 수(최신 우선)")
    args = parser.parse_args()

    load_dotenv()
    sites = _load_sites()
    if not sites:
        print("스냅샷에 site가 없습니다 — 먼저 scripts/run_priority_queue_*.py를 실행하세요.")
        return

    picked = stratified_sample(sites, args.n)
    print(f"전체 {len(sites)}건 중 {len(picked)}건 층화추출\n")

    out_dir = Path(args.out_dir)
    img_dir = out_dir / "review" / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    cards, rows = [], []
    for i, site in enumerate(picked, start=1):
        geometry = site.get("geometry_geojson")
        center = _centroid(geometry) if geometry else None
        images: list[dict] = []

        if center:
            lat, lon = center
            epochs = find_epochs(lat, lon)[-args.max_epochs :]  # 최신 시기 우선
            for ep in epochs:
                mosaic, bounds = fetch_mosaic(lat, lon, ep["release"])
                if mosaic is None:
                    continue
                draw_parcel(mosaic, bounds, geometry)
                fname = f"{site['site_id']}_{ep['date']}.jpg"
                mosaic.save(img_dir / fname, quality=82)
                images.append({"date": ep["date"], "file": f"img/{fname}"})
        print(f"  [{i}/{len(picked)}] {site['site_id']} — 영상 {len(images)}시기")

        cards.append(
            {
                "site_id": site["site_id"],
                "addr": site.get("addr", ""),
                "stratum": site["stratum"],
                "images": images,
            }
        )
        rows.append(
            {
                "site_id": site["site_id"],
                "addr": site.get("addr", ""),
                "stratum": site["stratum"],
                "epochs": " | ".join(im["date"] for im in images),
                # --- 판독자가 채울 칸 ---
                "verdict": "",
                "change_type": "",
                "reviewer": "",
                "reviewed_at": "",
                "note": "",
                # --- 대조용(판독 중에는 보지 말 것) ---
                "_priority_score": site.get("inspection_priority_score"),
                "_anomaly_score": site.get("anomaly_score"),
            }
        )

    csv_path = out_dir / "label_candidates.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:  # BOM — 엑셀 한글 깨짐 방지
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "label_candidates.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    html_path = _render_html(cards, out_dir / "review")

    by_stratum: dict[str, int] = {}
    for r in rows:
        by_stratum[r["stratum"]] = by_stratum.get(r["stratum"], 0) + 1
    no_image = sum(1 for c in cards if not c["images"])

    print(f"\n구간별 표본: {by_stratum}")
    if no_image:
        print(f"경고: {no_image}건은 고해상도 영상을 못 찾아 판독 불가")
    print(f"\n판독 화면 -> {html_path}")
    print(f"결과 입력 -> {csv_path}")
    print("\n다음 단계: HTML을 브라우저로 열어 판독 -> CSV 내려받기 -> label_candidates.csv에")
    print("          verdict/change_type/reviewer/reviewed_at 채우기 -> python scripts/import_labels.py")


if __name__ == "__main__":
    main()
