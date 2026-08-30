"""Esri Wayback — 날짜별 고해상도 실사 영상 조회 (Ground Truth 판독용).

**왜 NDVI 썸네일이 아니라 이것인가**: Silver-A 라벨링(§README Ground Truth 워크플로)은
사람이 Before/After를 눈으로 보고 "실제로 뭔가 달라졌나"를 판정하는 작업이다. 그런데
기존 `module_obs/thumbnail.py`의 NDVI 컬러 이미지로 판독하면 두 가지 문제가 있다:

1. **순환논리** — 알고리즘이 판단 근거로 쓴 바로 그 NDVI를 사람이 다시 보고 확인하는
   꼴이라, 독립적인 정답지가 되지 못한다.
2. **해상도 부족** — Sentinel-2는 10m/픽셀인데 우리 필지 중앙값이 883㎡(약 3×3 픽셀),
   최소는 4㎡로 1픽셀도 안 된다. 육안 판독이 물리적으로 불가능하다.

Esri Wayback은 World Imagery의 **날짜별 과거 스냅샷**(2014~현재, 196개 릴리스)을
서브미터급으로 제공한다. z18에서 한 타일이 약 120m를 덮으므로 3×3로 이어붙이면
필지(수십 m)와 주변 맥락이 함께 보인다 — 실측으로 확인된 판독 가능한 화질이다.

**주의**: 특정 지역에 모든 날짜의 영상이 있는 것은 아니다. 같은 타일이 여러 릴리스에서
동일한 바이트를 반환하면 그 사이 갱신이 없었다는 뜻이다(내용 해시로 중복 제거).
"""
from __future__ import annotations

import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import requests

CONFIG_URL = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"
TILE_URL = (
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0"
    "/default028mm/MapServer/tile/{release}/{z}/{y}/{x}"
)
TILE_PX = 256
DEFAULT_ZOOM = 18  # Esri World Imagery는 국내 시골 지역에서 z19+에 실제 영상이 없다(실측)
MIN_TILE_BYTES = 1000  # 이보다 작으면 빈/placeholder 타일로 본다


