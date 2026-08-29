"""좌표계 변환 헬퍼 — ARCHITECTURE.md §4.1.

내부 분석·저장은 EPSG:5179(한국 UTM-K), 웹 지도 출력 직전에만 EPSG:4326으로
재투영한다. 이 파일이 그 경계를 명시적으로 표시하는 유일한 지점이 되도록,
다른 모듈은 pyproj를 직접 import하지 말고 이 헬퍼를 통해서만 변환한다.

예외 — Module OBS가 Sentinel Hub에 AOI를 조회할 때는 입력이 EPSG:4326이어야
하므로 `geometry_5179_to_4326`으로 한 번 더 반대 방향 변환을 허용한다
(Sentinel Hub·V-World 등 외부 API 경계에서만).
"""
from __future__ import annotations

from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform as shapely_transform

_TO_4326 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
_TO_5179 = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)


def point_5179_to_4326(x_5179: float, y_5179: float) -> tuple[float, float]:
    """(x_5179, y_5179) -> (lon, lat). UI 출력 직전에만 호출할 것."""
    lon, lat = _TO_4326.transform(x_5179, y_5179)
    return lon, lat


def point_4326_to_5179(lon: float, lat: float) -> tuple[float, float]:
    """(lon, lat) -> (x_5179, y_5179). 외부 API(V-World 등) 응답을 내부 저장 규약으로 변환할 때 사용."""
    x, y = _TO_5179.transform(lon, lat)
    return x, y


def geometry_5179_to_4326(geometry_5179: dict) -> dict:
    """GeoJSON geometry(EPSG:5179) -> GeoJSON geometry(EPSG:4326).

    외부 관측 API(Sentinel Hub) 조회 시 AOI를 4326으로 넘겨야 하는 경계에서만
    사용한다 — 내부 저장·모듈 간 교환은 계속 5179를 유지한다.
    """
    geom = shape(geometry_5179)
    reprojected = shapely_transform(lambda x, y: _TO_4326.transform(x, y), geom)
    return mapping(reprojected)
