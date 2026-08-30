"use client";

import type { SeasonalAnomaly } from "@/lib/api";

const W = 320;
const H = 110;
const PAD_L = 34;
const PAD_R = 10;
const PAD_T = 10;
const PAD_B = 22;

/**
 * "같은 계절 과거 N년의 정상 범위" 밴드 위에 올해 값을 찍어, 벗어난 정도를 눈으로 보여준다.
 *
 * 이 차트가 방어하는 공격: *"작년 6월과 올해 4월을 비교하면 NDVI가 떨어지는 게 당연하지 않나?"*
 * 회색 밴드(median ± MAD)가 "해마다 자연스럽게 흔들리는 폭"이고, 빨간 점이 그 밖에 있으면
 * 계절 변동으로 설명되지 않는다는 뜻이다(§module_chg/run.py compute_seasonal_anomaly).
 *
 * 외부 차트 라이브러리 없이 순수 SVG로 그린다 — 이 프로젝트의 TimeSeriesChart와 같은 방식.
 */
export default function SeasonalBaselineChart({ seasonal }: { seasonal: SeasonalAnomaly | null }) {
  if (!seasonal || seasonal.years_used < 2) return null;

  const historical = seasonal.yearly?.filter((y) => y.ndvi_median !== null) ?? [];
  const points = [...historical.map((y) => ({ label: String(y.year), value: y.ndvi_median as number, current: false }))];
  points.push({ label: "올해", value: seasonal.current_ndvi, current: true });

  const values = points.map((p) => p.value);
  const bandLow = seasonal.historical_median - seasonal.historical_mad;
  const bandHigh = seasonal.historical_median + seasonal.historical_mad;
  const min = Math.min(...values, bandLow);
  const max = Math.max(...values, bandHigh);
  // 위아래 여유를 둬서 점이 테두리에 붙지 않게 한다
  const span = Math.max(max - min, 0.05) * 1.25;
  const mid = (max + min) / 2;
  const lo = mid - span / 2;

  const x = (i: number) => PAD_L + (i * (W - PAD_L - PAD_R)) / Math.max(points.length - 1, 1);
  const y = (v: number) => PAD_T + (1 - (v - lo) / span) * (H - PAD_T - PAD_B);

  const outside = Math.abs(seasonal.robust_z) > 3;

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          같은 계절 {seasonal.years_used}년 정상범위 대비
        </h3>
        <span className={`text-xs font-semibold ${outside ? "text-red-600" : "text-neutral-500"}`}>
          {seasonal.robust_z > 0 ? "+" : ""}
          {seasonal.robust_z.toFixed(1)}σ
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="계절 정상범위 대비 현재 NDVI">
        {/* 정상범위 밴드 (median ± MAD) */}
        <rect
          x={PAD_L}
          y={y(bandHigh)}
          width={W - PAD_L - PAD_R}
          height={Math.max(y(bandLow) - y(bandHigh), 1)}
          fill="#d4d4d4"
          opacity={0.55}
        />
        {/* 과거 중앙값 기준선 */}
        <line
          x1={PAD_L}
          x2={W - PAD_R}
          y1={y(seasonal.historical_median)}
          y2={y(seasonal.historical_median)}
          stroke="#737373"
          strokeWidth={1}
          strokeDasharray="3 2"
        />
        {/* y축 라벨 — 밴드 상·하한만 */}
        <text x={4} y={y(bandHigh) + 3} fontSize={8} fill="#737373">
          {bandHigh.toFixed(2)}
        </text>
        <text x={4} y={y(bandLow) + 3} fontSize={8} fill="#737373">
          {bandLow.toFixed(2)}
        </text>

        {points.map((p, i) => (
          <g key={p.label}>
            <circle
              cx={x(i)}
              cy={y(p.value)}
              r={p.current ? 5 : 3.5}
              fill={p.current ? (outside ? "#dc2626" : "#16a34a") : "#525252"}
            />
            <text x={x(i)} y={H - 8} fontSize={9} textAnchor="middle" fill={p.current ? "#171717" : "#737373"}>
              {p.label}
            </text>
          </g>
        ))}
      </svg>

      <p className="text-xs text-neutral-500">
        회색 띠 = 과거 {seasonal.years_used}년 같은 시기의 정상 변동폭(중앙값 ± MAD).{" "}
        {outside
          ? "올해 값이 그 밖에 있어 계절 변동만으로는 설명되지 않습니다."
          : "올해 값이 정상 변동폭 안에 있습니다."}
      </p>
    </div>
  );
}
