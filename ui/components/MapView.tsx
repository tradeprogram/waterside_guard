"use client";

import { useEffect, useRef, useState } from "react";
import { LngLatBounds, Map as MapLibreMap, type GeoJSONSource, type ImageSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { fetchThumbnails, type RouteStop, type Site } from "@/lib/api";

// GeoJSON Polygon/MultiPolygon 좌표 배열을 재귀적으로 훑어 [lng, lat] 쌍만 뽑는다.
// turf 같은 외부 라이브러리 없이 bbox 계산용으로만 쓴다.
function collectLngLat(coords: unknown, out: [number, number][]) {
  if (!Array.isArray(coords)) return;
  if (coords.length === 2 && typeof coords[0] === "number" && typeof coords[1] === "number") {
    out.push([coords[0], coords[1]]);
    return;
  }
  for (const c of coords) collectLngLat(c, out);
}

// 대상지 폴리곤(수백 m²)의 정확한 중심은 아니지만, 마커를 찍을 위치로는 충분한
// 근사치(꼭짓점 평균) — turf 등 외부 라이브러리 없이 계산한다.
function approxCentroid(geometry: GeoJSON.Geometry): [number, number] | null {
  const points: [number, number][] = [];
  if ("coordinates" in geometry) collectLngLat(geometry.coordinates, points);
  if (points.length === 0) return null;
  const [sumLon, sumLat] = points.reduce(([sLon, sLat], [lon, lat]) => [sLon + lon, sLat + lat], [0, 0]);
  return [sumLon / points.length, sumLat / points.length];
}

// map.once("load", cb") 패턴은 이 프로젝트 환경에서 신뢰할 수 없다고 실측으로 여러 번
// 확인됐다(2026-08-29·30 — "load"가 아예 안 오거나, 이미 소비된 뒤라 다시 안 옴). 대신
// 소스가 실제로 존재하는지를 200ms 간격으로 폴링한다 — 이미 있으면 즉시, 없으면 생길 때까지
// 기다린다. cleanup에서 반드시 취소해야 언마운트/의존성 변경 후에도 안 불린다.
function waitForSource(map: MapLibreMap, sourceId: string, callback: () => void): () => void {
  if (map.getSource(sourceId)) {
    callback();
    return () => {};
  }
  const intervalId = setInterval(() => {
    if (map.getSource(sourceId)) {
      clearInterval(intervalId);
      callback();
    }
  }, 200);
  return () => clearInterval(intervalId);
}

// priority_tier(§ARCHITECTURE.md Module RISK) 색상 — 등급 4단계
const TIER_COLOR: Record<string, string> = {
  "1순위": "#c0392b",
  "2순위": "#e67e22",
  "3순위": "#f1c40f",
  정상: "#7f9f7f",
};

export default function MapView({
  sites,
  selectedSiteId,
  onSelectSite,
  budgetSiteIds = [],
  routeStops = [],
}: {
  sites: Site[];
  selectedSiteId: string | null;
  onSelectSite: (siteId: string) => void;
  /** 이번 주 점검 예산 안에 드는 site — 지도에서 테두리로 구분한다(§InspectionBudgetPanel). */
  budgetSiteIds?: string[];
  /** 출장 방문 순서 — 지도에 경로선으로 그린다(§module_o/routing.py). 직선거리 기준이라
      실제 도로가 아니므로 점선으로 그려 "이동 순서"임을 시각적으로 구분한다. */
  routeStops?: RouteStop[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const onSelectSiteRef = useRef(onSelectSite);
  const hasFitBoundsRef = useRef(false);
  // Earth Engine 썸네일 fetch가 끝난 site_id — selectedSiteId와 다르면 "아직 로딩 중"으로
  // 파생시킨다. 실제 setState는 아래 effect의 .then/.catch(비동기) 안에서만 호출하므로
  // set-state-in-effect 린트에 안 걸린다.
  const [overlayReadySiteId, setOverlayReadySiteId] = useState<string | null>(null);
  const overlayLoading = selectedSiteId !== null && overlayReadySiteId !== selectedSiteId;

  // ref는 렌더 중이 아니라 커밋 후(effect)에 갱신한다 — MapLibre의 클릭 콜백은 한 번만 등록되므로
  // 매번 최신 onSelectSite를 읽으려면 ref를 거쳐야 한다.
  useEffect(() => {
    onSelectSiteRef.current = onSelectSite;
  }, [onSelectSite]);

  // 지도는 한 번만 생성 — sites가 바뀔 때마다 재생성하지 않는다(§ 성능)
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new MapLibreMap({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          esri: {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            // Esri World Imagery는 도심 밖 지역(용인/여주/가평 등)에서 zoom 19+에 실제
            // 이미지 없이 "Map data not yet available" placeholder 타일을 반환한다(실측 확인,
            // 2026-08-29). maxzoom을 18로 캡해서 그 이상은 z18 타일을 확대(overzoom)해
            // 쓰게 하면 placeholder가 아예 안 나온다.
            maxzoom: 18,
            attribution: "Esri World Imagery",
          },
        },
        layers: [{ id: "esri", type: "raster", source: "esri" }],
      },
      // 초기값 — 유방동 근처. sites가 로드되면 아래 effect가 전체 대상지 범위로 다시 맞춘다.
      center: [127.2095, 37.2622],
      zoom: 10,
    });
    mapRef.current = map;
    map.on("error", (e) => console.error("MapLibre error:", e.error));

    // "load" 하나에만 의존하지 않고 "idle"·"styledata"·폴링까지 걸어서 무엇이든 먼저
    // 되는 조건으로 설정을 진행한다(2026-08-30, 사용자 환경에서 "load"가 안 오는 사례
    // 실측 확인). 그 이벤트들이 실제로 스타일 준비 전에 먼저 오는 경우도 있어서(그 상태로
    // addSource를 부르면 "Style is not done loading"을 던짐) isStyleLoaded()로 한 번 더
    // 확인하고, 실패하면 setupDone을 다시 false로 둬 다음 이벤트가 재시도하게 한다.
    let setupDone = false;
    const setupLayers = () => {
      if (setupDone) return;
      if (!map.isStyleLoaded()) return; // 아직 준비 안 됐으면 이번 이벤트는 건너뛰고 다음 이벤트를 기다린다
      try {
        // 출장 경로 — 마커보다 먼저 추가해 아래에 깔린다
        map.addSource("route", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
        map.addLayer({
          id: "route-line",
          type: "line",
          source: "route",
          layout: { "line-cap": "round", "line-join": "round" },
          // 점선 = "직선거리 기준 방문 순서"이지 실제 주행 경로가 아니라는 시각적 신호
          paint: { "line-color": "#2563eb", "line-width": 2, "line-dasharray": [2, 2], "line-opacity": 0.8 },
        });

        map.addSource("sites", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
        map.addLayer({
          id: "sites-fill",
          type: "fill",
          source: "sites",
          paint: {
            "fill-color": ["get", "color"],
            "fill-opacity": ["case", ["get", "selected"], 0.85, 0.55],
          },
        });
        map.addLayer({
          id: "sites-outline",
          type: "line",
          source: "sites",
          paint: {
            "line-color": "#1a1a1a",
            "line-width": ["case", ["get", "selected"], 3, 1],
          },
        });

        // 대상지 폴리곤 자체가 수백 m²라, 한강유역 6개 시/군/구를 한 화면에 담는
        // 줌에서는 진짜 모양(위 sites-fill)이 화면에 몇 픽셀도 안 나온다 — 그래서
        // 줌과 무관하게 항상 일정 크기로 보이는 점 마커를 centroid 위치에 별도로
        // 얹는다(2026-08-30, "필지가 안 보인다" 사용자 지적 반영). 폴리곤 소스에
        // circle 레이어를 그대로 못 얹는 이유: circle은 Point/MultiPoint 지오메트리만
        // 그리고 Polygon 피처는 조용히 무시하므로, Point 전용 소스를 따로 둬야 한다.
        map.addSource("sites-points", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
        map.addLayer({
          id: "sites-markers",
          type: "circle",
          source: "sites-points",
          paint: {
            "circle-radius": ["case", ["get", "selected"], 10, 6],
            "circle-color": ["get", "color"],
            // 예산 안에 드는 대상지는 굵은 흰 테두리로 "이번 주에 갈 곳"임을 구분한다
            "circle-stroke-width": ["case", ["get", "inBudget"], 3, 1],
            "circle-stroke-color": ["case", ["get", "inBudget"], "#ffffff", "#d4d4d4"],
            "circle-opacity": ["case", ["get", "inBudget"], 1, 0.5],
          },
        });

        for (const layerId of ["sites-fill", "sites-markers"]) {
          map.on("click", layerId, (e) => {
            const siteId = e.features?.[0]?.properties?.site_id;
            if (siteId) onSelectSiteRef.current(siteId);
          });
          map.on("mouseenter", layerId, () => (map.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", layerId, () => (map.getCanvas().style.cursor = ""));
        }

        // 선택된 대상지의 실제 NDVI 위성 이미지를 지도 위에 얹는 레이어 — 처음엔 소스가
        // 없어야 하므로 화면 밖 아주 작은 좌표로 자리만 잡아둔다(빈 image source는 허용 안 됨).
        map.addSource("ndvi-overlay", {
          type: "image",
          url:
            "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBTAA7",
          coordinates: [
            [0, 0.0001],
            [0.0001, 0.0001],
            [0.0001, 0],
            [0, 0],
          ],
        });
        map.addLayer({ id: "ndvi-overlay-layer", type: "raster", source: "ndvi-overlay", paint: { "raster-opacity": 0.85 } });
        setupDone = true;
      } catch (e) {
        console.error("setupLayers 실패, 다음 이벤트에서 재시도:", e);
      }
    };

    map.on("load", setupLayers);
    map.on("idle", setupLayers);
    map.on("styledata", setupLayers);
    // 위 이벤트들도 전혀 안 왔을 극단적 경우를 대비한 최후 수단 — 1초 간격으로 폴링해서
    // 스타일이 준비되는 즉시 잡아낸다(setupDone 확인되면 스스로 멈춘다).
    const pollId = setInterval(() => {
      if (setupDone) {
        clearInterval(pollId);
        return;
      }
      setupLayers();
    }, 1000);

    return () => {
      clearInterval(pollId);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // sites/selectedSiteId가 바뀔 때마다 지도 위 데이터만 갱신
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const render = () => {
      const source = map.getSource("sites") as GeoJSONSource | undefined;
      const pointSource = map.getSource("sites-points") as GeoJSONSource | undefined;
      if (!source || !pointSource) return;

      const budgetSet = new Set(budgetSiteIds);

      const features = sites
        .filter((s) => s.geometry_geojson)
        .map((s) => ({
          type: "Feature" as const,
          geometry: s.geometry_geojson!,
          properties: {
            site_id: s.site_id,
            inspection_priority_score: s.inspection_priority_score,
            color: TIER_COLOR[s.priority_tier ?? "정상"] ?? "#999999",
            selected: s.site_id === selectedSiteId,
            inBudget: budgetSet.has(s.site_id),
          },
        }));
      source.setData({ type: "FeatureCollection", features });

      const pointFeatures = features
        .map((f) => {
          const centroid = approxCentroid(f.geometry);
          return centroid
            ? { type: "Feature" as const, geometry: { type: "Point" as const, coordinates: centroid }, properties: f.properties }
            : null;
        })
        .filter((f): f is NonNullable<typeof f> => f !== null);
      pointSource.setData({ type: "FeatureCollection", features: pointFeatures });

      // 대상지가 처음 로드된 시점에 한 번만 전체 범위로 맞춘다 — 유방동(단일 동)만이
      // 아니라 한강유역 여러 시/군/구에 흩어진 대상지를 한 화면에서 볼 수 있어야 한다.
      // 이후 재갱신(점검 등록 등)에서는 사용자가 보던 위치를 그대로 유지한다.
      if (!hasFitBoundsRef.current && features.length > 0) {
        const points: [number, number][] = [];
        for (const f of features) {
          if ("coordinates" in f.geometry) collectLngLat(f.geometry.coordinates, points);
        }
        if (points.length > 0) {
          const bounds = points.reduce(
            (b, p) => b.extend(p),
            new LngLatBounds(points[0], points[0])
          );
          map.fitBounds(bounds, { padding: 40, maxZoom: 15, duration: 0 });
          hasFitBoundsRef.current = true;
        }
      }
    };

    return waitForSource(map, "sites", render);
  }, [sites, selectedSiteId, budgetSiteIds]);

  // 출장 경로선 — 방문 순서대로 centroid를 잇는다
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const draw = () => {
      const source = map.getSource("route") as GeoJSONSource | undefined;
      if (!source) return;
      const coordinates = routeStops
        .map((s) => s.lonlat)
        .filter((c): c is [number, number] => Array.isArray(c));
      source.setData(
        coordinates.length >= 2
          ? { type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "LineString", coordinates }, properties: {} }] }
          : { type: "FeatureCollection", features: [] }
      );
    };

    return waitForSource(map, "route", draw);
  }, [routeStops]);

  // 대상지를 선택하면: (1) 실제 NDVI 위성 이미지를 그 위치에 얹고 (2) 알아볼 수 있게 확대한다.
  // 대상지 폴리곤 자체가 수백 m²로 작아서, 60개 전체를 보던 줌 레벨에서는 선택해도 안 보인다.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedSiteId) return;

    let cancelled = false;
    const site = sites.find((s) => s.site_id === selectedSiteId);

    const apply = () => {
      const source = map.getSource("ndvi-overlay") as ImageSource | undefined;
      if (!source) return;

      if (site?.geometry_geojson && "coordinates" in site.geometry_geojson) {
        const points: [number, number][] = [];
        collectLngLat(site.geometry_geojson.coordinates, points);
        if (points.length > 0) {
          const bounds = points.reduce((b, p) => b.extend(p), new LngLatBounds(points[0], points[0]));
          map.fitBounds(bounds, { padding: 150, maxZoom: 18, duration: 500 });
        }
      }

      fetchThumbnails(selectedSiteId)
        .then((res) => {
          if (cancelled) return;
          if (res.current) {
            source.updateImage({ url: res.current.url, coordinates: res.current.image_coordinates });
          }
          setOverlayReadySiteId(selectedSiteId);
        })
        .catch(() => {
          /* 지도 오버레이는 부가 기능 — 실패해도 나머지 화면에 영향 없음 */
          if (!cancelled) setOverlayReadySiteId(selectedSiteId);
        });
    };

    const cancelWait = waitForSource(map, "ndvi-overlay", apply);

    return () => {
      cancelled = true;
      cancelWait();
    };
  }, [selectedSiteId, sites]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {overlayLoading && (
        <div className="pointer-events-none absolute left-1/2 top-4 z-10 flex -translate-x-1/2 items-center gap-2 rounded-full bg-neutral-900/85 px-3 py-1.5 text-xs text-white shadow">
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white" />
          위성 이미지 불러오는 중...
        </div>
      )}
    </div>
  );
}
