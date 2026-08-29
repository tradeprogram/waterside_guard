"""B급 확장 — 여러 시/군/구에 걸친 배치 파이프라인 실행(module_obs.batch 사용).

기존 `run_priority_queue_demo.py`는 용인시 유방동 10필지만 처리했다 — 한강유역
5,526필지 전체는 이미 §3.2에서 폴리곤 복원까지 끝났지만, OBS→CHG→AGG→RISK
파이프라인은 유방동에서만 돌렸었다(사용자 지적, 2026-08-29). 이 스크립트는
`module_obs.batch.run_batch()`로 다른 시/군/구 표본을 효율적으로 추가한다 —
site당 개별 Earth Engine 호출이 아니라 이미지(관측 장면)당 1회 호출로 전체
site를 한 번에 처리하므로, 표본이 몇 배로 늘어도 API 왕복 수는 거의 그대로다
(§ module_obs/batch.py 참조).

사용법:
    python scripts/run_priority_queue_batch.py --per-region 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from shapely.geometry import mapping

from common.geo import geometry_5179_to_4326, point_5179_to_4326
from common.weather import fetch_recent_rainfall_mm
from module_agg.run import run as agg_run
from module_chg.run import compute_change_from_scenes
from module_obs.batch import run_batch, run_batch_sar
from module_risk.run import run as risk_run

BASELINE_PERIOD = ["2024-06-01", "2024-08-31"]
CURRENT_PERIOD = ["2026-06-01", "2026-08-25"]

# 유방동(경기도 용인시)은 scripts/run_priority_queue_demo.py로 이미 실증했으니
# 여기서는 다른 지역을 표본으로 뽑는다 — "왜 유방동만 보는가"에 대한 답.
TARGET_SIGUNGU_PREFIXES = [
    "경기도 양평군",
    "경기도 가평군",
    "경기도 광주시",
    "경기도 남양주시",
    "경기도 여주시",
]


def main() -> None:
    # Windows 콘솔 기본 codepage(cp949)는 em-dash 등 일부 유니코드 문자를 인코딩 못 해 print()가
    # 죽는다 — 배치 도중 크래시하면 이미 실행한 Earth Engine 호출 비용이 낭비되므로 방어적으로 설정.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/processed/hanriver_maesu_parcels.geojson")
    parser.add_argument("--output", default="data/processed/hanriver_priority_queue.geojson")
    parser.add_argument("--per-region", type=int, default=10, help="시/군/구당 표본 필지 수")
    args = parser.parse_args()

    load_dotenv()

    gdf = gpd.read_file(args.input)  # EPSG:5179 (scripts/fetch_parcel_geometry.py 저장 규약)

    samples = []
    for prefix in TARGET_SIGUNGU_PREFIXES:
        subset = gdf[gdf["addr"].str.startswith(prefix)].head(args.per_region)
        samples.append(subset)
        print(f"{prefix}: {len(subset)}건 선택")

    sample_gdf = pd.concat(samples).reset_index(drop=True)
    print(f"\n총 {len(sample_gdf)}건 배치 처리 시작")

    sites_for_obs = []
    site_meta: dict[str, dict] = {}
    for row in sample_gdf.itertuples():
        site_id = f"HANRIVER_{row.pnu}"
        geometry_4326 = geometry_5179_to_4326(mapping(row.geometry))
        sites_for_obs.append({"site_id": site_id, "geometry_4326": geometry_4326})
        site_meta[site_id] = {"pnu": row.pnu, "jibun": row.jibun, "addr": row.addr, "geometry": row.geometry}

    print("Earth Engine 배치 조회 — Sentinel-2 기준기간(2024)...")
    baseline_result = run_batch({"sites": sites_for_obs, "date_range": BASELINE_PERIOD})
    print("Earth Engine 배치 조회 — Sentinel-2 현재기간(2026)...")
    current_result = run_batch({"sites": sites_for_obs, "date_range": CURRENT_PERIOD})
    # SAR(Sentinel-1)는 구름과 무관하게 관측되므로 광학과 별개로 조회한다(§module_obs/batch.py).
    print("Earth Engine 배치 조회 — Sentinel-1 SAR 기준기간(2024)...")
    baseline_sar_result = run_batch_sar({"sites": sites_for_obs, "date_range": BASELINE_PERIOD})
    print("Earth Engine 배치 조회 — Sentinel-1 SAR 현재기간(2026)...")
    current_sar_result = run_batch_sar({"sites": sites_for_obs, "date_range": CURRENT_PERIOD})

    baseline_by_site = baseline_result["data"]["scenes_by_site"]
    current_by_site = current_result["data"]["scenes_by_site"]
    baseline_sar_by_site = baseline_sar_result["data"]["sar_vv_mean_by_site"]
    current_sar_by_site = current_sar_result["data"]["sar_vv_mean_by_site"]

    print("Open-Meteo 최근 강우량 조회...")
    rainfall_by_site: dict[str, float | None] = {}
    for site_id, meta in site_meta.items():
        centroid_5179 = meta["geometry"].centroid
        lon, lat = point_5179_to_4326(centroid_5179.x, centroid_5179.y)
        rainfall_by_site[site_id] = fetch_recent_rainfall_mm(lat, lon, as_of_date=CURRENT_PERIOD[1])

    rows = []
    for site_id, meta in site_meta.items():
        baseline_scenes = baseline_by_site.get(site_id, [])
        current_scenes = current_by_site.get(site_id, [])
        recent_rainfall_mm = rainfall_by_site.get(site_id)
        computed = compute_change_from_scenes(
            baseline_scenes,
            current_scenes,
            baseline_sar_vv_mean=baseline_sar_by_site.get(site_id),
            current_sar_vv_mean=current_sar_by_site.get(site_id),
        )

        if computed is None:
            anomaly_score = None
            change_type_hint = "no_significant_change"
            contributing_factors: list = []
            risk_score = None
            risk_tier = None
            sar_vv_delta = None
        else:
            agg_result = agg_run(
                {
                    "site_id": site_id,
                    "chg_results": [computed],
                    "site_attributes": {"recent_rainfall_mm": recent_rainfall_mm},
                }
            )
            risk_result = risk_run({"site_id": site_id, "features": agg_result["data"]["features"]})
            anomaly_score = computed["anomaly_score"]
            change_type_hint = computed["change_type_hint"]
            contributing_factors = risk_result["data"]["contributing_factors"]
            risk_score = risk_result["data"]["risk_score"]
            risk_tier = risk_result["data"]["risk_tier"]
            sar_vv_delta = computed.get("sar_vv_delta")

        rows.append(
            {
                "site_id": site_id,
                "pnu": meta["pnu"],
                "jibun": meta["jibun"],
                "addr": meta["addr"],
                "risk_score": risk_score,
                "risk_tier": risk_tier,
                "anomaly_score": anomaly_score,
                "change_type_hint": change_type_hint,
                "sar_vv_delta": sar_vv_delta,
                "recent_rainfall_mm": recent_rainfall_mm,
                "contributing_factors_json": json.dumps(contributing_factors, ensure_ascii=False),
                "baseline_scenes_json": json.dumps(baseline_scenes, ensure_ascii=False),
                "current_scenes_json": json.dumps(current_scenes, ensure_ascii=False),
                "geometry": meta["geometry"],
            }
        )

    result_gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:5179")
    result_gdf = result_gdf.sort_values("risk_score", ascending=False, na_position="last").reset_index(drop=True)
    result_gdf.insert(0, "rank", range(1, len(result_gdf) + 1))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result_gdf.to_file(out_path, driver="GeoJSON", encoding="utf-8")

    summary_path = out_path.with_suffix(".json")
    summary = result_gdf.drop(columns="geometry").to_dict(orient="records")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    n_success = int(result_gdf["risk_score"].notna().sum())
    print(f"\n완료: {n_success}/{len(result_gdf)}건 위험도 산정 -> {out_path}, {summary_path}")


if __name__ == "__main__":
    main()
