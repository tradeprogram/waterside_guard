"""제안서용 figure 생성 — 실제 데이터·실제 API 응답만 쓴다.

**원칙**: 여기서 만드는 그림은 전부 저장소의 실제 산출물에서 나온다. 추정치나 예시값으로
그림을 만들지 않는다 — 제안서에 들어간 숫자는 전부 재현 가능해야 한다(§9 불확실성 표기).
아직 없는 값(Precision@K 등)은 그리지 않는다.

UI 스크린샷은 여기서 만들지 않는다(화면 디자인이 아직 바뀔 수 있음) — 도식·차트·지도만.

사용법:
    python scripts/generate_figures.py          # 전부
    python scripts/generate_figures.py --only ablation seasonal
    -> docs/figures/*.png
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches

API_BASE = "http://localhost:8001"
OUT_DIR = Path("docs/figures")
DPI = 200

# 한글 라벨이 깨지면 그림 자체가 무용지물이라 폰트를 명시한다.
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호가 네모로 깨지는 것 방지

INK = "#171717"
MUTED = "#737373"
FAINT = "#d4d4d4"
RED = "#c0392b"
# 기관 CI에서 뽑은 두 계열. BLUE라는 이름은 호출부 호환으로 남겼지만 값은 CI 주색(그린)이다.
GREEN = "#009058"  # CI 주색 — 긍정적 결과(오탐 0건, 절감률)에 쓴다
BLUE = "#00794a"   # 화면의 --brand와 같은 값 — 위성·시스템 단계
LIME = "#6a8f00"   # CI 보조색(#90d000) 계열 — 현장·드론 단계. BLUE와 색상각이 80도 이상
                   # 벌어져야 F3 도식에서 두 계열이 구분된다(둘 다 초록이면 도식이 뭉개짐).
ORANGE = "#e67e22"
# ui/lib/tiers.ts, ui/app/globals.css의 --tier-* 와 반드시 같은 값 — 화면과 제안서 그림에서
# 같은 등급이 다른 색으로 보이면 그 자체로 신뢰를 깎는다.
TIER_COLOR = {"1순위": "#c0392b", "2순위": "#e67e22", "3순위": "#a3b545", "정상": "#009058"}


def _api(path: str) -> dict:
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=60) as r:
        return json.load(r)


def _save(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  저장: {path}")


def _style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(FAINT)
    ax.spines["bottom"].set_color(FAINT)
    ax.tick_params(colors=MUTED, labelsize=9)


# --- F1: 계절 기준선 오탐 감소 (핵심 실증) ---------------------------------


def fig_ablation() -> None:
    """두 기간 차분 상위 10위에 있던 계절 오탐이 계절 기준선 적용 후 어떻게 밀려났는지."""
    data = _api("/verify/ablation?k=10")["data"]
    dropped = [d for d in data["dropped_out_of_top_k"] if d["within_normal_range"]]
    k = data["k"]

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1, 1.5]})

    # 왼쪽: 요약 막대 (6건 -> 0건)
    ax0.bar(["두 기간 차분", "계절 기준선"], [len(dropped), len(data["top_k_within_normal_range"])],
            color=[RED, GREEN], width=0.5)
    for i, v in enumerate([len(dropped), len(data["top_k_within_normal_range"])]):
        ax0.text(i, v + 0.15, f"{v}건", ha="center", fontsize=13, fontweight="bold",
                 color=RED if i == 0 else GREEN)
    ax0.set_ylim(0, len(dropped) + 1.2)
    ax0.set_ylabel(f"상위 {k}위 중 계절 오탐 건수", fontsize=10, color=INK)
    ax0.set_title(f"상위 {k}위의 계절 오탐", fontsize=11, color=INK, pad=12)
    ax0.set_yticks(range(len(dropped) + 2))
    _style(ax0)

    # 오른쪽: 필지별 순위 이동 — 순위가 1~7위로 촘촘해 slope 차트로 그리면 라벨이 겹친다.
    # 한 필지당 한 행을 주는 dumbbell 형태면 충돌이 원천적으로 없다.
    dropped_sorted = sorted(dropped, key=lambda d: d["two_period_rank"])
    for i, d in enumerate(dropped_sorted):
        y = len(dropped_sorted) - i - 1
        ax1.plot([d["two_period_rank"], d["seasonal_rank"]], [y, y], "-", color=FAINT, linewidth=2.5, zorder=1)
        ax1.plot(d["two_period_rank"], y, "o", color=RED, markersize=9, zorder=3)
        ax1.plot(d["seasonal_rank"], y, "o", color=MUTED, markersize=9, markerfacecolor="white",
                 markeredgewidth=1.8, zorder=3)
        ax1.text(d["two_period_rank"] - 1.5, y, f"{d['two_period_rank']}위", ha="right", va="center",
                 fontsize=9.5, color=RED, fontweight="bold")
        ax1.text(d["seasonal_rank"] + 1.5, y, f"{d['seasonal_rank']}위  ({d['robust_z']:+.1f}σ)",
                 ha="left", va="center", fontsize=9.5, color=MUTED)

    ax1.axvspan(0, k + 0.5, color=RED, alpha=0.07, zorder=0)
    ax1.text(k / 2, len(dropped_sorted) - 0.35, f"상위 {k}위 구간", ha="center", fontsize=8.5, color=RED)
    ax1.set_xlim(-8, max(d["seasonal_rank"] for d in dropped) + 22)
    ax1.set_ylim(-0.7, len(dropped_sorted) - 0.1)
    ax1.set_yticks([])
    ax1.set_xlabel("순위 (낮을수록 우선)", fontsize=10, color=INK)
    ax1.set_title("계절 변동으로 걸러진 필지의 순위 이동", fontsize=11, color=INK, pad=12)
    ax1.spines["left"].set_visible(False)
    _style(ax1)

    _style(ax1)

    fig.suptitle("계절 정합 기준선의 오탐 감소 효과", fontsize=13, fontweight="bold", color=INK, y=1.0)
    fig.text(0.5, -0.04,
             f"전체 {data['comparable_site_count']}건 중 {data['within_normal_range_count']}건이 과거 3년 같은 계절의 정상 변동 범위 안. "
             "σ는 그 범위 대비 이탈 정도(|σ|<2면 정상 범위).",
             ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout()
    _save(fig, "F1_ablation_seasonal_falsepositive")


# --- F5: 계절 기준선 원리 ---------------------------------------------------


def fig_seasonal_principle() -> None:
    """과거 3년 정상범위 띠 위에 올해 값을 찍어 '무엇을 이상으로 보는가'를 설명한다."""
    sites = _api("/sites")
    target = max(
        (s for s in sites if s.get("inspection_priority_score") is not None),
        key=lambda s: s["inspection_priority_score"],
    )
    ev = _api(f"/sites/{target['site_id']}/evidence")
    seasonal = ev["seasonal_anomaly"]
    yearly = [y for y in seasonal["yearly"] if y["ndvi_median"] is not None]

    median, mad = seasonal["historical_median"], seasonal["historical_mad"]
    # 화면(SeasonalBaselineChart)과 같은 규칙 — 센서 노이즈를 반영한 하한 적용
    scale = max(1.4826 * mad, 0.03)

    fig, ax = plt.subplots(figsize=(8, 4.4))
    xs = list(range(len(yearly))) + [len(yearly)]
    labels = [str(y["year"]) for y in yearly] + ["올해"]
    values = [y["ndvi_median"] for y in yearly] + [seasonal["current_ndvi"]]

    ax.axhspan(median - scale * 2, median + scale * 2, color=FAINT, alpha=0.5,
               label="정상 변동 범위 (±2σ)", zorder=1)
    ax.axhline(median, color=MUTED, linestyle="--", linewidth=1, zorder=2,
               label=f"과거 중앙값 {median:.3f}")
    ax.plot(xs[:-1], values[:-1], "o-", color=MUTED, markersize=8, linewidth=1.5, zorder=3,
            label="과거 같은 계절")
    ax.plot([xs[-1]], [values[-1]], "o", color=RED, markersize=13, zorder=4, label="올해")

    # 라벨을 점 아래에 두면 축 밖으로 잘린다 — 왼쪽 같은 높이에 둔다
    ax.annotate(f"{seasonal['robust_z']:+.1f}σ\n정상범위 밖",
                xy=(xs[-1], values[-1]), xytext=(xs[-1] - 0.9, values[-1]),
                fontsize=10.5, color=RED, fontweight="bold", ha="center", va="center",
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
    # 정상범위와 올해 값 사이의 간격 자체가 메시지라 화살표로 명시한다
    ax.annotate("", xy=(xs[-1] - 0.3, median - scale * 2), xytext=(xs[-1] - 0.3, values[-1]),
                arrowprops=dict(arrowstyle="<->", color="#a3a3a3", lw=1.3))

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=10, color=INK)
    ax.set_ylabel("NDVI (같은 계절 중앙값)", fontsize=10, color=INK)
    ax.set_title(f"'계절 변화'와 '이상'을 구분하는 방법 — {target.get('addr', '')}",
                 fontsize=12, fontweight="bold", color=INK, pad=12)
    ax.legend(fontsize=8.5, frameon=False, loc="center left")
    ax.set_xlim(-0.45, len(yearly) + 0.45)
    _style(ax)
    fig.text(0.5, -0.03,
             "두 기간만 비교하면 '떨어졌다'까지만 말할 수 있지만, 같은 계절 과거 3년의 정상 변동 범위를 기준으로 하면 "
             "'해마다 있는 변동인가, 벗어났는가'를 구분할 수 있다.",
             ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout()
    _save(fig, "F5_seasonal_baseline_principle")


# --- NEW: 출장 이동거리 절감 -------------------------------------------------


def fig_route_savings() -> None:
    """예산별로 '순위대로 이동' vs '군집 순서 이동' 거리 비교."""
    budgets = [5, 10, 20]
    naive, clustered, saved_pct, basis = [], [], [], []
    for b in budgets:
        d = _api(f"/priority-queue/route?budget={b}")["data"]
        naive.append(d["naive_order_length_m"] / 1000)
        clustered.append(d["clustered_order_length_m"] / 1000)
        saved_pct.append(d["saved_pct"])
        basis.append(d["distance_basis"])

    fig, ax = plt.subplots(figsize=(8, 4.4))
    x = range(len(budgets))
    w = 0.34
    ax.bar([i - w / 2 for i in x], naive, w, label="순위 순차 방문", color=FAINT)
    ax.bar([i + w / 2 for i in x], clustered, w, label="권역 통합 방문", color=BLUE)

    for i, (n, c, p) in enumerate(zip(naive, clustered, saved_pct)):
        ax.text(i - w / 2, n + 6, f"{n:.0f}km", ha="center", fontsize=9, color=MUTED)
        ax.text(i + w / 2, c + 6, f"{c:.0f}km", ha="center", fontsize=9, color=BLUE, fontweight="bold")
        if p > 0:
            ax.text(i, max(n, c) + 32, f"-{p:.0f}%", ha="center", fontsize=11,
                    color=GREEN, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels([f"상위 {b}필지" for b in budgets], fontsize=10, color=INK)
    ax.set_ylabel("총 이동거리 (km)", fontsize=10, color=INK)
    ax.set_ylim(0, max(naive) * 1.25)
    ax.set_title("동일한 점검 대상에 필요한 이동거리", fontsize=12, fontweight="bold", color=INK, pad=12)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    _style(ax)
    caption = (
        "실제 도로 주행거리(OSRM) 기준이다. 점검 대상은 동일하고 방문 순서만 바뀐다."
        if all(b == "driving" for b in basis)
        else "직선거리 기준이며 실제 도로 주행거리와 다를 수 있다. 점검 대상은 동일하고 방문 순서만 바뀐다."
    )
    fig.text(0.5, -0.03, caption,
             ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout()
    _save(fig, "F_route_savings")


# --- F11: 점수 구성 --------------------------------------------------------

FACTOR_LABEL = {
    "anomaly_score_mean": "위성 이상도 (NDVI/NDMI)",
    "changed_area_ratio": "변화 면적 비율",
    "sar_anomaly_mean": "레이더(SAR) 변화",
    "recent_rainfall_mm": "최근 14일 누적 강우",
    "last_inspection_days_ago": "마지막 점검 후 경과일",
    "adjacent_to_water": "수변 인접 여부",
    "past_anomaly_count": "과거 이상 발생 횟수",
}
# module_risk/run.py의 _normalize()와 같은 규칙 — 그림과 실제 계산이 어긋나면 안 된다.
NORMALIZE = {
    "anomaly_score_mean": lambda v: min(max(v, 0), 1),
    "changed_area_ratio": lambda v: min(max(v, 0), 1),
    "sar_anomaly_mean": lambda v: min(max(v, 0), 1),
    "recent_rainfall_mm": lambda v: min(v / 50, 1),
    "last_inspection_days_ago": lambda v: min(v / 180, 1),
    "adjacent_to_water": lambda v: 1.0 if v else 0.0,
    "past_anomaly_count": lambda v: min(v / 3, 1),
}


# 값을 사람이 읽는 형태로 — 원본 숫자만 찍으면 단위를 알 수 없다.
FACTOR_VALUE_FMT = {
    "anomaly_score_mean": lambda v: f"{v:.2f} (0~1)",
    "changed_area_ratio": lambda v: f"{v*100:.0f}% 면적 변화",
    "sar_anomaly_mean": lambda v: f"{v:.2f} (0~1)",
    "recent_rainfall_mm": lambda v: f"{v:.0f}mm",
    "last_inspection_days_ago": lambda v: f"{v:.0f}일 전",
    "adjacent_to_water": lambda v: "수변 인접" if v else "비인접",
    "past_anomaly_count": lambda v: f"{v:.0f}회",
}
# module_risk/run.py의 WEIGHTS와 같아야 한다 — 결측 요인까지 그리려면 전체 목록이 필요하다.
ALL_WEIGHTS = {
    "anomaly_score_mean": 0.30,
    "changed_area_ratio": 0.15,
    "last_inspection_days_ago": 0.15,
    "sar_anomaly_mean": 0.10,
    "recent_rainfall_mm": 0.10,
    "adjacent_to_water": 0.10,
    "past_anomaly_count": 0.10,
}
MISSING_REASON = {
    "last_inspection_days_ago": "현장점검 이력 미축적",
    "past_anomaly_count": "현장점검 이력 미축적",
}


def fig_score_breakdown() -> None:
    """'왜 이 순위인가'를 요인별로 분해하고, **빠진 근거까지 함께** 보여준다.

    결측 요인을 그림에서 지우면 "7개 중 5개만 봤다"는 사실이 사라진다. 공공기관 심사에서
    불확실성을 드러내는 것 자체가 강점이므로 빗금 막대로 남긴다([[waterside-guard-scoring-defense]]).
    """
    sites = _api("/sites")
    target = max(
        (s for s in sites if s.get("inspection_priority_score") is not None),
        key=lambda s: s["inspection_priority_score"],
    )
    ev = _api(f"/sites/{target['site_id']}/evidence")
    present = {f["factor"]: f for f in ev["contributing_factors"]}

    rows = []
    for factor, weight in ALL_WEIGHTS.items():
        share = weight * 100  # 전체 7개 요인 기준 가중치 비중
        f = present.get(factor)
        if f is None:
            rows.append((FACTOR_LABEL[factor], None, share, MISSING_REASON.get(factor, "데이터 없음")))
        else:
            norm = NORMALIZE[factor](f["value"])
            rows.append((FACTOR_LABEL[factor], norm * share, share, FACTOR_VALUE_FMT[factor](f["value"])))
    # 결측을 아래로, 나머지는 기여도 오름차순 — 막대가 위로 갈수록 길어진다
    rows.sort(key=lambda r: (r[1] is not None, r[1] or 0))

    fig, ax = plt.subplots(figsize=(9, 4.6))
    ys = list(range(len(rows)))
    for i, (_, actual, share, _) in enumerate(rows):
        if actual is None:
            ax.barh(i, share, height=0.6, facecolor="white", edgecolor=FAINT,
                    hatch="///", linewidth=1.0, zorder=2)
        else:
            ax.barh(i, share, height=0.6, color=FAINT, zorder=2)
            ax.barh(i, actual, height=0.6, color=BLUE, zorder=3)

    for i, (_, actual, share, label) in enumerate(rows):
        color = MUTED if actual is not None else "#a3a3a3"
        ax.text(share + 0.8, i, label, va="center", fontsize=9, color=color,
                style="normal" if actual is not None else "italic")

    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=9.5, color=INK)
    ax.set_xlabel("전체 7개 요인 기준 가중치 비중 (%)", fontsize=10, color=INK)
    ax.set_xlim(0, 30 * 1.75)
    ax.set_title(
        f"점검 우선순위 {target['inspection_priority_score']}점의 근거 — {target.get('addr','')}",
        fontsize=12.5, fontweight="bold", color=INK, pad=12,
    )

    handles = [
        patches.Patch(facecolor=BLUE, label="실제 기여분"),
        patches.Patch(facecolor=FAINT, label="해당 요인의 최대 가능 기여분"),
        patches.Patch(facecolor="white", edgecolor=FAINT, hatch="///", label="근거 결측 — 점수에 미반영"),
    ]
    ax.legend(handles=handles, fontsize=8.5, frameon=False, loc="lower right")
    _style(ax)

    coverage = ev.get("weight_coverage")
    note = ("빗금은 아직 데이터가 없어 점수 산정에서 빠진 요인이다. "
            f"이 필지는 전체 가중치의 {round((coverage or 1)*100)}%만 확보된 상태에서 "
            "확보분을 재정규화해 점수를 냈고, 화면에도 같은 사실을 표기한다.")
    fig.text(0.5, -0.04, note, ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout()
    _save(fig, "F11_score_breakdown")


# --- F10: 대상지 분포 지도 ---------------------------------------------------


def fig_site_map() -> None:
    """대상지가 한강유역 어디에 흩어져 있고 등급이 어떻게 분포하는지."""
    import geopandas as gpd
    import pandas as pd

    gdfs = [
        gpd.read_file(p)
        for p in ("data/processed/hanriver_priority_queue.geojson", "data/processed/yongin_yubang_priority_queue.geojson")
        if Path(p).exists()
    ]
    gdf = pd.concat(gdfs).to_crs("EPSG:5179")
    gdf["sigungu"] = gdf["addr"].str.split().str[1]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 5.6), gridspec_kw={"width_ratios": [1.8, 1]})

    # 행정동 경계를 옅게 깔아 지리적 맥락을 준다 — 점만 떠 있으면 어디인지 알 수 없다.
    boundary_path = Path("data/processed/admin_dong_boundaries.geojson")
    if boundary_path.exists():
        dong = gpd.read_file(boundary_path).to_crs("EPSG:5179")
        dong.boundary.plot(ax=ax, color="#e5e5e5", linewidth=0.6, zorder=1)

    pts = gdf.geometry.centroid
    minx, miny, maxx, maxy = pts.total_bounds
    pad = max(maxx - minx, maxy - miny) * 0.12

    for tier, color in TIER_COLOR.items():
        subset = gdf[gdf["priority_tier"] == tier]
        if subset.empty:
            continue
        c = subset.geometry.centroid
        ax.scatter(c.x, c.y, s=80, c=color, edgecolors="white", linewidths=1.3,
                   label=f"{tier} ({len(subset)})", zorder=4)

    # 시군구 이름 — 무리 위쪽에 배치하되 범례와 겹치지 않게 지도 안쪽에만 둔다
    for name, group in gdf.groupby("sigungu"):
        c = group.geometry.centroid
        ax.annotate(name, (c.x.mean(), c.y.max() + pad * 0.22), ha="center", fontsize=9.5,
                    color=INK, zorder=5,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none", alpha=0.85))

    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    # 범례를 축 밖(아래)에 두어 지도 라벨과 절대 겹치지 않게 한다
    ax.legend(fontsize=9, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              title="점검 우선순위 등급", title_fontsize=9)
    ax.set_title(f"대상지 분포 — 한강유역 {gdf['sigungu'].nunique()}개 시/군/구 {len(gdf)}필지",
                 fontsize=12.5, fontweight="bold", color=INK, pad=14)

    # 시군구별 개수는 표본 설계상 전부 같아 정보가 없다 — 등급 분포를 보여준다.
    counts = [(t, int((gdf["priority_tier"] == t).sum())) for t in ("1순위", "2순위", "3순위", "정상")]
    counts = [(t, n) for t, n in counts if n > 0][::-1]
    ax2.barh([t for t, _ in counts], [n for _, n in counts],
             color=[TIER_COLOR[t] for t, _ in counts], height=0.6)
    for i, (_, n) in enumerate(counts):
        ax2.text(n + 0.5, i, f"{n}필지", va="center", fontsize=9.5, color=MUTED)
    ax2.set_xlim(0, max(n for _, n in counts) * 1.28)
    ax2.set_xlabel("필지 수", fontsize=10, color=INK)
    ax2.set_title("점검 우선순위 등급 분포", fontsize=11.5, color=INK, pad=14)
    ax2.tick_params(labelsize=10)
    _style(ax2)

    fig.text(0.5, -0.02,
             "한강유역 매수토지 6,275필지 중 폴리곤 복원에 성공한 5,526필지에서 시/군/구별로 10필지씩 표본 추출했다. "
             "회색 선은 행정동 경계.",
             ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout()
    _save(fig, "F10_site_distribution")


# --- F3: 워크플로 다이어그램 -------------------------------------------------


def _box(ax, x, y, w, h, text, fc, ec, fontsize=10, weight="normal", tc=None):
    ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                        facecolor=fc, edgecolor=ec, linewidth=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            color=tc or INK, fontweight=weight, linespacing=1.5)


def _arrow(ax, xy_from, xy_to, color=MUTED, style="->", lw=1.5, ls="-"):
    ax.annotate("", xy=xy_to, xytext=xy_from,
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, linestyle=ls,
                                shrinkA=2, shrinkB=2))


def fig_workflow() -> None:
    """'위성이 후보를 좁히고, 드론과 사람이 확인한다' — 드론 대체가 아님을 그림으로."""
    fig, ax = plt.subplots(figsize=(9.5, 6.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)
    ax.axis("off")

    _box(ax, 2.5, 7.9, 5, 0.85, "광역 위성 관측\nSentinel-2 · Sentinel-1 · (국토위성)", "#f5f5f5", FAINT, 10)
    _box(ax, 2.5, 6.4, 5, 0.85, "변화 선별\n계절 정합 기준선 · 센서 일치 · 품질 게이트", "#e6f4ed", BLUE, 10)
    _box(ax, 2.5, 4.9, 5, 0.85, "점검 우선순위 + 근거\n왜 이 순위인가 · 증거 신뢰도", "#e6f4ed", BLUE, 10, "bold")
    _box(ax, 2.5, 3.4, 5, 0.85, "주간 점검 가능 인력에 맞춘 상위 N필지\n권역별 통합 방문 순서", "#e6f4ed", BLUE, 10)

    _box(ax, 1.35, 1.6, 3.15, 0.85, "현장직원 확인", "#f4f8e6", LIME, 10)
    _box(ax, 5.5, 1.6, 3.15, 0.85, "드론 확인", "#f4f8e6", LIME, 10)
    _box(ax, 2.5, 0.2, 5, 0.85, "확정 · 결과 기록\n변화 유형 · 사진 · 오탐 사유", "#f4f8e6", LIME, 10, "bold")

    for y0, y1 in ((7.9, 7.25), (6.4, 5.75), (4.9, 4.25)):
        _arrow(ax, (5, y0), (5, y1))
    _arrow(ax, (4.2, 3.4), (3.0, 2.45))
    _arrow(ax, (5.8, 3.4), (7.0, 2.45))
    _arrow(ax, (3.0, 1.6), (4.2, 1.05), LIME)
    _arrow(ax, (7.0, 1.6), (5.8, 1.05), LIME)

    # 환류 — 현장 결과가 다음 주기 우선순위로 되돌아간다.
    # 곡선(arc3)으로 그리면 좌측 "현장직원 확인" 박스를 관통하므로, 바깥으로 우회하는
    # 폴리라인으로 그린다.
    fx = 0.5
    ax.plot([2.5, fx, fx, 2.35], [0.62, 0.62, 5.32, 5.32], color=ORANGE, lw=1.6,
            linestyle="--", solid_capstyle="round", zorder=1)
    _arrow(ax, (2.2, 5.32), (2.48, 5.32), ORANGE, lw=1.6)
    ax.text(fx + 0.14, 3.05, "현장 결과가\n다음 주기\n우선순위에\n반영", fontsize=8.5, color=ORANGE,
            ha="left", va="center", linespacing=1.6)

    ax.text(5, 8.98, "수변생태벨트 점검 우선순위 지원시스템 — 관측에서 현장 확인까지", fontsize=12.5, fontweight="bold",
            color=INK, ha="center")
    ax.text(5, -0.35,
            "위성은 훼손을 확정하지 않는다. 넓은 대상 지역에서 먼저 확인할 후보를 좁히고, 확정은 현장직원과 드론이 한다\n"
            "— 드론을 대체하는 것이 아니라 어디로 보낼지를 정한다.",
            fontsize=9, color=MUTED, ha="center", linespacing=1.6)
    fig.tight_layout()
    _save(fig, "F3_workflow")


# --- F9: 모듈 아키텍처 -------------------------------------------------------


def fig_architecture() -> None:
    """8개 모듈의 데이터 흐름과 각 모듈이 만들어내는 값."""
    modules = [
        ("OBS", "관측 수집", "Sentinel-2/1 · V-World"),
        ("CHG", "변화 탐지", "계절 정합 이상도"),
        ("AGG", "필지 집계", "feature 벡터"),
        ("RISK", "우선순위 산정", "점수 + 근거"),
        ("O", "큐 · 동선", "Top-N · 출장 묶음"),
        ("FIELD", "현장 결과", "변화 유형 · 사진"),
        ("VERIFY", "검증", "기여도 · Precision@K"),
        ("AGENT", "설명", "근거 요약 · 주간보고"),
    ]
    fig, ax = plt.subplots(figsize=(12, 3.6))
    ax.set_xlim(0, len(modules) * 1.5)
    ax.set_ylim(0, 3)
    ax.axis("off")

    for i, (code, name, out) in enumerate(modules):
        x = i * 1.5 + 0.08
        # AGENT는 판정에 관여하지 않으므로 색을 달리해 위치를 분명히 한다
        fc, ec = ("#fafafa", FAINT) if code == "AGENT" else ("#e6f4ed", BLUE)
        _box(ax, x, 1.15, 1.34, 0.95, f"{code}\n{name}", fc, ec, 9.5, "bold")
        ax.text(x + 0.67, 0.85, out, ha="center", va="top", fontsize=7.8, color=MUTED)
        if i < len(modules) - 1:
            _arrow(ax, (x + 1.36, 1.62), (x + 1.5, 1.62), FAINT, lw=1.2)

    ax.text(len(modules) * 0.75, 2.75, "8개 모듈 — 관측에서 검증까지 하나의 루프",
            fontsize=12.5, fontweight="bold", color=INK, ha="center")
    ax.text(len(modules) * 0.75, 0.2,
            "모든 모듈은 공통 봉투 규약 {status, fallback_tier, data, warnings}을 따른다 — 한 단계가 실패해도 서비스는 낮은 신뢰도로 계속 동작한다.\n"
            "AGENT(회색)는 판정에 관여하지 않는다: 이미 계산된 근거를 읽어 설명만 한다.",
            fontsize=8.5, color=MUTED, ha="center", linespacing=1.6)
    fig.tight_layout()
    _save(fig, "F9_architecture")


FIGURES = {
    "ablation": fig_ablation,
    "seasonal": fig_seasonal_principle,
    "route": fig_route_savings,
    "score": fig_score_breakdown,
    "map": fig_site_map,
    "workflow": fig_workflow,
    "architecture": fig_architecture,
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", choices=list(FIGURES), help="일부만 생성")
    args = parser.parse_args()

    targets = args.only or list(FIGURES)
    print(f"figure {len(targets)}종 생성 (API: {API_BASE})\n")
    for name in targets:
        print(f"[{name}]")
        try:
            FIGURES[name]()
        except Exception as e:  # noqa: BLE001 — 하나 실패해도 나머지는 만든다
            print(f"  실패: {type(e).__name__}: {e}")
    print(f"\n완료 -> {OUT_DIR}/")


if __name__ == "__main__":
    main()
