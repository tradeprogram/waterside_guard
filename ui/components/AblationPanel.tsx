"use client";

import { useEffect, useState } from "react";
import { fetchAblation, type AblationResult, type Envelope } from "@/lib/api";

/**
 * 계절 기준선의 **기여도** — 현장 라벨이 없어도 낼 수 있는 근거.
 *
 * 이건 정확도가 아니다. "훼손을 몇 % 맞혔다"는 주장은 실제 현장 결과 없이는 할 수 없고,
 * 해서도 안 된다. 여기서 보여주는 건 "계절 기준선을 켰더니 과거 정상 변동 범위 안에 있던
 * 필지들이 상위권에서 빠졌다"는 것 — 오탐 감소의 직접 증거다(§module_verify/ablation.py).
 */
export default function AblationPanel() {
  const [result, setResult] = useState<Envelope<AblationResult> | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchAblation(10)
      .then((r) => !cancelled && setResult(r))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) return null;
  if (!result) return <p className="text-sm text-neutral-400">기여도 계산 중...</p>;

  const d = result.data;
  if (d.comparable_site_count === 0) return null;

  const droppedSeasonal = d.dropped_out_of_top_k.filter((s) => s.within_normal_range);
  // 기존 방식 상위 K = (밀려난 것) + (양쪽 다 상위인 것). 후자는 정의상 정상범위 밖이므로
  // "기존 상위 K 중 정상범위 필지 수" = 밀려난 것 중 정상범위 수.
  const oldPolluted = droppedSeasonal.length;
  const newPolluted = d.top_k_within_normal_range.length;

  return (
    <div>
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        계절 기준선 기여도 (라벨 불필요)
      </h4>

      <div className="mb-3 flex gap-3">
        <div className="flex-1 rounded bg-neutral-50 p-3 text-center">
          <p className="text-2xl font-bold tabular-nums text-red-600">{oldPolluted}건</p>
          <p className="text-xs text-neutral-500">
            기존(두 기간 차분) 상위 {d.k}위 중<br />
            정상 변동 범위 내 필지
          </p>
        </div>
        <div className="flex items-center text-neutral-400">→</div>
        <div className="flex-1 rounded bg-neutral-50 p-3 text-center">
          <p className="text-2xl font-bold tabular-nums text-green-700">{newPolluted}건</p>
          <p className="text-xs text-neutral-500">
            계절 기준선 적용 후<br />
            상위 {d.k}위 중 같은 필지
          </p>
        </div>
      </div>

      {droppedSeasonal.length > 0 && (
        <table className="mb-2 w-full text-xs">
          <thead>
            <tr className="border-b border-neutral-200 text-left text-neutral-500">
              <th className="py-1">계절 변동으로 걸러진 필지</th>
              <th className="py-1 text-right">기존 순위</th>
              <th className="py-1 text-right">현재 순위</th>
              <th className="py-1 text-right">정상범위 대비</th>
            </tr>
          </thead>
          <tbody>
            {droppedSeasonal.map((s) => (
              <tr key={s.site_id} className="border-b border-neutral-100">
                <td className="py-1 font-mono text-[10px]">{s.site_id.replace(/^(HANRIVER|YUBANG)_/, "")}</td>
                <td className="py-1 text-right tabular-nums">{s.two_period_rank}위</td>
                <td className="py-1 text-right tabular-nums text-neutral-500">{s.seasonal_rank}위</td>
                <td className="py-1 text-right tabular-nums">{s.robust_z?.toFixed(1)}σ</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="text-xs text-neutral-500">
        전체 {d.comparable_site_count}건 중 {d.within_normal_range_count}건이 과거 3년 같은 계절의 정상 변동
        범위 안에 있습니다. 위 필지들은 두 기간만 비교하면 큰 변화로 보이지만, 해마다 반복되는 변동이라
        우선순위에서 밀려났습니다 — <strong>이건 정확도가 아니라 방법의 기여도</strong>입니다.
      </p>
    </div>
  );
}
