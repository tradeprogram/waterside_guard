"use client";

import { useEffect, useState } from "react";
import { fetchBacktest, type BacktestResult, type Envelope } from "@/lib/api";
import CoverageCurveChart from "./CoverageCurveChart";
import AblationPanel from "./AblationPanel";

// Module VERIFY(§ARCHITECTURE.md §5)의 GET /verify/backtest를 그대로 보여준다 — 이 화면이
// 없으면 예측 성능을 어디서 확인하느냐는 질문에 답할 방법이 없었다.
const BASELINE_LABEL: Record<string, string> = {
  random: "무작위 선정",
  ndvi_only: "NDVI 이상도 단독",
  recency: "최종 점검일 기준",
  proposed: "본 시스템 (다요인 통합)",
};

function pct(v: number | null): string {
  return v != null ? `${Math.round(v * 100)}%` : "–";
}

function StatTile({ value, label }: { value: string; label: string }) {
  return (
    <div className="card flex-1 p-3 text-center">
      <p className="text-[24px] font-bold leading-none">{value}</p>
      <p className="mt-1.5 text-[11px] text-ink-3">{label}</p>
    </div>
  );
}

export default function BacktestModal({ onClose }: { onClose: () => void }) {
  const [k, setK] = useState(10);
  const [result, setResult] = useState<Envelope<BacktestResult> | null>(null);
  const [error, setError] = useState<string | null>(null);
  // result/error가 어느 k에 대한 응답인지 별도로 들고 있다가 k와 비교해 loading을 파생시킨다 —
  // effect 본문에서 setLoading(true)를 동기 호출하지 않기 위함(§NdviThumbnails.tsx와 같은 패턴).
  const [resolvedK, setResolvedK] = useState<number | null>(null);
  const loading = resolvedK !== k;

  useEffect(() => {
    let cancelled = false;
    fetchBacktest(k)
      .then((r) => {
        if (cancelled) return;
        setResult(r);
        setError(null);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setResult(null);
      })
      .finally(() => {
        if (!cancelled) setResolvedK(k);
      });
    return () => {
      cancelled = true;
    };
  }, [k]);

  const data = result?.data;

  return (
    <div
      className="no-print fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(26,29,33,0.42)", backdropFilter: "blur(3px)" }}
      onClick={onClose}
    >
      <div
        className="glass flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="예측 성능 검증"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-line px-4 py-3">
          <div>
            <p className="text-[14px] font-bold">예측 성능 검증</p>
            <p className="text-[11px] text-ink-3">현장점검으로 확인된 실제 결과 대비 예측 성능</p>
          </div>
          <button onClick={onClose} aria-label="닫기" className="text-ink-3 transition hover:text-ink">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div className="scroll-thin flex-1 overflow-y-auto p-4">
          {loading && <p className="text-[13px] text-ink-3">분석 중</p>}

          {!loading && error && (
            <p className="rounded px-3 py-2 text-[13px]" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
              조회에 실패했습니다: {error}
            </p>
          )}

          {!loading && data && (
            <>
              {data.labeled_site_count === 0 ? (
                <>
                  <p
                    className="mb-4 rounded px-3 py-2.5 text-[13px] leading-relaxed"
                    style={{ background: "var(--warn-soft)", color: "#7a5310" }}
                  >
                    <strong className="font-bold">적중률(Precision@K)은 현재 산출할 수 없습니다.</strong> 실제
                    현장점검 결과가 축적되지 않았기 때문입니다. 0.5m급 영상으로도 수변녹지의 훼손 유형(예초와
                    식생 소실의 구분 등)은 판별되지 않아, 현장 또는 드론 확인을 거쳐야 정답 자료가 만들어집니다.
                    아래는 정답 자료 없이도 제시할 수 있는 근거입니다.
                  </p>
                  <AblationPanel />
                </>
              ) : (
                <>
                  <label className="mb-4 flex items-center gap-2 text-[11px] text-ink-3">
                    상위 K필지 기준
                    <input
                      type="number"
                      min={1}
                      value={k}
                      onChange={(e) => setK(Math.max(1, Number(e.target.value) || 1))}
                      className="field w-16 px-2 py-1 text-[13px]"
                    />
                  </label>

                  <div className="mb-4 flex gap-2">
                    <StatTile value={pct(data.precision_at_k.value)} label={`적중률 (상위 ${data.precision_at_k.k}필지)`} />
                    <StatTile value={pct(data.recall_at_top20pct)} label="발견율 (상위 20% 점검 시)" />
                    <StatTile
                      value={data.lift_at_k != null ? `${data.lift_at_k}배` : "–"}
                      label="무작위 선정 대비 향상도"
                    />
                  </div>

                  <div className="mb-4">
                    <h4 className="section-title mb-1.5">점검 범위별 변화 발견율</h4>
                    <CoverageCurveChart curves={data.coverage_curves} />
                  </div>

                  <table className="mb-4 w-full text-[13px]">
                    <thead>
                      <tr className="border-b border-line text-left text-[11px] text-ink-3">
                        <th className="py-1.5 font-semibold">비교 기준</th>
                        <th className="py-1.5 text-right font-semibold">
                          적중률 (상위 {data.precision_at_k.k}필지)
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.baseline_comparison.map((b) => {
                        const isProposed = b.baseline === "proposed";
                        return (
                          <tr key={b.baseline} className="border-b border-line last:border-b-0">
                            <td className={`py-2 ${isProposed ? "font-semibold text-brand" : "text-ink-2"}`}>
                              {BASELINE_LABEL[b.baseline] ?? b.baseline}
                            </td>
                            <td className={`py-2 text-right ${isProposed ? "font-bold text-brand" : ""}`}>
                              {pct(b.precision_at_k)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  <p className="text-[11px] text-ink-3">
                    점검 결과가 등록된 {data.labeled_site_count}필지 중 실제 변화 확인 {data.positive_count}필지 기준입니다.
                  </p>
                </>
              )}

              {result && result.warnings.length > 0 && data.labeled_site_count > 0 && (
                <div
                  className="mt-3 rounded px-3 py-2 text-[11px] leading-snug"
                  style={{ background: "var(--warn-soft)", color: "#7a5310" }}
                >
                  {result.warnings.map((w, i) => (
                    <p key={i}>{w}</p>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
