"use client";

import { useEffect, useState } from "react";
import { fetchAblation, type AblationResult, type Envelope } from "@/lib/api";

/**
 * 계절 기준선의 **적용 효과** — 현장 라벨이 없어도 제시할 수 있는 근거.
 *
 * 이건 정확도가 아니다. 훼손을 몇 % 맞혔다는 주장은 실제 현장 결과 없이는 할 수 없고,
 * 해서도 안 된다. 여기서 보여주는 건 계절 기준선을 적용했더니 과거 정상 변동 범위 안에 있던
 * 필지들이 상위권에서 빠졌다는 것 — 오탐 감소의 직접 증거다(§module_verify/ablation.py).
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
  if (!result) return <p className="text-[13px] text-ink-3">분석 중</p>;

  const d = result.data;
  if (d.comparable_site_count === 0) return null;

  const droppedSeasonal = d.dropped_out_of_top_k.filter((s) => s.within_normal_range);
  // 기존 방식 상위 K = (밀려난 것) + (양쪽 다 상위인 것). 후자는 정의상 정상범위 밖이므로
  // 기존 상위 K 중 정상범위 필지 수 = 밀려난 것 중 정상범위 수.
  const before = droppedSeasonal.length;
  const after = d.top_k_within_normal_range.length;

  return (
    <div>
      <h4 className="section-title mb-2">계절 기준선 적용 효과</h4>

      <div className="mb-3 flex items-stretch gap-2">
        <div className="card flex-1 p-3 text-center">
          <p className="text-[26px] font-bold leading-none" style={{ color: "var(--danger)" }}>
            {before}
            <span className="text-[13px] font-semibold">건</span>
          </p>
          <p className="mt-1.5 text-[11px] leading-snug text-ink-3">
            기존 방식(두 기간 차분)
            <br />
            상위 {d.k}위 중 정상범위 필지
          </p>
        </div>
        <div className="flex items-center text-ink-3" aria-hidden>
          →
        </div>
        <div className="card flex-1 p-3 text-center">
          <p className="text-[26px] font-bold leading-none" style={{ color: "var(--ok)" }}>
            {after}
            <span className="text-[13px] font-semibold">건</span>
          </p>
          <p className="mt-1.5 text-[11px] leading-snug text-ink-3">
            계절 기준선 적용 후
            <br />
            상위 {d.k}위 중 정상범위 필지
          </p>
        </div>
      </div>

      {droppedSeasonal.length > 0 && (
        <div className="mb-2 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-line text-left text-ink-3">
                <th className="py-1.5 font-semibold">계절 변동으로 제외된 필지</th>
                <th className="py-1.5 text-right font-semibold">기존 순위</th>
                <th className="py-1.5 text-right font-semibold">적용 후</th>
                <th className="py-1.5 text-right font-semibold">정상범위 대비</th>
              </tr>
            </thead>
            <tbody>
              {droppedSeasonal.map((s) => (
                <tr key={s.site_id} className="border-b border-line last:border-b-0">
                  <td className="py-1.5 font-mono text-[10px] text-ink-2">
                    {s.site_id.replace(/^(HANRIVER|YUBANG)_/, "")}
                  </td>
                  <td className="py-1.5 text-right font-semibold">{s.two_period_rank}위</td>
                  <td className="py-1.5 text-right text-ink-3">{s.seasonal_rank}위</td>
                  <td className="py-1.5 text-right">{s.robust_z?.toFixed(1)}σ</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[11px] leading-snug text-ink-3">
        전체 {d.comparable_site_count}필지 중 {d.within_normal_range_count}필지가 과거 3년 동일 계절의 정상 변동
        범위 이내입니다. 위 필지들은 두 기간만 비교하면 큰 변화로 보이나 해마다 반복되는 변동이므로
        우선순위에서 제외되었습니다.{" "}
        <strong className="font-semibold text-ink-2">본 수치는 예측 정확도가 아니라 방법론의 개선 효과입니다.</strong>
      </p>
    </div>
  );
}
