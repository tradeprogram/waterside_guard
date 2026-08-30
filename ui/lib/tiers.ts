// 점검 우선순위 등급의 표시 규칙 — 목록·지도·상세·보고서가 같은 값을 써야 한다.
// scripts/generate_figures.py의 TIER_COLOR, globals.css의 --tier-* 와도 동일하게 유지할 것.
//
// 브랜드 청록으로 물들이지 않는다: 1순위와 3순위가 비슷해 보이는 순간 판별 도구로서 실패한다.
export const TIER_ORDER = ["1순위", "2순위", "3순위", "정상"] as const;

export const TIER_COLOR: Record<string, string> = {
  "1순위": "#c0392b",
  "2순위": "#e67e22",
  "3순위": "#d4a017",
  정상: "#5b8c6e",
};

/** 배지용 — 배경은 옅게, 글자는 진하게(옅은 배경 위 대비 확보). */
export const TIER_BADGE: Record<string, { bg: string; fg: string }> = {
  "1순위": { bg: "rgba(192,57,43,0.12)", fg: "#c0392b" },
  "2순위": { bg: "rgba(230,126,34,0.14)", fg: "#b8621a" },
  "3순위": { bg: "rgba(212,160,23,0.16)", fg: "#8a6508" },
  정상: { bg: "rgba(91,140,110,0.14)", fg: "#1e7a4b" },
};
