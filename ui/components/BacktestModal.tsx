"use client";

import { useEffect, useState } from "react";
import { fetchBacktest, type BacktestResult, type Envelope } from "@/lib/api";

// Module VERIFY(§ARCHITECTURE.md §5)의 GET /verify/backtest를 그대로 보여준다 — 이 화면이
// 없으면 "예측 정확도가 어디 있나"라는 질문에 답할 방법이 없었다.
const BASELINE_LABEL: Record<string, string> = { random: "무작위", proposed: "제안 모델(Module RISK)" };

function pct(v: number | null): string {
  return v != null ? `${Math.round(v * 100)}%` : "–";
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
          <div>
            <p className="text-sm font-semibold">성과 검증 (Backtest)</p>
            <p className="text-xs text-neutral-500">현장점검으로 확인된 실제 결과 대비 예측 정확도</p>
          </div>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-900">
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {loading && <p className="text-sm text-neutral-400">계산 중...</p>}

          {!loading && error && (
            <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">불러오기 실패: {error}</p>
          )}

          {!loading && data && (
            <>
              {data.labeled_site_count === 0 ? (
                <p className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  아직 현장점검 결과가 등록된 대상지가 없어 검증할 수 없습니다. 왼쪽 목록에서 점검을
                  등록하면 여기에 정확도가 나타납니다.
                </p>
              ) : (
                <>
                  <label className="mb-4 flex items-center gap-2 text-xs text-neutral-500">
                    Top-K
                    <input
                      type="number"
                      min={1}
                      value={k}
                      onChange={(e) => setK(Math.max(1, Number(e.target.value) || 1))}
                      className="w-16 rounded border border-neutral-300 px-2 py-1 text-sm"
                    />
                  </label>

                  <div className="mb-4 flex gap-4">
                    <div className="flex-1 rounded bg-neutral-50 p-3 text-center">
                      <p className="text-2xl font-bold tabular-nums">{pct(data.precision_at_k.value)}</p>
                      <p className="text-xs text-neutral-500">Precision@{data.precision_at_k.k}</p>
                    </div>
                    <div className="flex-1 rounded bg-neutral-50 p-3 text-center">
                      <p className="text-2xl font-bold tabular-nums">{pct(data.recall_at_top20pct)}</p>
                      <p className="text-xs text-neutral-500">Recall@Top20%</p>
                    </div>
                  </div>

                  <table className="mb-4 w-full text-sm">
                    <thead>
                      <tr className="border-b border-neutral-200 text-left text-xs text-neutral-500">
                        <th className="py-1">비교 기준</th>
                        <th className="py-1 text-right">Precision@{data.precision_at_k.k}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.baseline_comparison.map((b) => (
                        <tr key={b.baseline} className="border-b border-neutral-100">
                          <td className="py-1.5">{BASELINE_LABEL[b.baseline] ?? b.baseline}</td>
                          <td className="py-1.5 text-right tabular-nums">{pct(b.precision_at_k)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <p className="text-xs text-neutral-400">
                    라벨된 대상지 {data.labeled_site_count}건 중 실제 이상 확인 {data.positive_count}건 기준.
                  </p>
                </>
              )}

              {result && result.warnings.length > 0 && data.labeled_site_count > 0 && (
                <div className="mt-3 rounded bg-amber-50 px-3 py-2 text-xs text-amber-800">
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
