"use client";

import type { ContributingFactor } from "@/lib/api";

// 요인별 라벨 — EvidencePanel과 공유한다(같은 문자열을 두 곳에서 관리하지 않기 위해 export).
export const FACTOR_LABEL: Record<string, string> = {
  anomaly_score_mean: "위성 이상도 (NDVI/NDMI)",
  changed_area_ratio: "변화 면적 비율",
  sar_anomaly_mean: "레이더(SAR) 변화",
  recent_rainfall_mm: "최근 14일 누적 강우",
  last_inspection_days_ago: "마지막 점검 후 경과일",
  adjacent_to_water: "수변 인접 여부",
  past_anomaly_count: "과거 이상 발생 횟수",
};

// Module RISK의 _normalize()와 반드시 같은 규칙이어야 한다 — 화면에 그리는 막대가
// 실제 점수 계산과 다른 값을 보여주면 그 자체가 신뢰를 깎는다(§9 불확실성 표기 원칙).
// 백엔드가 정규화된 값을 안 내려주므로 여기서 같은 식을 다시 적용한다.
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

function formatValue(value: number | boolean | null): string {
  if (value === null) return "–";
  if (typeof value === "boolean") return value ? "예" : "아니오";
  return String(value);
}

/**
 * "왜 이 순위인가"를 숫자 목록이 아니라 막대로 보여준다 — 어떤 요인이 점수를 끌어올렸는지
 * 한눈에 들어와야 심사위원이 근거를 확인할 수 있다(중간점검 리서치 §Evidence Card).
 *
 * 각 막대의 길이는 그 요인이 최종 점수에 실제로 기여한 몫(정규화값 × 가중치 / 전체 가중치)이고,
 * 회색 배경은 그 요인이 가질 수 있었던 최대 몫이다 — "이 요인이 만점이었다면 얼마나 더
 * 올라갔을까"가 같이 보인다.
 */
export default function ScoreBreakdown({
  factors,
  weightCoverage,
}: {
  factors: ContributingFactor[];
  weightCoverage?: number | null;
}) {
  if (factors.length === 0) {
    return <p className="text-sm text-neutral-400">근거 요인 없음(위성 관측 미확보)</p>;
  }

  const totalWeight = factors.reduce((sum, f) => sum + f.weight, 0);
  const rows = factors
    .map((f) => {
      const normalized = normalize(f.factor, f.value);
      const maxShare = totalWeight > 0 ? f.weight / totalWeight : 0;
      return { ...f, normalized, contribution: normalized === null ? 0 : normalized * maxShare, maxShare };
    })
    .sort((a, b) => b.contribution - a.contribution);

  return (
    <div className="flex flex-col gap-2">
      {rows.map((r) => (
        <div key={r.factor}>
          <div className="flex items-baseline justify-between text-xs">
            <span className="text-neutral-700">{FACTOR_LABEL[r.factor] ?? r.factor}</span>
            <span className="font-mono text-neutral-500">{formatValue(r.value)}</span>
          </div>
          {/* 배경 막대 = 이 요인의 최대 가능 기여분, 앞 막대 = 실제 기여분 */}
          <div className="mt-0.5 h-2 w-full overflow-hidden rounded-full bg-neutral-100">
            <div className="h-full rounded-full bg-neutral-200" style={{ width: `${r.maxShare * 100}%` }}>
              <div
                className="h-full rounded-full bg-neutral-800"
                style={{ width: r.maxShare > 0 ? `${(r.contribution / r.maxShare) * 100}%` : "0%" }}
              />
            </div>
          </div>
        </div>
      ))}

      {weightCoverage != null && weightCoverage < 1 && (
        <p className="mt-1 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">
          전체 근거의 {Math.round(weightCoverage * 100)}%만 확보된 상태에서 산정된 점수입니다 — 나머지
          요인(복원경과일·최근점검일·과거이상이력)은 KECI 내부 자료가 있어야 채워집니다.
        </p>
      )}
    </div>
  );
}
