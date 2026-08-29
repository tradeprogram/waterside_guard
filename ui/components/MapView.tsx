"use client";

import { useEffect, useRef } from "react";
import { LngLatBounds, Map as MapLibreMap, type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Site } from "@/lib/api";

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

// risk_tier(§ARCHITECTURE.md Module RISK) 색상 — 등급 4단계
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
}: {
  sites: Site[];
  selectedSiteId: string | null;
  onSelectSite: (siteId: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const onSelectSiteRef = useRef(onSelectSite);
  const hasFitBoundsRef = useRef(false);

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

    map.on("load", () => {
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

      map.on("click", "sites-fill", (e) => {
        const siteId = e.features?.[0]?.properties?.site_id;
        if (siteId) onSelectSiteRef.current(siteId);
      });
      map.on("mouseenter", "sites-fill", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "sites-fill", () => (map.getCanvas().style.cursor = ""));
    });

    return () => {
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
      if (!source) return;

      const features = sites
        .filter((s) => s.geometry_geojson)
        .map((s) => ({
          type: "Feature" as const,
          geometry: s.geometry_geojson!,
          properties: {
            site_id: s.site_id,
            risk_score: s.risk_score,
            color: TIER_COLOR[s.risk_tier ?? "정상"] ?? "#999999",
            selected: s.site_id === selectedSiteId,
          },
        }));
      source.setData({ type: "FeatureCollection", features });

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

    if (map.isStyleLoaded()) render();
    else map.once("load", render);
  }, [sites, selectedSiteId]);

  return <div ref={containerRef} className="h-full w-full" />;
}
