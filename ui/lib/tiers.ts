// 점검 우선순위 등급의 표시 규칙 — 목록·지도·상세·보고서가 같은 값을 써야 한다.
// scripts/generate_figures.py의 TIER_COLOR, globals.css의 --tier-* 와도 동일하게 유지할 것.
//
// 적색(경고)에서 기관 CI 그린까지 이어지는 2색 구성. 색상만이 아니라 **명도**도 인접 단계마다
// 0.06 이상 벌려 놓았다 — 적록색약에서 색상 구분이 무너져도 밝기로 순서가 남는다.
export const TIER_ORDER = ["1순위", "2순위", "3순위", "정상"] as const;

export const TIER_COLOR: Record<string, string> = {
  "1순위": "#c0392b",
  "2순위": "#e67e22",
  "3순위": "#a3b545",
  정상: "#009058",
};

/** 배지용 — 배경은 옅게, 글자는 진하게(옅은 배경 위 대비 확보). */
export const TIER_BADGE: Record<string, { bg: string; fg: string }> = {
  "1순위": { bg: "rgba(192,57,43,0.12)", fg: "#c0392b" },
  "2순위": { bg: "rgba(230,126,34,0.14)", fg: "#b8621a" },
  "3순위": { bg: "rgba(163,181,69,0.20)", fg: "#5f6d15" },
  정상: { bg: "rgba(0,144,88,0.13)", fg: "#00794a" },
};
