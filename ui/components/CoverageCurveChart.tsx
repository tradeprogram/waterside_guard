"use client";

import type { CoveragePoint } from "@/lib/api";

const W = 420;
const H = 260;
const PAD_L = 44;
const PAD_R = 90; // 범례 자리
const PAD_T = 12;
const PAD_B = 34;

const SERIES_STYLE: Record<string, { label: string; color: string; dash?: string }> = {
  proposed: { label: "수변가드(다요인)", color: "#171717" },
  ndvi_only: { label: "NDVI 이상도만", color: "#2563eb", dash: "4 3" },
  recency: { label: "마지막 점검일만", color: "#ea580c", dash: "4 3" },
};

/**
 * "현장점검 가능 비율(상위 K%) vs 실제 변화 발견 비율(recall)" 곡선.
 *
 * 중간점검 리서치가 공모전에서 가장 강력한 한 장으로 꼽은 그래프 — 목표는 "정확도 몇 %"가
 * 아니라 **"전체의 상위 20%만 확인해서 실제 변화의 몇 %를 잡았는가"**다.
 * 회색 대각선이 무작위 랭킹(상위 K%에서 recall도 K%)이고, 곡선이 그 위로 볼록할수록
 * 우선순위화가 실제로 기여했다는 뜻이다.
 */
export default function CoverageCurveChart({ curves }: { curves: Record<string, CoveragePoint[]> }) {
  const series = Object.entries(curves).filter(([, pts]) => pts.length > 0);
  if (series.length === 0) return null;

  const x = (pct: number) => PAD_L + (pct / 100) * (W - PAD_L - PAD_R);
  const y = (recall: number) => PAD_T + (1 - recall) * (H - PAD_T - PAD_B);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="점검 커버리지 대비 변화 발견율">
        {/* 격자 + 축 눈금 */}
        {[0, 0.25, 0.5, 0.75, 1].map((r) => (
          <g key={r}>
            <line x1={PAD_L} x2={W - PAD_R} y1={y(r)} y2={y(r)} stroke="#e5e5e5" strokeWidth={1} />
            <text x={PAD_L - 6} y={y(r) + 3} fontSize={9} textAnchor="end" fill="#737373">
              {Math.round(r * 100)}%
            </text>
          </g>
        ))}
        {[0, 25, 50, 75, 100].map((p) => (
          <text key={p} x={x(p)} y={H - 16} fontSize={9} textAnchor="middle" fill="#737373">
            {p}%
          </text>
        ))}

        {/* 무작위 기준선 — 이 대각선 위로 볼록해야 우선순위화가 작동한 것 */}
        <line x1={x(0)} y1={y(0)} x2={x(100)} y2={y(1)} stroke="#a3a3a3" strokeWidth={1} strokeDasharray="2 3" />
        <text x={x(52)} y={y(0.5) - 4} fontSize={8} fill="#a3a3a3" transform={`rotate(-22 ${x(52)} ${y(0.5)})`}>
          무작위
        </text>

        {series.map(([name, points]) => {
          const style = SERIES_STYLE[name] ?? { label: name, color: "#737373" };
          // 원점(0%, 0)에서 시작해야 곡선의 시작 기울기가 정직하게 보인다
          const d = [`M ${x(0)} ${y(0)}`, ...points.map((p) => `L ${x(p.coverage_pct)} ${y(p.recall)}`)].join(" ");
          return (
            <g key={name}>
              <path d={d} fill="none" stroke={style.color} strokeWidth={name === "proposed" ? 2.5 : 1.5} strokeDasharray={style.dash} />
              {name === "proposed" &&
                points.map((p) => <circle key={p.coverage_pct} cx={x(p.coverage_pct)} cy={y(p.recall)} r={2.5} fill={style.color} />)}
            </g>
          );
        })}

        {/* 범례 */}
        {series.map(([name], i) => {
          const style = SERIES_STYLE[name] ?? { label: name, color: "#737373" };
          return (
            <g key={name} transform={`translate(${W - PAD_R + 6}, ${PAD_T + 10 + i * 16})`}>
              <line x1={0} x2={14} y1={0} y2={0} stroke={style.color} strokeWidth={2} strokeDasharray={style.dash} />
              <text x={18} y={3} fontSize={9} fill="#404040">
                {style.label}
              </text>
            </g>
          );
        })}

        <text x={(PAD_L + W - PAD_R) / 2} y={H - 3} fontSize={9} textAnchor="middle" fill="#525252">
          현장점검 가능 비율 (상위 K%)
        </text>
      </svg>
      <p className="text-xs text-neutral-500">
        가로축은 &ldquo;전체 대상지 중 몇 %를 점검할 여력이 있는가&rdquo;, 세로축은 &ldquo;그 범위 안에서 실제 변화
        사례의 몇 %를 찾았는가&rdquo;입니다. 무작위 대각선 위로 볼록할수록 우선순위화가 실제로 기여한 것입니다.
      </p>
    </div>
  );
}
