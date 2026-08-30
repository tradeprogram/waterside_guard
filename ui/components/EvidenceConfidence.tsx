"use client";

import type { EvidenceConfidence as EvidenceConfidenceData } from "@/lib/api";

const LEVEL_STYLE: Record<string, { bg: string; fg: string }> = {
  높음: { bg: "var(--ok-soft)", fg: "var(--ok)" },
  보통: { bg: "var(--warn-soft)", fg: "var(--warn)" },
  낮음: { bg: "var(--danger-soft)", fg: "var(--danger)" },
};

/**
 * 이 점수를 얼마나 신뢰할 수 있는지를 등급과 가감 사유 목록으로 보여준다.
 *
 * 중요한 구분: 이건 **훼손 확률이 아니라 위성 관측 근거의 신뢰도**다(§module_chg/confidence.py).
 * 그래서 숫자 하나가 아니라 무엇 때문에 신뢰할 만한지/못한지를 나열한다 — 구름은 어떻게
 * 걸렀는지, SAR와 광학이 어긋나지는 않는지를 화면에서 바로 확인할 수 있도록.
 */
export default function EvidenceConfidence({ confidence }: { confidence: EvidenceConfidenceData | null }) {
  if (!confidence) return null;

  const positives = confidence.factors.filter((f) => f.effect > 0);
  const negatives = confidence.factors.filter((f) => f.effect < 0);
  const style = LEVEL_STYLE[confidence.level] ?? { bg: "var(--brand-soft)", fg: "var(--brand)" };

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <h3 className="section-title">관측 근거 신뢰도</h3>
        <span
          className="rounded-full px-2 py-0.5 text-[11px] font-bold"
          style={{ background: style.bg, color: style.fg }}
        >
          {confidence.level}
        </span>
      </div>

      <ul className="flex flex-col gap-1.5">
        {[...positives, ...negatives].map((f, i) => {
          const up = f.effect > 0;
          return (
            <li key={i} className="flex items-start gap-2 text-[11px] leading-snug">
              <span
                className="mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] font-bold"
                style={{
                  background: up ? "var(--ok-soft)" : "var(--danger-soft)",
                  color: up ? "var(--ok)" : "var(--danger)",
                }}
                aria-label={up ? "신뢰도 상승 요인" : "신뢰도 하락 요인"}
              >
                {up ? "+" : "−"}
              </span>
              <span className="flex-1">
                <span className="font-semibold text-ink-2">{f.label}</span>
                <span className="text-ink-3"> — {f.detail}</span>
              </span>
            </li>
          );
        })}
      </ul>

      <p className="mt-2 text-[11px] leading-snug text-ink-3">
        훼손 발생 확률이 아니라, 현재 확보된 위성 관측 근거를 얼마나 신뢰할 수 있는지를 나타냅니다.
      </p>
    </div>
  );
}
