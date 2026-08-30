"use client";

import { useState } from "react";
import {
  fetchEvidence,
  fetchPriorityQueue,
  fetchRoute,
  fetchSites,
  generateWeeklyReport,
  type PriorityQueueEntry,
  type RouteResult,
  type Site,
} from "@/lib/api";
import ScoreBreakdown from "./ScoreBreakdown";
import SeasonalBaselineChart from "./SeasonalBaselineChart";
import EvidenceConfidence from "./EvidenceConfidence";
import AblationPanel from "./AblationPanel";
import { TIER_BADGE, TIER_COLOR, TIER_ORDER } from "@/lib/tiers";

type Evidence = Awaited<ReturnType<typeof fetchEvidence>>;

type ReportData = {
  weekOf: string;
  generatedAt: string;
  sites: Site[];
  queue: PriorityQueueEntry[];
  route: RouteResult | null;
  evidences: Map<string, Evidence>;
  narrative: string | null;
  narrativeDegraded: boolean;
};

// 상세 근거 카드는 상위 몇 필지까지 실을지 — 전부 실으면 보고서가 수십 장이 된다.
const DETAIL_LIMIT = 5;

function km(m: number): string {
  return (m / 1000).toFixed(1);
}

function shortAddr(addr?: string | null): string {
  if (!addr) return "주소 미상";
  return addr.split(/\s+/).slice(1).join(" ");
}