def deg2num(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2.0**z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def num2deg(x: float, y: float, z: int) -> tuple[float, float]:
    """타일 좌표(실수 허용) -> (lat, lon). 폴리곤을 픽셀로 옮길 때 쓴다."""
    n = 2.0**z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


@lru_cache(maxsize=1)
def list_releases() -> tuple[tuple[str, str], ...]:
    """((날짜 'YYYY-MM-DD', 릴리스번호), ...) — 날짜 오름차순. 실패하면 빈 튜플."""
    try:
        cfg = requests.get(CONFIG_URL, timeout=30).json()
    except Exception:  # noqa: BLE001 — 부가 기능, 실패해도 파이프라인은 계속된다
        return ()
    items = []
    for release, meta in cfg.items():
        title = meta.get("itemTitle", "")
        # 형식: "World Imagery (Wayback 2023-08-31)"
        if "Wayback " in title and title.endswith(")"):
            items.append((title[-11:-1], release))
    return tuple(sorted(items))


def fetch_tile(release: str, z: int, x: int, y: int) -> bytes | None:
    try:
        r = requests.get(TILE_URL.format(release=release, z=z, y=y, x=x), timeout=25)
    except Exception:  # noqa: BLE001
        return None
    if r.status_code != 200 or len(r.content) < MIN_TILE_BYTES:
        return None
    return r.content


# 영상 시기(epoch) 탐색은 릴리스를 전수 조사해야 정확하다 — 표본만 훑으면 실제로 존재하는
# 시기를 통째로 놓친다(실측: 25개 표본으로는 2026-05 영상을 못 찾았으나 전수 조사에서는
# 찾았다, 2026-08-31). 대신 site마다 75회씩 왕복하면 60개 site에 4,500회가 되므로,
# 인접 site가 같은 영상을 공유한다는 점을 이용해 성긴 타일(z13, 약 5km) 단위로 캐시한다.
EPOCH_CACHE_ZOOM = 13
_epoch_cache: dict[tuple[int, int], list[dict]] = {}

# 시기 탐색은 지역당 75회 왕복이라 매번 다시 하면 몇 분씩 걸린다 — 결과가 잘 바뀌지 않는
# 값이므로 디스크에 남긴다. Evidence Card가 이 캐시에 의존하므로(§api_server /highres)
# 임시 산출물이 아니라 저장소에 커밋하는 데이터 자산으로 취급한다.
EPOCH_CACHE_FILE = Path("data/processed/wayback_epochs.json")
MAX_WORKERS = 8  # Esri 타일 서버에 과하지 않은 수준의 동시 요청


def _load_disk_cache() -> None:
    if _epoch_cache or not EPOCH_CACHE_FILE.exists():
        return
    try:
        raw = json.loads(EPOCH_CACHE_FILE.read_text(encoding="utf-8"))
        for key, epochs in raw.items():
            x, y = key.split(",")
            _epoch_cache[(int(x), int(y))] = epochs
    except Exception:  # noqa: BLE001 — 캐시는 부가 기능, 깨졌으면 그냥 다시 조회한다
        pass


def _save_disk_cache() -> None:
    try:
        EPOCH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        EPOCH_CACHE_FILE.write_text(
            json.dumps({f"{k[0]},{k[1]}": v for k, v in _epoch_cache.items()}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        pass


def find_epochs(lat: float, lon: float, since: str = "2021") -> list[dict]:
    """이 지역에서 **실제로 서로 다른 영상 시기**를 [{date, release}] 로 반환한다(오래된 순).

    같은 원본 영상을 다시 배포한 릴리스가 많아 바이트 해시로 중복을 제거한다. 반환되는
    `date`는 **배포일이지 촬영일이 아니다** — Esri는 촬영일을 공개하지 않으므로, 판독 화면은
    계절 차이를 훼손으로 오판하지 않도록 별도로 안내해야 한다(§scripts/build_label_candidates.py).
    """
    _load_disk_cache()
    key = deg2num(lat, lon, EPOCH_CACHE_ZOOM)
    if key in _epoch_cache:
        return _epoch_cache[key]

    releases = [r for r in list_releases() if r[0] >= since]
    x, y = key

    # 릴리스를 순차로 훑으면 지역당 75회 × 왕복시간이라 너무 느리다 — 동시에 받는다.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        contents = list(pool.map(lambda r: fetch_tile(r[1], EPOCH_CACHE_ZOOM, x, y), releases))

    seen: dict[str, dict] = {}
    for (date, release), content in zip(releases, contents):
        if content is None:
            continue
        digest = hashlib.md5(content).hexdigest()
        if digest not in seen:
            seen[digest] = {"date": date, "release": release}

    epochs = sorted(seen.values(), key=lambda v: v["date"])
    _epoch_cache[key] = epochs
    _save_disk_cache()
    return epochs


def pick_release_near(versions: list[dict], target_date: str) -> dict | None:
    """target_date에 가장 가까운 버전. 없으면 None."""
    if not versions:
        return None
    return min(versions, key=lambda v: abs((_ord(v["date"]) - _ord(target_date))))


def _ord(date: str) -> int:
    y, m, d = date.split("-")
    return int(y) * 372 + int(m) * 31 + int(d)  # 대소 비교용 근사 — 정확한 일수일 필요 없다


def fetch_mosaic(lat: float, lon: float, release: str, z: int = DEFAULT_ZOOM, grid: int = 3):
    """중심 좌표 주변 grid×grid 타일을 이어붙인 PIL 이미지와 지리 범위를 반환한다.

    returns (image, bounds) where bounds = (west, north, east, south) in degrees,
    or (None, None) if 타일을 하나도 못 받았을 때.
    """
    from PIL import Image

    from io import BytesIO

    cx, cy = deg2num(lat, lon, z)
    half = grid // 2
    canvas = Image.new("RGB", (TILE_PX * grid, TILE_PX * grid), (32, 32, 32))
    got_any = False

    offsets = [(dx, dy) for dy in range(-half, half + 1) for dx in range(-half, half + 1)]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        contents = list(pool.map(lambda o: fetch_tile(release, z, cx + o[0], cy + o[1]), offsets))

    for (dx, dy), content in zip(offsets, contents):
        if content is None:
            continue
        try:
            tile = Image.open(BytesIO(content)).convert("RGB")
        except Exception:  # noqa: BLE001
            continue
        canvas.paste(tile, ((dx + half) * TILE_PX, (dy + half) * TILE_PX))
        got_any = True

    if not got_any:
        return None, None

    north, west = num2deg(cx - half, cy - half, z)
    south, east = num2deg(cx + half + 1, cy + half + 1, z)
    return canvas, (west, north, east, south)


def draw_parcel(image, bounds, geometry_4326: dict, color=(255, 60, 60), width: int = 3):
    """필지 경계를 이미지 위에 그린다 — 판독자가 *어느 필지*를 봐야 하는지 알아야 한다."""
    from PIL import ImageDraw

    west, north, east, south = bounds
    w, h = image.size

    def to_px(lon: float, lat: float) -> tuple[float, float]:
        return ((lon - west) / (east - west) * w, (lat - north) / (south - north) * h)

    def rings(coords):
        """Polygon/MultiPolygon의 외곽 링만 재귀적으로 뽑는다."""
        if not coords:
            return []
        if isinstance(coords[0][0], (int, float)):
            return [coords]
        out = []
        for c in coords:
            out.extend(rings(c))
        return out

    draw = ImageDraw.Draw(image)
    for ring in rings(geometry_4326.get("coordinates", [])):
        pts = [to_px(lon, lat) for lon, lat in ring]
        if len(pts) >= 2:
            draw.line(pts + [pts[0]], fill=color, width=width)
    return image
