"use client";

import type { Scene } from "@/lib/api";

// 순수 SVG 스파크라인 — 외부 차트 라이브러리 없이 baseline/current NDVI를 나란히 보여준다.
export default function TimeSeriesChart({ baseline, current }: { baseline: Scene[]; current: Scene[] }) {
  const all = [...baseline, ...current].map((s) => s.indices.ndvi_mean).filter((v): v is number => v != null);
  if (all.length === 0) return <p className="text-sm text-neutral-500">관측 데이터 없음</p>;

  const min = Math.min(...all, 0);
  const max = Math.max(...all, 1);
  const width = 320;
  const height = 90;
  const pad = 8;

  const toPoints = (scenes: Scene[]) => {
    const vals = scenes.map((s) => s.indices.ndvi_mean).filter((v): v is number => v != null);
    return vals.map((v, i) => {
      const x = pad + (i / Math.max(vals.length - 1, 1)) * (width - 2 * pad);
      const y = height - pad - ((v - min) / (max - min || 1)) * (height - 2 * pad);
      return `${x},${y}`;
    });
  };

  const basePoints = toPoints(baseline);
  const curPoints = toPoints(current);

  return (
    <div>
      <svg width={width} height={height} className="rounded bg-neutral-50">
        {basePoints.length > 1 && (
          <polyline points={basePoints.join(" ")} fill="none" stroke="#94a3b8" strokeWidth={2} strokeDasharray="4 3" />
        )}
        {curPoints.length > 1 && <polyline points={curPoints.join(" ")} fill="none" stroke="#c0392b" strokeWidth={2} />}
      </svg>
      <div className="mt-1 flex gap-4 text-xs text-neutral-600">
        <span>
          <span className="inline-block h-2 w-2 rounded-full bg-slate-400 align-middle" /> 기준기간(2024) NDVI
        </span>
        <span>
          <span className="inline-block h-2 w-2 rounded-full bg-red-700 align-middle" /> 현재기간(2026) NDVI
        </span>
      </div>
    </div>
  );
}
