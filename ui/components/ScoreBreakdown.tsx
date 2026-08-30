"use client";

import type { ContributingFactor } from "@/lib/api";

// 요인별 라벨 — EvidencePanel과 공유한다(같은 문자열을 두 곳에서 관리하지 않기 위해 export).
export const FACTOR_LABEL: Record<string, string> = {
  anomaly_score_mean: "위성 이상도 (NDVI/NDMI)",
  changed_area_ratio: "변화 면적 비율",
  sar_anomaly_mean: "레이더(SAR) 변화",
  recent_rainfall_mm: "최근 14일 누적 강우",
  last_inspection_days_ago: "최종 점검 후 경과일",
  adjacent_to_water: "수변 인접 여부",
  past_anomaly_count: "과거 이상 발생 횟수",
};

// module_risk/run.py의 WEIGHTS와 반드시 같아야 한다 — 결측 요인까지 화면에 남기려면
// "원래 몇 개였는지"를 알아야 하는데, 백엔드는 확보된 요인만 내려주기 때문이다.
const ALL_WEIGHTS: Record<string, number> = {
  anomaly_score_mean: 0.3,
  changed_area_ratio: 0.15,
  last_inspection_days_ago: 0.15,
  sar_anomaly_mean: 0.1,
  recent_rainfall_mm: 0.1,
  adjacent_to_water: 0.1,
  past_anomaly_count: 0.1,
};

// 결측 사유 — 그냥 "데이터 없음"이라고 하면 언제 채워지는지 알 수 없다.
const MISSING_REASON: Record<string, string> = {
  last_inspection_days_ago: "점검 이력 축적 후 반영",
  past_anomaly_count: "점검 이력 축적 후 반영",
};

// Module RISK의 _normalize()와 반드시 같은 규칙이어야 한다 — 화면에 그리는 막대가
// 실제 점수 계산과 다른 값을 보여주면 그 자체가 신뢰를 깎는다(§9 불확실성 표기 원칙).
function normalize(factor: string, value: number | boolean | null): number | null {
  if (value === null) return null;
  if (typeof value === "boolean") return value ? 1 : 0;
  switch (factor) {
    case "anomaly_score_mean":
    case "changed_area_ratio":
    case "sar_anomaly_mean":
      return Math.max(0, Math.min(value, 1));
    case "recent_rainfall_mm":
      return Math.min(value / 50, 1);
    case "last_inspection_days_ago":
      return Math.min(value / 180, 1);
    case "past_anomaly_count":
      return Math.min(value / 3, 1);
    default:
      return null;
  }
}

// 원본 숫자만 찍으면 단위를 알 수 없다 — 화면에서는 사람이 읽는 형태로 보여준다.
function formatValue(factor: string, value: number | boolean | null): string {
  if (value === null) return "–";
  if (typeof value === "boolean") return value ? "인접" : "비인접";
  switch (factor) {
    case "changed_area_ratio":
      return `${Math.round(value * 100)}%`;
    case "recent_rainfall_mm":
      return `${Math.round(value)}mm`;
    case "last_inspection_days_ago":
      return `${Math.round(value)}일`;
    case "past_anomaly_count":
      return `${Math.round(value)}회`;
    default:
      return value.toFixed(2);
  }
}

/**
 * 우선순위 산정 근거를 숫자 목록이 아니라 막대로 보여준다 — 어떤 요인이 점수를 끌어올렸는지
 * 한눈에 들어와야 근거를 확인할 수 있다(중간점검 리서치 §Evidence Card).
 *
 * 막대 길이는 전체 7개 요인 기준 가중치 비중이고, 진한 부분이 실제 기여분이다.
 * **결측 요인도 지우지 않고 남긴다** — 화면에서 지우면 "7개 중 5개만 봤다"는 사실이
 * 사라지고, 그 순간 아래의 확보율 문구도 근거를 잃는다(§9, docs/figures F11과 동일한 표현).
 */
export default function ScoreBreakdown({
  factors,
  weightCoverage,
}: {
  factors: ContributingFactor[];
  weightCoverage?: number | null;
}) {
  if (factors.length === 0) {
    return <p className="text-[13px] text-ink-3">산정 근거 없음 (위성 관측 미확보)</p>;
  }

  const present = new Map(factors.map((f) => [f.factor, f]));
  const maxWeight = Math.max(...Object.values(ALL_WEIGHTS));

  const rows = Object.entries(ALL_WEIGHTS).map(([factor, weight]) => {
    const f = present.get(factor);
    const normalized = f ? normalize(factor, f.value) : null;
    return {
      factor,
      weight,
      missing: !f,
      normalized,
      // 막대 폭은 최대 가중치(0.30)를 100%로 잡아 요인 간 비중 차이가 보이게 한다
      trackPct: (weight / maxWeight) * 100,
      valueLabel: f ? formatValue(factor, f.value) : MISSING_REASON[factor] ?? "미확보",
      contribution: normalized === null ? 0 : normalized * weight,
    };
  });
  rows.sort((a, b) => Number(a.missing) - Number(b.missing) || b.contribution - a.contribution);

  return (
    <div className="flex flex-col gap-2">
      {rows.map((r) => (
        <div key={r.factor}>
          <div className="flex items-baseline justify-between gap-2 text-[11px]">
            <span className={r.missing ? "text-ink-3" : "text-ink-2"}>{FACTOR_LABEL[r.factor] ?? r.factor}</span>
            <span className={r.missing ? "shrink-0 italic text-ink-3" : "shrink-0 font-semibold text-ink"}>
              {r.valueLabel}
            </span>
          </div>

          <div className="mt-1 h-1.5 w-full">
            {r.missing ? (
              // 결측 — 빗금으로 "자리는 있으나 채워지지 않았음"을 표시한다
              <div
                className="h-full rounded-full"
                style={{
                  width: `${r.trackPct}%`,
                  border: "1px solid var(--line-strong)",
                  backgroundImage:
                    "repeating-linear-gradient(45deg, var(--line) 0 3px, transparent 3px 6px)",
                }}
              />
            ) : (
              <div
                className="h-full overflow-hidden rounded-full"
                style={{ width: `${r.trackPct}%`, background: "rgba(108,123,138,0.18)" }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(r.normalized ?? 0) * 100}%`,
                    background: "linear-gradient(90deg, var(--brand), var(--accent))",
                  }}
                />
              </div>
            )}
          </div>
        </div>
      ))}

      {weightCoverage != null && weightCoverage < 1 && (
        <p
          className="mt-1 rounded px-2 py-1.5 text-[11px] leading-snug"
          style={{ background: "var(--warn-soft)", color: "#7a5310" }}
        >
          전체 가중치의 {Math.round(weightCoverage * 100)}%만 확보된 상태에서 산정된 점수입니다. 빗금 표시
          요인은 점검 이력이 축적되면 반영됩니다.
        </p>
      )}
    </div>
  );
}
