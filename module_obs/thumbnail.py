"""Module OBS — NDVI 썸네일 생성 (§8 UI 구현 상태에서 "아직 없다"고 적어둔
Before/After 위성영상, Module OBS의 `composite_ref` 예약 필드를 실제로
채우는 지점).

**왜 필요한가**: 지금까지 지도는 위험도 색상으로 칠한 행정 폴리곤만 보여줬다
— "위성 관측 기반"이라면서 정작 위성이 실제로 무엇을 봤는지는 화면 어디에도
없었다(사용자 지적, 2026-08-29). 이 모듈은 선택된 대상지의 NDVI를 실제로
색상화한 PNG를 Earth Engine `getThumbURL()`로 생성해, 지도 위에 실제 좌표로
얹거나 Evidence Card에 그대로 보여줄 수 있게 한다.

**호출 시점 — 배치가 아니라 on-demand**: 대상지가 60개라고 60개 전부
미리 썸네일을 만들어두지 않는다 — 실제로 클릭해서 보는 대상지에 대해서만
API가 그때 생성한다(§7 `/sites/{id}/thumbnails`). 배치로 다 만들면 site
수만큼 Earth Engine 왕복이 늘어나 §12 B급 확장에서 고친 배치 조회의
이점을 스스로 깎아먹는다.
"""
from __future__ import annotations

from common.envelope import error_envelope, make_envelope
from module_obs.run import CLOUD_SCL_CLASSES, MAX_TILE_CLOUDY_PIXEL_PCT, _init_ee

NDVI_PALETTE = [
    "a50026", "d73027", "f46d43", "fdae61", "fee08b",
    "d9ef8b", "a6d96a", "66bd63", "1a9850", "006837",
]  # 낮음(적색) -> 높음(녹색) 식생지수, ColorBrewer RdYlGn
BUFFER_M = 150  # 대상지 폴리곤 자체가 수백 m²로 작아서 맥락 없이는 알아보기 어렵다
THUMB_DIMENSION_PX = 256


def _fetch_ndvi_thumbnail(geometry_4326: dict, date_range: list[str]) -> dict | None:
    import ee

    site_geom = ee.Geometry(geometry_4326)
    region = site_geom.buffer(BUFFER_M).bounds()

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(date_range[0], date_range[1])
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_TILE_CLOUDY_PIXEL_PCT))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )

    if collection.size().getInfo() == 0:
        return None

    img = collection.first()
    scl = img.select("SCL")
    valid_mask = scl.remap(CLOUD_SCL_CLASSES, [0] * len(CLOUD_SCL_CLASSES), defaultValue=1)
    ndvi = img.normalizedDifference(["B8", "B4"]).updateMask(valid_mask)
    vis = ndvi.visualize(min=-0.2, max=0.9, palette=NDVI_PALETTE)

    url = vis.getThumbURL({"region": region, "dimensions": THUMB_DIMENSION_PX, "format": "png"})

    # bbox 좌표와 촬영일을 한 번의 getInfo() 호출로 같이 받는다(왕복 절약).
    info = ee.Dictionary({"coords": region.coordinates(), "date": img.date().format("YYYY-MM-dd")}).getInfo()
    ring = info["coords"][0]
    lons = [c[0] for c in ring]
    lats = [c[1] for c in ring]
    minlon, maxlon, minlat, maxlat = min(lons), max(lons), min(lats), max(lats)
    # MapLibre "image" source가 요구하는 순서: [좌상단, 우상단, 우하단, 좌하단]
    image_coordinates = [[minlon, maxlat], [maxlon, maxlat], [maxlon, minlat], [minlon, minlat]]

    return {"url": url, "image_coordinates": image_coordinates, "acquisition_date": info["date"]}


def run(input: dict) -> dict:
    site_id = input.get("site_id", "unknown")
    geometry_4326 = input.get("aoi_geometry_4326")
    date_range = input.get("date_range")

    if not geometry_4326 or not date_range:
        return error_envelope(f"[{site_id}] aoi_geometry_4326/date_range가 필요합니다.", fallback_tier=3)

    init_error = _init_ee()
    if init_error:
        return make_envelope({"thumbnail": None}, status="degraded", fallback_tier=3, warnings=[init_error])

    try:
        thumbnail = _fetch_ndvi_thumbnail(geometry_4326, date_range)
    except Exception as e:  # noqa: BLE001 — 모듈 경계에서는 모든 예외를 degraded로 흡수(§4.2)
        return error_envelope(f"[{site_id}] NDVI 썸네일 생성 실패: {e}", fallback_tier=2)

    if thumbnail is None:
        return make_envelope(
            {"thumbnail": None},
            status="degraded",
            fallback_tier=2,
            warnings=[f"[{site_id}] {date_range} 구간에 유효 관측이 없어 썸네일을 만들 수 없습니다."],
        )

    return make_envelope({"thumbnail": thumbnail}, status="ok", fallback_tier=1)
