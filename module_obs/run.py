"""Module OBS — 관측 수집·전처리 (ARCHITECTURE.md §5 Module OBS).

Sentinel-2/1을 Sentinel Hub Statistical API로 조회해 AOI 단위 NDVI/NDMI 통계
시계열을 만든다. 픽셀 래스터 전체를 내려받지 않고 서버 사이드에서 AOI
zonal statistics만 계산하므로 MVP 단계의 대역폭·저장 비용이 낮다.

자격증명(SENTINELHUB_CLIENT_ID/SECRET)이 없으면 예외를 던지지 않고
degraded envelope을 반환한다 — ARCHITECTURE.md §0.5 "AI가 실패해도
서비스가 작동하는 설계" 원칙을 코드로 강제하는 지점.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any

from common.envelope import error_envelope, make_envelope

NDVI_NDMI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B03", "B04", "B08", "B11", "SCL", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1 },
      { id: "ndmi", bands: 1 },
      { id: "dataMask", bands: 1 },
    ],
  };
}

function evaluatePixel(s) {
  let ndvi = (s.B08 - s.B04) / (s.B08 + s.B04);
  let ndmi = (s.B08 - s.B11) / (s.B08 + s.B11);
  // SCL 3=구름그림자 8/9=구름 10=씨러스 -> dataMask에서 제외
  let cloud = [3, 8, 9, 10].includes(s.SCL) ? 0 : s.dataMask;
  return {
    ndvi: [ndvi],
    ndmi: [ndmi],
    dataMask: [cloud],
  };
}
"""


def _load_config():
    """SENTINELHUB_CLIENT_ID/SECRET이 있으면 SHConfig를, 없으면 None을 반환한다."""
    client_id = os.environ.get("SENTINELHUB_CLIENT_ID")
    client_secret = os.environ.get("SENTINELHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    from sentinelhub import SHConfig

    config = SHConfig()
    config.sh_client_id = client_id
    config.sh_client_secret = client_secret
    return config


def _bbox_from_geometry_4326(geometry_4326: dict) -> tuple[float, float, float, float]:
    """GeoJSON geometry(EPSG:4326)에서 bbox(minx, miny, maxx, maxy)를 뽑는다."""
    coords = geometry_4326["coordinates"]

    def _flatten(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for sub in c:
                yield from _flatten(sub)

    pts = list(_flatten(coords))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _fetch_statistics(config, bbox: tuple[float, float, float, float], date_range: list[str]) -> list[dict[str, Any]]:
    from sentinelhub import (
        BBox,
        CRS,
        DataCollection,
        SentinelHubStatistical,
        Geometry,
    )

    sh_bbox = BBox(bbox=bbox, crs=CRS.WGS84)

    request = SentinelHubStatistical(
        aggregation=SentinelHubStatistical.aggregation(
            evalscript=NDVI_NDMI_EVALSCRIPT,
            time_interval=(date_range[0], date_range[1]),
            aggregation_interval="P1D",  # 일 단위 — Sentinel-2 재방문 주기(~5일)상 장면 단위와 사실상 동일
        ),
        input_data=[
            SentinelHubStatistical.input_data(
                DataCollection.SENTINEL2_L2A,
                maxcc=0.3,  # 구름 30% 이상 장면은 애초에 요청 단계에서 제외
            )
        ],
        bbox=sh_bbox,
        config=config,
    )
    result = request.get_data()[0]

    scenes = []
    for interval_result in result.get("data", []):
        stats = interval_result.get("outputs", {})
        ndvi_stats = stats.get("ndvi", {}).get("bands", {}).get("B0", {}).get("stats")
        ndmi_stats = stats.get("ndmi", {}).get("bands", {}).get("B0", {}).get("stats")
        mask_stats = stats.get("dataMask", {}).get("bands", {}).get("B0", {}).get("stats")
        if not ndvi_stats or mask_stats is None or mask_stats.get("sampleCount", 0) == 0:
            continue
        valid_ratio = mask_stats.get("mean", 0.0)
        scenes.append(
            {
                "source": "sentinel2",
                "acquisition_date": interval_result["interval"]["from"][:10],
                "cloud_cover_pct": round((1 - valid_ratio) * 100, 1),
                "indices": {
                    "ndvi_mean": round(ndvi_stats.get("mean"), 4) if ndvi_stats.get("mean") is not None else None,
                    "ndmi_mean": round(ndmi_stats.get("mean"), 4) if ndmi_stats and ndmi_stats.get("mean") is not None else None,
                },
            }
        )
    return scenes


def run(input: dict) -> dict:
    aoi_id = input.get("aoi_id", "unknown")
    date_range = input.get("date_range")
    geometry_4326 = input.get("aoi_geometry_4326")

    if not date_range or not geometry_4326:
        return error_envelope(
            f"[{aoi_id}] date_range 또는 aoi_geometry_4326이 없어 관측을 조회할 수 없습니다.",
            fallback_tier=3,
        )

    config = _load_config()
    if config is None:
        return make_envelope(
            {"aoi_id": aoi_id, "scenes": [], "composite_ref": None},
            status="degraded",
            fallback_tier=3,
            warnings=[
                "SENTINELHUB_CLIENT_ID/SECRET이 .env에 없습니다 — 관측 데이터 없이 빈 결과를 반환합니다. "
                ".env.example 참조."
            ],
        )

    try:
        bbox = _bbox_from_geometry_4326(geometry_4326)
        scenes = _fetch_statistics(config, bbox, date_range)
    except Exception as e:  # noqa: BLE001 — 모듈 경계에서는 모든 예외를 degraded로 흡수한다 (ARCHITECTURE.md §4.2)
        return error_envelope(f"[{aoi_id}] Sentinel Hub 조회 실패: {e}", fallback_tier=2)

    if not scenes:
        return make_envelope(
            {"aoi_id": aoi_id, "scenes": [], "composite_ref": None},
            status="degraded",
            fallback_tier=2,
            warnings=[f"[{aoi_id}] {date_range} 구간에 유효한 장면이 없습니다(구름 등)."],
        )

    return make_envelope(
        {"aoi_id": aoi_id, "scenes": scenes, "composite_ref": None},
        status="ok",
        fallback_tier=1,
    )
