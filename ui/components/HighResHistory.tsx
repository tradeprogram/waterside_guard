"use client";

import { useEffect, useState } from "react";
import { fetchHighRes, type HighResHistoryData } from "@/lib/api";

const CELL = 110; // 한 타일을 화면에 그릴 크기(px) — 3×3이면 330px

/** GeoJSON 좌표 배열에서 [lng, lat] 쌍만 재귀적으로 뽑는다(MapView의 collectLngLat과 같은 역할). */
function collectRings(coords: unknown, out: [number, number][][]): void {
  if (!Array.isArray(coords) || coords.length === 0) return;
  const first = coords[0];
  if (Array.isArray(first) && typeof first[0] === "number") {
    out.push(coords as [number, number][]);
    return;
  }
  for (const c of coords) collectRings(c, out);
}

/**
 * 시기별 고해상도 실사 영상 — 현장직원이 출동 전에 "갈 만한가"를 눈으로 판단하는 화면.
 *
 * **왜 NDVI 썸네일과 별개로 필요한가**: NDVI는 Sentinel-2 10m라 필지 중앙값 883㎡가
 * 약 3×3 픽셀밖에 안 된다 — 무엇이 달라졌는지 눈으로 확인할 수 없다. Wayback은
 * 서브미터급이라 건물·토공·나지화가 실제로 보인다(§api_server /highres).
 *
 * **의도적으로 판정하지 않는다**: 이 화면은 근거를 보여줄 뿐, 시스템이 "훼손됨"이라고
 * 확정하지 않는다. 0.5m급으로도 예초와 식생 소실은 구분되지 않기 때문에, 확정은
 * 현장·드론의 몫이다(§ARCHITECTURE.md 범위 제한).
 */
export default function HighResHistory({ siteId }: { siteId: string }) {
  const [data, setData] = useState<HighResHistoryData | null>(null);
  const [failed, setFailed] = useState(false);
  const loading = !failed && data?.site_id !== siteId;

  useEffect(() => {
    let cancelled = false;
    fetchHighRes(siteId)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  if (loading) return <p className="text-sm text-neutral-400">고해상도 영상 불러오는 중...</p>;
  if (failed || !data || data.epochs.length === 0) return null;

  const [west, north, east, south] = data.bounds;
  const size = CELL * data.grid;

  // 필지 경계를 타일 격자 위에 SVG로 얹는다 — 어느 필지를 봐야 하는지 표시해야 의미가 있다.
  const rings: [number, number][][] = [];
  if (data.geometry_geojson && "coordinates" in data.geometry_geojson) {
    collectRings((data.geometry_geojson as { coordinates: unknown }).coordinates, rings);
  }
  const polygons = rings.map((ring) =>
    ring.map(([lon, lat]) => `${((lon - west) / (east - west)) * size},${((lat - north) / (south - north)) * size}`).join(" ")
  );

  return (
    <div>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        고해상도 실사 영상 (시기별)
      </h3>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {data.epochs.map((epoch) => (
          <figure key={epoch.date} className="m-0 shrink-0">
            <div className="relative" style={{ width: size, height: size }}>
              {epoch.tiles.map((row, ri) =>
                row.map((url, ci) => (
                  // eslint-disable-next-line @next/next/no-img-element -- 외부(Esri) 타일, next/image 최적화 불필요
                  <img
                    key={`${ri}-${ci}`}
                    src={url}
                    alt=""
                    className="absolute"
                    style={{ left: ci * CELL, top: ri * CELL, width: CELL, height: CELL }}
                  />
                ))
              )}
              <svg className="absolute inset-0" width={size} height={size}>
                {polygons.map((points, i) => (
                  <polygon key={i} points={points} fill="none" stroke="#ff3b30" strokeWidth={2} />
                ))}
              </svg>
            </div>
            <figcaption className="mt-0.5 text-center text-xs text-neutral-500">{epoch.date}</figcaption>
          </figure>
        ))}
      </div>
      <p className="mt-1 text-xs text-neutral-400">
        빨간 테두리가 대상 필지입니다. 날짜는 Esri 배포일이라 시기마다 촬영 계절이 달라
        초록/갈색 차이가 날 수 있습니다 — 건물·토공·나지화 같은 <strong>구조적 변화</strong>를 보세요.
      </p>
    </div>
  );
}
