"""End-to-end 파이프라인 데모 — OBS→CHG→AGG→RISK를 실제 유방동 필지에 돌려
Priority Queue를 만든다(ARCHITECTURE.md §11.4 "심사위원에게 보여줄 가장
강력한 한 장"의 첫 실증).

전체 82필지가 아니라 앞쪽 N개만 처리한다 — 필지당 CHG 호출 1회가 OBS 호출
2회(기준기간·현재기간)를 부르고, 각 OBS 호출이 Earth Engine getInfo 4회를
쓰므로 필지당 최대 8회 API 왕복이다. 전체 배치 처리는 §12 로드맵 B급
확장(reduceRegions로 여러 AOI를 한 번에 묶는 성능 개선)에서 다룬다.

사용법:
    python scripts/run_priority_queue_demo.py --limit 10
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv
from shapely.geometry import mapping

from module_agg.run import run as agg_run
from module_chg.run import run as chg_run
from module_obs.run import run as obs_run
from module_obs.water import is_adjacent_to_water
from module_risk.run import run as risk_run
from common.geo import geometry_5179_to_4326, point_5179_to_4326
from common.weather import fetch_recent_rainfall_mm

BASELINE_PERIOD = ["2024-06-01", "2024-08-31"]
CURRENT_PERIOD = ["2026-06-01", "2026-08-25"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/processed/yongin_yubang_parcels.geojson")
    parser.add_argument("--output", default="data/processed/yongin_yubang_priority_queue.geojson")
    parser.add_argument("--limit", type=int, default=10, help="처리할 필지 수(기본 10)")
    args = parser.parse_args()

    load_dotenv()

    gdf = gpd.read_file(args.input)  # EPSG:5179 (scripts/fetch_parcel_geometry.py 저장 규약)
    subset = gdf.head(args.limit)

    rows = []
    for i, row in enumerate(subset.itertuples(), start=1):
        site_id = f"YUBANG_{row.pnu}"
        geometry_5179 = mapping(row.geometry)

        print(f"[{i}/{len(subset)}] {site_id} 처리 중...")

        centroid_5179 = row.geometry.centroid
        lon, lat = point_5179_to_4326(centroid_5179.x, centroid_5179.y)
        recent_rainfall_mm = fetch_recent_rainfall_mm(lat, lon, as_of_date=CURRENT_PERIOD[1])

        chg_result = chg_run(
            {
                "aoi_id": site_id,
                "site_geometry_5179": geometry_5179,
                "baseline_period": BASELINE_PERIOD,
                "current_period": CURRENT_PERIOD,
                "recent_rainfall_mm": recent_rainfall_mm,
            }
        )
        geometry_4326_for_water = geometry_5179_to_4326(mapping(row.geometry))
        adjacent_to_water = is_adjacent_to_water(geometry_4326_for_water)

        agg_result = agg_run(
            {
                "site_id": site_id,
                "pnu": row.pnu,
                "chg_results": [chg_result["data"]],
                # site_attributes: KECI 내부 자산 DB 접근 불가(§ Module AGG 구현 상태 참조) — recent_rainfall_mm·
                # adjacent_to_water는 공개 데이터(Open-Meteo·JRC Global Surface Water)로 채울 수 있고
                # 나머지(복원경과일·최근점검일·과거이상이력)는 여전히 None.
                "site_attributes": {"recent_rainfall_mm": recent_rainfall_mm, "adjacent_to_water": adjacent_to_water},
            }
        )

        risk_result = risk_run({"site_id": site_id, "features": agg_result["data"]["features"]})

        # Evidence Card/Time Series 화면(§8)이 쓸 원자료 — CHG는 집계값만 반환하므로
        # 장면 단위 시계열은 OBS를 한 번 더 불러 별도로 확보한다(재사용 아님, §12 TODO 참조).
        geometry_4326 = geometry_5179_to_4326(geometry_5179)
        baseline_obs = obs_run({"aoi_id": site_id, "date_range": BASELINE_PERIOD, "aoi_geometry_4326": geometry_4326})
        current_obs = obs_run({"aoi_id": site_id, "date_range": CURRENT_PERIOD, "aoi_geometry_4326": geometry_4326})

        rows.append(
            {
                "site_id": site_id,
                "pnu": row.pnu,
                "jibun": row.jibun,
                "addr": row.addr,
                "inspection_priority_score": risk_result["data"]["inspection_priority_score"],
                "priority_tier": risk_result["data"]["priority_tier"],
                "weight_coverage": risk_result["data"]["weight_coverage"],
                "anomaly_score": chg_result["data"].get("anomaly_score"),
                "change_type_hint": chg_result["data"].get("change_type_hint"),
                "sar_vv_delta": chg_result["data"].get("sar_vv_delta"),
                "recent_rainfall_mm": recent_rainfall_mm,
                "adjacent_to_water": adjacent_to_water,
                "changed_area_ratio_source": chg_result["data"].get("changed_area_ratio_source"),
                "evidence_confidence_json": json.dumps(chg_result["data"].get("evidence_confidence"), ensure_ascii=False),
                "anomaly_method": chg_result["data"].get("anomaly_method"),
                "seasonal_anomaly_json": json.dumps(chg_result["data"].get("seasonal_anomaly"), ensure_ascii=False),
                "chg_status": chg_result["status"],
                "contributing_factors_json": json.dumps(risk_result["data"]["contributing_factors"], ensure_ascii=False),
                "baseline_scenes_json": json.dumps(baseline_obs["data"].get("scenes", []), ensure_ascii=False),
                "current_scenes_json": json.dumps(current_obs["data"].get("scenes", []), ensure_ascii=False),
                "geometry": row.geometry,
            }
        )

    result_gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:5179")
    result_gdf = result_gdf.sort_values("inspection_priority_score", ascending=False).reset_index(drop=True)
    result_gdf.insert(0, "rank", range(1, len(result_gdf) + 1))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result_gdf.to_file(out_path, driver="GeoJSON", encoding="utf-8")

    summary_path = out_path.with_suffix(".json")
    summary = result_gdf.drop(columns="geometry").to_dict(orient="records")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n완료: {len(result_gdf)}건 -> {out_path}, {summary_path}")


if __name__ == "__main__":
    main()
