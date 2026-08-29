"use client";

import { useState } from "react";
import { generateWeeklyReport } from "@/lib/api";
import TypewriterText from "./TypewriterText";

function defaultWeekOf(): string {
  return new Date().toISOString().slice(0, 10);
}

// POST /reports/weekly(§module_agent/report.py)를 화면에서 직접 트리거한다 — 이전엔
// pytest로만 검증됐고 실제로 눌러서 받아볼 화면이 없었다.
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
          <p className="text-sm font-semibold">주간보고서</p>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-900">
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-3 flex gap-2">
            <input
              value={weekOf}
              onChange={(e) => setWeekOf(e.target.value)}
              placeholder="주간 기준일 (예: 2026-08-30)"
              className="flex-1 rounded border border-neutral-300 px-2 py-1.5 text-sm"
            />
            <button
              onClick={generate}
              disabled={loading || !weekOf.trim()}
              className="rounded bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {loading ? "생성 중..." : "생성"}
            </button>
          </div>

          {error && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">생성 실패: {error}</p>}

          {reportText && (
            <p className={`whitespace-pre-wrap rounded p-3 text-sm ${degraded ? "bg-amber-50 text-amber-900" : "bg-neutral-50"}`}>
              <TypewriterText text={reportText} />
              {degraded && (
                <span className="mt-2 block text-xs opacity-70">
                  (템플릿 응답 — GEMINI_API_KEY 미설정 또는 호출 실패)
                </span>
              )}
            </p>
          )}

          {!reportText && !loading && !error && (
            <p className="text-sm text-neutral-400">기준일을 확인하고 생성 버튼을 누르세요.</p>
          )}
        </div>
      </div>
    </div>
  );
}
