"use client";

import { useEffect, useState } from "react";
import { fetchEvidence, fetchTimeseries, type Site, type Scene } from "@/lib/api";
import TimeSeriesChart from "./TimeSeriesChart";
import InspectionForm from "./InspectionForm";

const FACTOR_LABEL: Record<string, string> = {
  anomaly_score_mean: "위성 이상도(계절 대비 변화)",
  changed_area_ratio: "변화 면적 비율",
  last_inspection_days_ago: "마지막 점검 후 경과일",
  adjacent_to_water: "수변 인접 여부",
  past_anomaly_count: "과거 이상 발생 횟수",
};

export default function EvidencePanel({ site, onInspectionSubmitted }: { site: Site; onInspectionSubmitted: () => void }) {
  const [timeseries, setTimeseries] = useState<{ baseline_scenes: Scene[]; current_scenes: Scene[] } | null>(null);
  const [evidence, setEvidence] = useState<Awaited<ReturnType<typeof fetchEvidence>> | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchEvidence(site.site_id).then((d) => !cancelled && setEvidence(d));
    fetchTimeseries(site.site_id).then((d) => !cancelled && setTimeseries(d));
    return () => {
      cancelled = true;
    };
  }, [site.site_id]);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div>
        <h2 className="font-mono text-sm text-neutral-500">{site.pnu}</h2>
        <p className="text-lg font-semibold">{site.addr ?? site.site_id}</p>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-3xl font-bold tabular-nums">{site.risk_score ?? "–"}</span>
        <span className="rounded bg-neutral-200 px-2 py-1 text-sm font-medium">{site.risk_tier}</span>
      </div>

      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">왜 이 순위인가</h3>
        <ul className="flex flex-col gap-1 text-sm">
          {(evidence?.contributing_factors ?? []).map((f) => (
            <li key={f.factor} className="flex justify-between border-b border-neutral-100 py-1">
              <span>{FACTOR_LABEL[f.factor] ?? f.factor}</span>
              <span className="font-mono text-neutral-600">
                {typeof f.value === "boolean" ? (f.value ? "예" : "아니오") : String(f.value)}
              </span>
            </li>
          ))}
          {evidence && evidence.contributing_factors.length === 0 && (
            <li className="text-neutral-400">근거 요인 없음(위성 관측 미확보)</li>
          )}
        </ul>
        {site.change_type_hint && site.change_type_hint !== "no_significant_change" && (
          <p className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">
            변화 힌트: {site.change_type_hint} — 종 판독이 아니라 &ldquo;계절패턴과 다른 변화가 있다&rdquo;는 선별 신호일 뿐입니다.
          </p>
        )}
      </div>

      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">위성 시계열 (NDVI)</h3>
        {timeseries ? (
          <TimeSeriesChart baseline={timeseries.baseline_scenes} current={timeseries.current_scenes} />
        ) : (
          <p className="text-sm text-neutral-400">불러오는 중...</p>
        )}
      </div>

      <InspectionForm siteId={site.site_id} onSubmitted={onInspectionSubmitted} />

      {site.inspections.length > 0 && (
        <div>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            점검 이력 ({site.inspections.length}건)
          </h3>
          <ul className="text-xs text-neutral-600">
            {site.inspections.map((insp, i) => (
              <li key={i}>{JSON.stringify(insp)}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