/** 등급 분포 누적 막대 — 이번 주 대상 집단이 어떻게 구성돼 있는지 한 줄로 보여준다. */
function TierDistribution({ sites }: { sites: Site[] }) {
  const counts = TIER_ORDER.map((t) => ({ tier: t, n: sites.filter((s) => s.priority_tier === t).length })).filter(
    (c) => c.n > 0
  );
  const total = counts.reduce((sum, c) => sum + c.n, 0);
  if (total === 0) return null;

  return (
    <div className="avoid-break">
      <div className="flex h-5 w-full overflow-hidden rounded" style={{ border: "1px solid var(--line)" }}>
        {counts.map((c) => (
          <div
            key={c.tier}
            style={{ width: `${(c.n / total) * 100}%`, background: TIER_COLOR[c.tier] }}
            title={`${c.tier} ${c.n}필지`}
          />
        ))}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
        {counts.map((c) => (
          <span key={c.tier} className="flex items-center gap-1.5 text-[11px] text-ink-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: TIER_COLOR[c.tier] }} />
            {c.tier} <strong className="font-semibold">{c.n}</strong>필지
            <span className="text-ink-3">({Math.round((c.n / total) * 100)}%)</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function StatTile({ value, unit, label }: { value: string | number; unit?: string; label: string }) {
  return (
    <div className="card flex-1 px-3 py-2.5">
      <p className="text-[22px] font-bold leading-none">
        {value}
        {unit && <span className="ml-0.5 text-[12px] font-semibold text-ink-3">{unit}</span>}
      </p>
      <p className="mt-1.5 text-[11px] leading-snug text-ink-3">{label}</p>
    </div>
  );
}

function SectionHeading({ no, title, note }: { no: number; title: string; note?: string }) {
  return (
    <div className="mb-2.5 flex items-baseline gap-2 border-b pb-1.5" style={{ borderColor: "var(--line)" }}>
      <span
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-[11px] font-bold text-white"
        style={{ background: "var(--brand)" }}
      >
        {no}
      </span>
      <h2 className="text-[14px] font-bold">{title}</h2>
      {note && <span className="ml-auto text-[11px] text-ink-3">{note}</span>}
    </div>
  );
}

/**
 * 주간 점검현황 보고서 — 화면 조회와 인쇄(PDF 저장)를 같은 마크업으로 처리한다.
 *
 * 각 모듈이 이미 만들어 둔 도식을 그대로 싣는다(ScoreBreakdown·SeasonalBaselineChart·
 * EvidenceConfidence·AblationPanel). 보고서용으로 그림을 새로 그리면 화면과 보고서의 숫자가
 * 갈라질 수 있는데, 그건 근거 자료로서 치명적이다.
 *
 * 인쇄는 브라우저의 "PDF로 저장"을 쓴다 — 외부 PDF 라이브러리를 넣지 않는다(§만들지 말 것).
 * 인쇄 규칙은 globals.css의 @media print에 있다.
 */
function ReportBody({ data, budget }: { data: ReportData; budget: number }) {
  const { sites, queue, route, evidences, narrative, narrativeDegraded } = data;
  const siteById = new Map(sites.map((s) => [s.site_id, s]));
  const assigned = queue.slice(0, budget);
  const uninspected = queue.filter((q) => q.status === "미점검").length;
  const urgent = sites.filter((s) => s.priority_tier === "1순위" || s.priority_tier === "2순위").length;
  const coverage = queue.length > 0 ? Math.round((budget / queue.length) * 100) : 0;
  const multiCluster = route?.clusters.filter((c) => c.size > 1) ?? [];

  return (
    <>
      {/* ── 표제부 ────────────────────────────────────────────────── */}
      <header className="mb-6 avoid-break">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[11px] font-semibold tracking-wide text-brand">수변녹지 점검 우선순위 지원시스템</p>
            <h1 className="mt-1 text-[22px] font-bold leading-tight">주간 점검현황 보고</h1>
          </div>
          <div className="text-right text-[11px] leading-relaxed text-ink-3">
            <p>
              기준일 <strong className="font-semibold text-ink-2">{data.weekOf}</strong>
            </p>
            <p>작성 {data.generatedAt}</p>
          </div>
        </div>
        <div className="mt-3 h-0.5 w-full" style={{ background: "linear-gradient(90deg, var(--brand), var(--accent))" }} />
        <p className="mt-2 text-[11px] text-ink-3">
          대상 범위: 한강수계 매수토지·수변녹지 {sites.length}필지 (위성 변화탐지 기반 우선순위 산정)
        </p>
      </header>

      {/* ── 1. 총괄 요약 ─────────────────────────────────────────── */}
      <section className="mb-6">
        <SectionHeading no={1} title="총괄 요약" />
        <div className="mb-3 flex gap-2">
          <StatTile value={queue.length} unit="필지" label="점검 대상 필지" />
          <StatTile value={urgent} unit="필지" label="1·2순위 (우선 확인 대상)" />
          <StatTile value={uninspected} unit="필지" label="미점검" />
          <StatTile value={budget} unit="필지" label={`금주 배정 (전체의 ${coverage}%)`} />
        </div>
        <TierDistribution sites={sites} />
      </section>

      {/* ── 2. 종합 의견 ─────────────────────────────────────────── */}
      {narrative && (
        <section className="mb-6 avoid-break">
          <SectionHeading no={2} title="종합 의견" />
          <div
            className="whitespace-pre-wrap rounded px-3 py-2.5 text-[12px] leading-relaxed"
            style={{ background: "rgba(108,123,138,0.07)", border: "1px solid var(--line)" }}
          >
            {narrative}
          </div>
          {narrativeDegraded && (
            <p className="mt-1.5 text-[11px] text-ink-3">
              생성형 AI 미연동 상태로, 표준 양식에 따라 작성된 의견입니다.
            </p>
          )}
        </section>
      )}

      {/* ── 3. 금주 점검 배정 필지 ──────────────────────────────── */}
      <section className="mb-6">
        <SectionHeading no={3} title="금주 점검 배정 필지" note={`상위 ${budget}필지`} />
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-left" style={{ borderBottom: "1.5px solid var(--line-strong)" }}>
              <th className="py-1.5 font-semibold">순위</th>
              <th className="py-1.5 font-semibold">소재지</th>
              <th className="py-1.5 font-semibold">등급</th>
              <th className="py-1.5 text-right font-semibold">점수</th>
              <th className="py-1.5 text-right font-semibold">정상범위 대비</th>
              <th className="py-1.5 text-center font-semibold">근거 신뢰도</th>
              <th className="py-1.5 text-center font-semibold">점검 상태</th>
            </tr>
          </thead>
          <tbody>
            {assigned.map((e) => {
              const site = siteById.get(e.site_id);
              const ev = evidences.get(e.site_id);
              const tier = site?.priority_tier ?? null;
              const badge = tier ? TIER_BADGE[tier] : null;
              const z = ev?.seasonal_anomaly?.robust_z ?? null;
              return (
                <tr key={e.site_id} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td className="py-1.5 font-semibold">{e.rank}</td>
                  <td className="py-1.5">{shortAddr(site?.addr)}</td>
                  <td className="py-1.5">
                    {tier && (
                      <span
                        className="rounded-full px-1.5 py-0.5 text-[10px] font-bold"
                        style={{ background: badge?.bg, color: badge?.fg }}
                      >
                        {tier}
                      </span>
                    )}
                  </td>
                  <td className="py-1.5 text-right font-bold">{e.inspection_priority_score ?? "–"}</td>
                  <td
                    className="py-1.5 text-right font-semibold"
                    style={{ color: z != null && Math.abs(z) > 3 ? "var(--danger)" : "var(--ink-3)" }}
                  >
                    {z != null ? `${z > 0 ? "+" : ""}${z.toFixed(1)}σ` : "–"}
                  </td>
                  <td className="py-1.5 text-center text-ink-2">{ev?.evidence_confidence?.level ?? "–"}</td>
                  <td className="py-1.5 text-center" style={{ color: e.status === "점검완료" ? "var(--ok)" : "var(--warn)" }}>
                    {e.status}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="mt-1.5 text-[11px] leading-snug text-ink-3">
          정상범위 대비는 과거 3년 동일 계절 관측의 중앙값·MAD를 기준으로 한 로버스트 z값입니다. 절댓값이
          클수록 계절 변동만으로는 설명되지 않는 관측입니다.
        </p>
      </section>

      {/* ── 4. 권역별 점검 동선 ─────────────────────────────────── */}
      {route && route.cluster_count > 0 && (
        <section className="mb-6 avoid-break">
          <SectionHeading no={4} title="권역별 점검 동선" note={`${route.cluster_count}개 권역`} />
          <div className="mb-2.5 flex gap-2">
            <StatTile value={km(route.naive_order_length_m)} unit="km" label="순위 순차 방문 시 이동거리" />
            <StatTile value={km(route.clustered_order_length_m)} unit="km" label="권역 통합 시 이동거리" />
            <StatTile value={`${route.saved_pct}`} unit="%" label={`단축 (${km(route.saved_length_m)}km 절감)`} />
          </div>
          {multiCluster.length > 0 && (
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-left" style={{ borderBottom: "1.5px solid var(--line-strong)" }}>
                  <th className="py-1.5 font-semibold">권역</th>
                  <th className="py-1.5 font-semibold">중심 지역</th>
                  <th className="py-1.5 text-right font-semibold">필지 수</th>
                  <th className="py-1.5 text-right font-semibold">반경</th>
                  <th className="py-1.5 text-right font-semibold">최우선 순위</th>
                </tr>
              </thead>
              <tbody>
                {multiCluster.map((c) => (
                  <tr key={c.cluster_id} style={{ borderBottom: "1px solid var(--line)" }}>
                    <td className="py-1.5">{c.cluster_id}</td>
                    <td className="py-1.5">
                      {c.stops[0]?.addr?.split(" ").slice(1, 3).join(" ") ?? "해당 권역"} 일원
                    </td>
                    <td className="py-1.5 text-right font-semibold">{c.size}필지</td>
                    <td className="py-1.5 text-right">{km(c.radius_m)}km</td>
                    <td className="py-1.5 text-right">{c.top_rank}위</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="mt-1.5 text-[11px] text-ink-3">
            직선거리 기준으로 산출한 값이며, 실제 주행거리와는 차이가 있습니다.
          </p>
        </section>
      )}

      {/* ── 5. 필지별 산정 근거 ─────────────────────────────────── */}
      <section className="mb-6 page-break">
        <SectionHeading no={5} title="필지별 산정 근거" note={`상위 ${Math.min(DETAIL_LIMIT, assigned.length)}필지`} />
        <div className="flex flex-col gap-4">
          {assigned.slice(0, DETAIL_LIMIT).map((e) => {
            const site = siteById.get(e.site_id);
            const ev = evidences.get(e.site_id);
            const tier = site?.priority_tier ?? null;
            const badge = tier ? TIER_BADGE[tier] : null;
            return (
              <article key={e.site_id} className="avoid-break card p-3">
                <div className="mb-2.5 flex items-baseline gap-2 border-b pb-2" style={{ borderColor: "var(--line)" }}>
                  <span className="text-[12px] font-bold text-ink-3">{e.rank}위</span>
                  <span className="text-[13px] font-bold">{site?.addr ?? e.site_id}</span>
                  {tier && (
                    <span
                      className="rounded-full px-1.5 py-0.5 text-[10px] font-bold"
                      style={{ background: badge?.bg, color: badge?.fg }}
                    >
                      {tier}
                    </span>
                  )}
                  <span className="ml-auto text-[18px] font-bold">{e.inspection_priority_score ?? "–"}</span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="section-title mb-1.5">우선순위 산정 근거</h4>
                    <ScoreBreakdown factors={ev?.contributing_factors ?? []} weightCoverage={ev?.weight_coverage} />
                  </div>
                  <div className="flex flex-col gap-3">
                    <SeasonalBaselineChart seasonal={ev?.seasonal_anomaly ?? null} />
                    <EvidenceConfidence confidence={ev?.evidence_confidence ?? null} />
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* ── 6. 방법론 및 한계 ───────────────────────────────────── */}
      <section className="page-break">
        <SectionHeading no={6} title="방법론 및 한계" />
        <div className="mb-4">
          <AblationPanel />
        </div>

        <div className="card p-3 text-[11px] leading-relaxed text-ink-2">
          <p className="mb-1.5 font-bold text-ink">본 보고서 해석 시 유의사항</p>
          <ul className="flex list-disc flex-col gap-1 pl-4">
            <li>
              점검 우선순위 점수는 훼손 발생 확률이 아니라, 한정된 점검 인력을 어디에 먼저 배정할지를
              나타내는 운영 지표입니다.
            </li>
            <li>
              위성 관측은 <strong className="font-semibold">변화의 유무</strong>를 선별할 뿐 훼손 유형(예초와
              식생 소실의 구분 등)을 판정하지 않습니다. 유형 판정은 현장 또는 드론 확인의 몫입니다.
            </li>
            <li>
              점검 이력이 축적되지 않은 요인(최종 점검 후 경과일, 과거 이상 발생 횟수)은 점수 산정에서
              제외되어 있으며, 각 필지의 근거 도표에 빗금으로 표시했습니다.
            </li>
            <li>이동거리는 직선거리 기준 산출값으로, 실제 주행거리와 차이가 있습니다.</li>
            <li>
              적중률(Precision@K)은 현장점검 결과가 축적된 이후에 산출됩니다. 본 보고서의 방법론 근거는
              정답 자료 없이 제시 가능한 계절 기준선 적용 효과입니다.
            </li>
          </ul>
        </div>

        <p className="mt-4 border-t pt-2 text-[10px] text-ink-3" style={{ borderColor: "var(--line)" }}>
          Sentinel-2 광학 / Sentinel-1 레이더 관측, JRC 수역 자료, 기상 강수 자료를 근거로 산출. 작성{" "}
          {data.generatedAt} · 수변가드 AI
        </p>
      </section>
    </>
  );
}

export default function WeeklyReportModal({ budget, onClose }: { budget: number; onClose: () => void }) {
  const [weekOf, setWeekOf] = useState(() => new Date().toISOString().slice(0, 10));
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const [sites, queueEnv, narrativeRes] = await Promise.all([
        fetchSites(),
        fetchPriorityQueue(),
        generateWeeklyReport(weekOf).catch(() => null), // 서술 의견은 부가 요소 — 실패해도 보고서는 낸다
      ]);
      const queue = queueEnv.data.priority_queue;

      // 부가 자료는 실패해도 보고서 본문이 나와야 한다(§0.5 폴백 설계).
      // 계절 기준선 기여도는 AblationPanel이 스스로 조회하므로 여기서 부르지 않는다.
      const route = await fetchRoute(budget)
        .then((r) => r.data)
        .catch(() => null);

      const targets = queue.slice(0, budget);
      const evidences = new Map<string, Evidence>();
      const settled = await Promise.allSettled(targets.map((t) => fetchEvidence(t.site_id)));
      settled.forEach((r, i) => {
        if (r.status === "fulfilled") evidences.set(targets[i].site_id, r.value);
      });

      setData({
        weekOf,
        generatedAt: new Date().toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" }),
        sites,
        queue,
        route,
        evidences,
        narrative: narrativeRes?.data.report_text ?? null,
        narrativeDegraded: narrativeRes ? narrativeRes.status !== "ok" : false,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="report-overlay fixed inset-0 z-50 overflow-y-auto scroll-thin"
      style={{ background: "rgba(26,29,33,0.42)", backdropFilter: "blur(3px)" }}
      onClick={onClose}
    >
      <div className="mx-auto w-full max-w-[210mm] px-4 py-6" onClick={(e) => e.stopPropagation()}>
        {/* 조작부 — 인쇄물에는 나오지 않는다 */}
        <div className="no-print glass mb-3 flex flex-wrap items-center gap-2 px-3 py-2.5">
          <p className="mr-auto text-[13px] font-bold">주간 점검현황 보고</p>
          <label className="flex items-center gap-1.5 text-[11px] text-ink-3">
            기준일
            <input
              value={weekOf}
              onChange={(e) => setWeekOf(e.target.value)}
              aria-label="주간 기준일"
              className="field w-32 px-2 py-1.5 text-[13px]"
            />
          </label>
          <button
            onClick={generate}
            disabled={loading || !weekOf.trim()}
            className="btn-primary px-3.5 py-1.5 text-[13px] font-semibold"
          >
            {loading ? "생성 중" : data ? "다시 생성" : "보고서 생성"}
          </button>
          <button
            onClick={() => window.print()}
            disabled={!data}
            className="btn-ghost px-3.5 py-1.5 text-[13px] font-medium disabled:opacity-40"
          >
            인쇄 · PDF 저장
          </button>
          <button onClick={onClose} aria-label="닫기" className="btn-ghost px-2.5 py-1.5 text-ink-3">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        {error && (
          <div
            className="no-print glass mb-3 px-3 py-2.5 text-[13px]"
            style={{ color: "var(--danger)" }}
            role="alert"
          >
            보고서 생성에 실패했습니다: {error}
          </div>
        )}

        <div className="report-doc glass px-8 py-7" style={{ background: "var(--surface)" }}>
          {data ? (
            <ReportBody data={data} budget={budget} />
          ) : (
            <div className="py-16 text-center">
              <p className="text-[13px] text-ink-2">
                {loading ? "보고서를 생성하고 있습니다" : "기준일 확인 후 보고서 생성 버튼을 선택해 주십시오."}
              </p>
              {!loading && (
                <p className="mx-auto mt-2 max-w-md text-[11px] leading-relaxed text-ink-3">
                  금주 배정 {budget}필지의 우선순위 산정 근거, 권역별 점검 동선, 계절 기준선 적용 효과가
                  하나의 문서로 작성됩니다. 생성 후 인쇄 기능으로 PDF 저장이 가능합니다.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
