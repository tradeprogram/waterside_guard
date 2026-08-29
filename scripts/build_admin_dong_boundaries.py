"""행정동(읍면동) 경계 GeoJSON 생성 — 지도 배경 컨텍스트용(사용자 제공 데이터).

사용자가 제공한 전국 읍면동 경계 shapefile(`BND_ADM_DONG_PG`, EPSG:5186,
필드 ADM_CD/ADM_NM/BASE_DATE만 있음 — 시/군/구·시/도 이름은 없음)을
현재 대상지 60건이 있는 범위로만 잘라 정적 GeoJSON으로 만든다.

**왜 필요한가**: 지도 위 대상지 폴리곤이 수백 m² 크기라 배경 없이 보면
"의미 없는 사각형이 떠 있다"는 인상을 준다(사용자 지적, 2026-08-29) —
실제로는 NDVI 썸네일의 bounding box일 뿐이지만, 진짜 행정동 경계를
배경 레이어로 깔면 "이 필지가 어느 동에 속하는지" 시각적 맥락이 생긴다.

**시/군/구 이름으로 필터링하지 않는다** — 이 shapefile엔 시/군/구 이름이
없어서(ADM_NM은 읍면동명뿐) 문자열 매칭이 안 된다. 대신 대상지 60건의
경계상자(EPSG:5179)를 5km 버퍼로 확장해 공간적으로 교차하는 읍면동만
남긴다 — sido/sigungu 조인용 외부 참조(vuski/admdongkor 등)가 없어도 된다.

사용법:
    python scripts/build_admin_dong_boundaries.py --shapefile "C:\\sb2\\mask\\BND_ADM_DONG_PG (2)\\BND_ADM_DONG_PG.shp"
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

BUFFER_M = 5000  # 대상지 경계상자를 이만큼 넓혀서 인접 읍면동까지 포함(초기 가정치)
OUTPUT_PATHS = [
    Path("data/processed/admin_dong_boundaries.geojson"),
    Path("ui/public/admin_dong_boundaries.geojson"),  # Next.js가 정적 파일로 그대로 서빙
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shapefile", required=True, help="BND_ADM_DONG_PG.shp 경로")
    args = parser.parse_args()

    site_gdfs = []
    for path in ["data/processed/hanriver_priority_queue.geojson", "data/processed/yongin_yubang_priority_queue.geojson"]:
        site_gdfs.append(gpd.read_file(path))  # EPSG:5179
    sites = pd.concat(site_gdfs)

    from shapely.geometry import box

    minx, miny, maxx, maxy = sites.total_bounds
    bbox_5179 = gpd.GeoDataFrame(
        geometry=[box(minx - BUFFER_M, miny - BUFFER_M, maxx + BUFFER_M, maxy + BUFFER_M)], crs="EPSG:5179"
    )

    dong = gpd.read_file(args.shapefile).to_crs("EPSG:5179")
    print(f"전국 읍면동 {len(dong)}건 로드, EPSG:5179로 재투영 완료")

    clipped = dong[dong.intersects(bbox_5179.geometry.iloc[0])].copy()
    print(f"대상지 범위(+{BUFFER_M}m 버퍼)와 교차하는 읍면동 {len(clipped)}건 선별")

    clipped = clipped[["ADM_CD", "ADM_NM", "geometry"]].to_crs("EPSG:4326")
    # 배경 컨텍스트용이라 측량급 정밀도가 필요 없다 — 원본 그대로 저장하면 6MB를 넘어
    # 클라이언트가 매번 받기엔 무겁다. 0.0001도(~11m) 단순화로 브라우저에서 눈에 띄지
    # 않는 수준까지 정점 수를 크게 줄인다.
    clipped["geometry"] = clipped.geometry.simplify(0.0001, preserve_topology=True)

    for out_path in OUTPUT_PATHS:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        clipped.to_file(out_path, driver="GeoJSON", encoding="utf-8")
        print(f"저장: {out_path}")


if __name__ == "__main__":
    main()
