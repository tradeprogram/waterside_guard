"use client";

import type { Scene } from "@/lib/api";

// 순수 SVG 스파크라인 — 외부 차트 라이브러리 없이 기준기간/비교기간 NDVI를 나란히 보여준다.
export default function TimeSeriesChart({ baseline, current }: { baseline: Scene[]; current: Scene[] }) {
  const all = [...baseline, ...current].map((s) => s.indices.ndvi_mean).filter((v): v is number => v != null);
  if (all.length === 0) return <p className="text-[13px] text-ink-3">관측 자료 없음</p>;

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
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full rounded"
        style={{ background: "rgba(108,123,138,0.08)" }}
        role="img"
        aria-label="기준기간 대비 비교기간 NDVI 시계열"
      >
        {basePoints.length > 1 && (
          <polyline
            points={basePoints.join(" ")}
            fill="none"
            stroke="var(--ink-3)"
            strokeWidth={2}
            strokeDasharray="4 3"
          />
        )}
        {curPoints.length > 1 && (
          <polyline points={curPoints.join(" ")} fill="none" stroke="var(--brand)" strokeWidth={2.4} />
        )}
      </svg>
      <div className="mt-1.5 flex gap-4 text-[11px] text-ink-2">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: "var(--ink-3)" }} />
          기준기간 (2024)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: "var(--brand)" }} />
          비교기간 (2026)
        </span>
      </div>
    </div>
  );
}
