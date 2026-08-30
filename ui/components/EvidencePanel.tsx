"use client";

import { useEffect, useState } from "react";
import { fetchEvidence, fetchTimeseries, type Site, type Scene } from "@/lib/api";
import TimeSeriesChart from "./TimeSeriesChart";
import InspectionForm, { CHANGE_TYPE_LABEL, VERDICT_LABEL } from "./InspectionForm";
import NdviThumbnails from "./NdviThumbnails";
import HighResHistory from "./HighResHistory";
import ScoreBreakdown from "./ScoreBreakdown";
import EvidenceConfidence from "./EvidenceConfidence";
import SeasonalBaselineChart from "./SeasonalBaselineChart";
import SiteTimeline from "./SiteTimeline";

// module_chg/run.py _classify_change()가 내는 값 — 화면에 원문 그대로 노출되면 안 된다.
// 단정하지 않는 표현으로 옮긴다(§3.4 종 판독 금지: 무엇이 훼손됐는지 판정하지 않는다).
const CHANGE_HINT_LABEL: Record<string, string> = {
  vegetation_decline: "식생 활력 감소",
  moisture_increase: "습윤도 증가",
  bare_ground_increase: "나지 증가 경향",
  possible_change_sar_only: "레이더 단독 변화 신호",
};

const TIER_STYLE: Record<string, { bg: string; fg: string }> = {
  "1순위": { bg: "rgba(192,57,43,0.12)", fg: "var(--tier-1)" },
  "2순위": { bg: "rgba(230,126,34,0.14)", fg: "#b8621a" },
  "3순위": { bg: "rgba(212,160,23,0.16)", fg: "#8a6508" },
  정상: { bg: "rgba(91,140,110,0.14)", fg: "var(--ok)" },
};

/** 점검 이력 한 건을 사람이 읽는 문장으로 — 이전에는 원본 JSON이 그대로 노출돼 있었다. */
function InspectionRow({ record }: { record: Record<string, unknown> }) {
  const at = typeof record.inspected_at === "string" ? record.inspected_at.slice(0, 10) : "일자 미상";
  const verdict = typeof record.verdict === "string" ? VERDICT_LABEL[record.verdict] ?? record.verdict : null;
  const category =
    typeof record.anomaly_category === "string" ? CHANGE_TYPE_LABEL[record.anomaly_category] ?? record.anomaly_category : null;
  const note = typeof record.note === "string" && record.note.trim() ? record.note.trim() : null;
  const found = record.actual_anomaly_found === true;

  return (
    <li className="flex flex-col gap-0.5 border-b border-line py-1.5 last:border-b-0">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[10px] text-ink-3">{at}</span>
        <span className="text-[12px] font-semibold" style={{ color: found ? "var(--danger)" : "var(--ok)" }}>
          {verdict ?? (found ? "변화 확인" : "변화 없음")}
        </span>
        {category && <span className="text-[11px] text-ink-2">{category}</span>}
      </div>
      {note && <p className="text-[11px] leading-snug text-ink-3">{note}</p>}
    </li>
  );
}

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

  const tierStyle = site.priority_tier ? TIER_STYLE[site.priority_tier] : null;

  return (
    <div className="scroll-thin flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div>
        <p className="text-[17px] font-bold leading-snug">{site.addr ?? site.site_id}</p>
        <p className="mt-0.5 font-mono text-[11px] text-ink-3">PNU {site.pnu}</p>
      </div>

      {/* 위험도가 아니라 점검 우선순위임을 점수 옆에 항상 명시한다 — 이 값은 환경피해
          발생확률로 calibration된 게 아니라 운영상 ranking이다(§ Module RISK 명칭 정리). */}
      <div className="card px-3 py-2.5">
        <div className="flex items-baseline gap-2.5">
          <span className="text-[32px] font-bold leading-none">{site.inspection_priority_score ?? "–"}</span>
          <span className="text-[13px] text-ink-3">/ 100</span>
          {site.priority_tier && (
            <span
              className="ml-auto rounded-full px-2.5 py-1 text-[12px] font-bold"
              style={{ background: tierStyle?.bg ?? "var(--brand-soft)", color: tierStyle?.fg ?? "var(--brand)" }}
            >
              {site.priority_tier}
            </span>
          )}
        </div>
        <p className="mt-1.5 text-[11px] leading-snug text-ink-3">
          점검 우선순위 점수입니다. 훼손 발생 확률이 아니라 한정된 점검 인력을 어디에 먼저 배정할지를
          나타내는 운영 지표입니다.
        </p>
      </div>

      <div>
        <h3 className="section-title mb-2">우선순위 산정 근거</h3>
        <ScoreBreakdown factors={evidence?.contributing_factors ?? []} weightCoverage={evidence?.weight_coverage} />

        {site.change_type_hint && site.change_type_hint !== "no_significant_change" && (
          <p
            className="mt-2 rounded px-2 py-1.5 text-[11px] leading-snug"
            style={{ background: "var(--warn-soft)", color: "#7a5310" }}
          >
            참고 신호: {CHANGE_HINT_LABEL[site.change_type_hint] ?? site.change_type_hint} — 훼손 유형을
            판정한 것이 아니라, 계절 패턴과 다른 변화가 관측되었다는 선별 신호입니다.
          </p>
        )}

        {evidence?.changed_area_ratio_source === "approximated" && (
          <p
            className="mt-1.5 rounded px-2 py-1.5 text-[11px] leading-snug"
            style={{ background: "var(--est-soft)", color: "var(--est)" }}
          >
            변화 면적은 관측 부족으로 픽셀 실측이 아닌 이상도 기반 근사치입니다.
          </p>
        )}
      </div>

      <SeasonalBaselineChart seasonal={evidence?.seasonal_anomaly ?? null} />

      <EvidenceConfidence confidence={evidence?.evidence_confidence ?? null} />

      <HighResHistory siteId={site.site_id} />

      <NdviThumbnails siteId={site.site_id} />

      <div>
        <h3 className="section-title mb-1.5">위성 관측 시계열 (NDVI)</h3>
        {timeseries ? (
          <TimeSeriesChart baseline={timeseries.baseline_scenes} current={timeseries.current_scenes} />
        ) : (
          <p className="text-[13px] text-ink-3">불러오는 중</p>
        )}
      </div>

      <SiteTimeline
        seasonal={evidence?.seasonal_anomaly ?? null}
        currentScenes={timeseries?.current_scenes ?? []}
        inspections={site.inspections}
      />

      <InspectionForm siteId={site.site_id} onSubmitted={onInspectionSubmitted} />

      {site.inspections.length > 0 && (
        <div>
          <h3 className="section-title mb-1">현장점검 이력 ({site.inspections.length}건)</h3>
          <ul className="flex flex-col">
            {site.inspections.map((record, i) => (
              <InspectionRow key={i} record={record} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
