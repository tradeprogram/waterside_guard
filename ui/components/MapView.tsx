"use client";

import { useEffect, useRef } from "react";
import { Map as MapLibreMap, type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Site } from "@/lib/api";

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
      center: [127.2095, 37.2622], // 유방동 AOI 중심
      zoom: 16,
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
    };

    if (map.isStyleLoaded()) render();
    else map.once("load", render);
  }, [sites, selectedSiteId]);

  return <div ref={containerRef} className="h-full w-full" />;
}
