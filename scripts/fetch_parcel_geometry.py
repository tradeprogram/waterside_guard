"""
Milestone 1 — PNU 코드로 V-World 연속지적도(LP_PA_CBND_BUBUN)에서 필지 폴리곤을 복원한다.

ARCHITECTURE.md §3.2 참조. 입력 CSV는 `토지고유코드`(PNU, 19자리) 컬럼을 가진
data/raw/*.csv 형식(hanriver_maesu_raw.csv / yongin_yubang_maesu.csv)을 기대한다.

사용법:
    python scripts/fetch_parcel_geometry.py \
        --input data/raw/yongin_yubang_maesu.csv \
        --output data/processed/yongin_yubang_parcels.geojson
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from dotenv import load_dotenv
from shapely.geometry import shape

VWORLD_URL = "http://api.vworld.kr/req/data"
LAYER = "LP_PA_CBND_BUBUN"  # 연속지적도
REQUEST_INTERVAL_SEC = 0.2  # V-World 호출량 보호용 최소 간격


def fetch_parcel(pnu: str, service_key: str, session: requests.Session) -> dict | None:
    """PNU 1건에 대해 V-World 연속지적도 GetFeature를 호출해 GeoJSON Feature를 반환한다."""
    params = {
        "key": service_key,
        "service": "data",
        "request": "GetFeature",
        "page": 1,
        "size": 10,
        "data": LAYER,
        "attrFilter": f"pnu:like:{pnu}",
    }
    res = session.get(VWORLD_URL, params=params, verify=False, timeout=15)
    res.raise_for_status()
    payload = json.loads(res.content.decode("utf-8"))

    response = payload.get("response", {})
    if response.get("status") != "OK":
        return None

    features = (
        response.get("result", {}).get("featureCollection", {}).get("features", [])
    )
    if not features:
        return None
    return features[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="입력 CSV (토지고유코드 컬럼 필요)")
    parser.add_argument("--output", required=True, help="출력 GeoJSON 경로")
    parser.add_argument("--limit", type=int, default=None, help="테스트용 상한 건수")
    args = parser.parse_args()

    load_dotenv()
    import os

    service_key = os.environ.get("VWORLD_API_KEY")
    if not service_key:
        raise SystemExit(".env에 VWORLD_API_KEY가 없습니다 — .env.example 참조")

    df = pd.read_csv(args.input, dtype={"토지고유코드": str})
    pnus = df["토지고유코드"].tolist()
    if args.limit:
        pnus = pnus[: args.limit]

    session = requests.Session()
    records = []
    not_found = []

    for i, pnu in enumerate(pnus, start=1):
        try:
            feature = fetch_parcel(pnu, service_key, session)
        except requests.RequestException as e:
            print(f"[{i}/{len(pnus)}] {pnu} 요청 실패: {e}")
            not_found.append(pnu)
            continue

        if feature is None:
            not_found.append(pnu)
        else:
            props = feature.get("properties", {})
            records.append(
                {
                    "pnu": pnu,
                    "jibun": props.get("jibun"),
                    "addr": props.get("addr"),
                    "gosi_year": props.get("gosi_year"),
                    "geometry": shape(feature["geometry"]),
                }
            )

        if i % 10 == 0 or i == len(pnus):
            print(f"[{i}/{len(pnus)}] 처리 중... (성공 {len(records)}, 미확인 {len(not_found)})")

        time.sleep(REQUEST_INTERVAL_SEC)

    if not records:
        raise SystemExit("복원된 필지가 없습니다 — API 키·attrFilter 문법을 확인하세요")

    # V-World 응답은 EPSG:4326(lon/lat) — 내부 규약(ARCHITECTURE.md §4.1)에 맞춰 EPSG:5179로 저장
    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
    gdf_5179 = gdf.to_crs("EPSG:5179")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gdf_5179.to_file(out_path, driver="GeoJSON", encoding="utf-8")

    print(f"\n완료: {len(records)}/{len(pnus)}건 복원 -> {out_path}")
    if not_found:
        miss_path = out_path.with_name(out_path.stem + "_미확인_pnu.txt")
        miss_path.write_text("\n".join(not_found), encoding="utf-8")
        print(f"미확인 PNU {len(not_found)}건 -> {miss_path}")


if __name__ == "__main__":
    main()
