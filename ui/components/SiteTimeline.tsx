"use client";

import type { Scene, SeasonalAnomaly } from "@/lib/api";
import { CHANGE_TYPE_LABEL } from "./InspectionForm";

type Event =
  | { kind: "seasonal"; date: string; label: string; value: number; detail: string }
  | { kind: "scene"; date: string; label: string; value: number; detail: string }
  | { kind: "inspection"; date: string; label: string; detail: string };

function formatDate(iso: string): string {
  return iso.slice(0, 10);
}

/**
 * 한 필지의 변화 이력을 하나의 시간축에 모은다 — 과거 동일 계절 관측, 금년 관측, 현장점검
 * 기록이 각각 다른 화면에 흩어져 있으면 이 필지가 어떻게 변해왔는지를 읽을 수 없다.
 *
 * 리서치가 P2로 꼽은 복원 후 변화 이력 관리에 해당한다. 점검 이력이 없는 필지도 많으므로
 * 관측만으로도 의미 있게 보이도록 설계했다.
 */
export default function SiteTimeline({
  seasonal,
  currentScenes,
  inspections,
}: {
  seasonal: SeasonalAnomaly | null;
  currentScenes: Scene[];
  inspections: Record<string, unknown>[];
}) {
  const events: Event[] = [];

  // 과거 동일 계절 관측 — 연도만 있으므로 그 해 여름을 대표 날짜로 둔다
  for (const y of seasonal?.yearly ?? []) {
    if (y.ndvi_median === null) continue;
    events.push({
      kind: "seasonal",
      date: `${y.year}-08-15`,
      label: `${y.year}년 동일 계절`,
      value: y.ndvi_median,
      detail: `NDVI ${y.ndvi_median.toFixed(3)} · 관측 ${y.scene_count}건`,
    });
  }

  for (const s of currentScenes) {
    if (s.indices.ndvi_mean === null) continue;
    events.push({
      kind: "scene",
      date: s.acquisition_date,
      label: "금년 관측",
      value: s.indices.ndvi_mean,
      detail: `NDVI ${s.indices.ndvi_mean.toFixed(3)} · 운량 ${s.cloud_cover_pct}%`,
    });
  }

  for (const insp of inspections) {
    const at = typeof insp.inspected_at === "string" ? insp.inspected_at : null;
    if (!at) continue;
    const found = insp.actual_anomaly_found === true;
    const category = typeof insp.anomaly_category === "string" ? insp.anomaly_category : null;
    events.push({
      kind: "inspection",
      date: formatDate(at),
      label: "현장점검",
      detail: found ? `변화 확인 (${category ? CHANGE_TYPE_LABEL[category] ?? category : "유형 미분류"})` : "변화 없음",
    });
  }

  if (events.length === 0) return null;
  events.sort((a, b) => a.date.localeCompare(b.date));

  const median = seasonal?.historical_median;
  const mad = seasonal?.historical_mad;

  return (
    <div>
      <h3 className="section-title mb-1.5">관측·점검 이력</h3>
      <ol className="relative flex flex-col gap-1.5 border-l border-line pl-3">
        {events.map((e, i) => {
          // 정상 범위를 벗어난 관측을 색으로 표시 — 시간축에서 언제 이탈했는지 보인다
          const outside =
            "value" in e && median != null && mad != null
              ? Math.abs(e.value - median) > Math.max(1.4826 * mad, 0.03) * 2
              : false;
          const dot =
            e.kind === "inspection"
              ? "var(--ink)"
              : outside
                ? "var(--danger)"
                : e.kind === "seasonal"
                  ? "var(--ink-3)"
                  : "var(--ok)";
          return (
            <li key={i} className="relative text-[11px]">
              <span className="absolute -left-[17px] top-1 h-2 w-2 rounded-full" style={{ background: dot }} />
              <span className="font-mono text-[10px] text-ink-3">{e.date}</span>{" "}
              <span className={e.kind === "inspection" ? "font-semibold text-ink" : "text-ink-2"}>{e.label}</span>
              <span className="text-ink-3"> · {e.detail}</span>
            </li>
          );
        })}
      </ol>
      <p className="mt-1.5 text-[11px] text-ink-3">
        회색 = 과거 동일 계절, 녹색 = 금년 관측, 적색 = 정상범위 이탈, 흑색 = 현장점검
      </p>
    </div>
  );
}
