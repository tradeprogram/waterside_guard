"use client";

import { useEffect, useState } from "react";
import { fetchEvidence, fetchTimeseries, type Site, type Scene } from "@/lib/api";
import TimeSeriesChart from "./TimeSeriesChart";
import InspectionForm from "./InspectionForm";
import NdviThumbnails from "./NdviThumbnails";
import HighResHistory from "./HighResHistory";
import ScoreBreakdown from "./ScoreBreakdown";
import EvidenceConfidence from "./EvidenceConfidence";
import SeasonalBaselineChart from "./SeasonalBaselineChart";

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

      {/* "위험도"가 아니라 "점검 우선순위"임을 점수 옆에 항상 명시한다 — 이 값은 환경피해
          발생확률로 calibration된 게 아니라 운영상 ranking이다(§ Module RISK 명칭 정리). */}
      <div>
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold tabular-nums">{site.inspection_priority_score ?? "–"}</span>
          <span className="rounded bg-neutral-200 px-2 py-1 text-sm font-medium">{site.priority_tier}</span>
        </div>
        <p className="mt-1 text-xs text-neutral-500">
          점검 우선순위 점수 (0~100) — 훼손 확률이 아니라 &ldquo;먼저 가볼 순서&rdquo;를 나타내는 운영 지표입니다.
        </p>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">왜 이 순위인가</h3>
        <ScoreBreakdown
          factors={evidence?.contributing_factors ?? []}
          weightCoverage={evidence?.weight_coverage}
        />
        {site.change_type_hint && site.change_type_hint !== "no_significant_change" && (
          <p className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">
            변화 힌트: {site.change_type_hint} — 종 판독이 아니라 &ldquo;계절패턴과 다른 변화가 있다&rdquo;는 선별 신호일 뿐입니다.
          </p>
        )}
        {evidence?.changed_area_ratio_source === "approximated" && (
          <p className="mt-1 text-xs text-neutral-500">
            변화 면적은 픽셀 실측이 아니라 이상도 크기로부터의 근사치입니다(관측 부족).
          </p>
        )}
      </div>

      <SeasonalBaselineChart seasonal={evidence?.seasonal_anomaly ?? null} />

      <EvidenceConfidence confidence={evidence?.evidence_confidence ?? null} />

      <HighResHistory siteId={site.site_id} />

      <NdviThumbnails siteId={site.site_id} />

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
