"use client";

import type { EvidenceConfidence as EvidenceConfidenceData } from "@/lib/api";

const LEVEL_STYLE: Record<string, string> = {
  높음: "bg-green-100 text-green-900",
  보통: "bg-amber-100 text-amber-900",
  낮음: "bg-red-100 text-red-900",
};

/**
 * "이 점수를 얼마나 믿을 수 있는가"를 등급 배지 + ± 사유 목록으로 보여준다.
 *
 * 중요한 구분: 이건 **훼손될 확률이 아니라 위성 증거의 신뢰도**다(§module_chg/confidence.py).
 * 그래서 숫자 하나가 아니라 "무엇 때문에 믿을 만한가/못한가"를 나열한다 — 심사위원이
 * "구름은 어떻게 걸렀나", "SAR와 광학이 안 맞으면?" 같은 질문을 화면에서 바로 확인할 수 있게.
 */
export default function EvidenceConfidence({ confidence }: { confidence: EvidenceConfidenceData | null }) {
  if (!confidence) return null;

  const positives = confidence.factors.filter((f) => f.effect > 0);
  const negatives = confidence.factors.filter((f) => f.effect < 0);

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">증거 신뢰도</h3>
        <span className={`rounded px-2 py-0.5 text-xs font-semibold ${LEVEL_STYLE[confidence.level] ?? "bg-neutral-100"}`}>
          {confidence.level}
        </span>
      </div>

      <ul className="flex flex-col gap-1">
        {[...positives, ...negatives].map((f, i) => (
          <li key={i} className="flex items-start gap-1.5 text-xs">
            <span className={f.effect > 0 ? "text-green-600" : "text-red-600"}>
              {f.effect > 0 ? "▲".repeat(Math.min(f.effect, 2)) : "▼".repeat(Math.min(-f.effect, 2))}
            </span>
            <span className="flex-1">
              <span className="text-neutral-800">{f.label}</span>
              <span className="text-neutral-500"> — {f.detail}</span>
            </span>
          </li>
        ))}
      </ul>

      <p className="mt-1.5 text-xs text-neutral-400">
        훼손 확률이 아니라 &ldquo;지금 확보된 위성 증거를 얼마나 믿을 수 있는가&rdquo;입니다.
      </p>
    </div>
  );
}
