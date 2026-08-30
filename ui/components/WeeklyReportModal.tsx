"use client";

import { useState } from "react";
import { generateWeeklyReport } from "@/lib/api";
import TypewriterText from "./TypewriterText";

function defaultWeekOf(): string {
  return new Date().toISOString().slice(0, 10);
}

// POST /reports/weekly(§module_agent/report.py)를 화면에서 직접 실행한다 — 이전엔
// pytest로만 검증됐고 실제로 받아볼 화면이 없었다.
export default function WeeklyReportModal({ onClose }: { onClose: () => void }) {
  const [weekOf, setWeekOf] = useState(defaultWeekOf());
  const [reportText, setReportText] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    setReportText(null);
    try {
      const res = await generateWeeklyReport(weekOf);
      setReportText(res.data.report_text);
      setDegraded(res.status !== "ok");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(26,29,33,0.42)", backdropFilter: "blur(3px)" }}
      onClick={onClose}
    >
      <div
        className="glass flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="주간 점검현황 보고"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-line px-4 py-3">
          <p className="text-[14px] font-bold">주간 점검현황 보고</p>
          <button onClick={onClose} aria-label="닫기" className="text-ink-3 transition hover:text-ink">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div className="scroll-thin flex-1 overflow-y-auto p-4">
          <div className="mb-3 flex gap-2">
            <input
              value={weekOf}
              onChange={(e) => setWeekOf(e.target.value)}
              placeholder="주간 기준일 (예: 2026-08-30)"
              aria-label="주간 기준일"
              className="field flex-1 px-2.5 py-2 text-[13px]"
            />
            <button
              onClick={generate}
              disabled={loading || !weekOf.trim()}
              className="btn-primary shrink-0 px-4 py-2 text-[13px] font-semibold"
            >
              {loading ? "생성 중" : "보고서 생성"}
            </button>
          </div>

          {error && (
            <p className="rounded px-3 py-2 text-[13px]" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
              보고서 생성에 실패했습니다: {error}
            </p>
          )}

          {reportText && (
            <div
              className="whitespace-pre-wrap rounded p-3 text-[13px] leading-relaxed"
              style={
                degraded
                  ? { background: "var(--warn-soft)", color: "var(--ink)" }
                  : { background: "rgba(108,123,138,0.08)", color: "var(--ink)" }
              }
            >
              <TypewriterText text={reportText} />
              {degraded && (
                <span className="mt-2 block text-[11px] opacity-70">
                  생성형 AI 미연동 상태로, 표준 양식에 따라 작성된 보고서입니다.
                </span>
              )}
            </div>
          )}

          {!reportText && !loading && !error && (
            <p className="text-[13px] text-ink-3">기준일 확인 후 보고서 생성 버튼을 선택해 주십시오.</p>
          )}
        </div>
      </div>
    </div>
  );
}
