// api_server.py(ARCHITECTURE.md §7)를 그대로 감싼 얇은 클라이언트.
// 계산은 전부 백엔드가 한다 — 여기서는 fetch만 한다.

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";

export type ContributingFactor = {
  factor: string;
  value: number | boolean | null;
  weight: number;
};

export type Site = {
  site_id: string;
  stage: string;
  inspection_priority_score: number | null;
  priority_tier: string | null;
  contributing_factors: ContributingFactor[];
  pnu?: string;
  jibun?: string;
  addr?: string;
  anomaly_score?: number | null;
  change_type_hint?: string;
  geometry_geojson?: GeoJSON.Geometry;
  inspections: Record<string, unknown>[];
};

export type PriorityQueueEntry = {
  rank: number;
  site_id: string;
  inspection_priority_score: number | null;
  status: "미점검" | "점검완료";
};

// module_chg/run.py compute_seasonal_anomaly()의 반환 구조 — 같은 계절 과거 N년 대비 위치.
export type SeasonalAnomaly = {
  robust_z: number;
  seasonal_anomaly_score: number;
  historical_median: number;
  historical_mad: number;
  years_used: number;
  current_ndvi: number;
  yearly?: { year: number; ndvi_median: number | null; scene_count: number }[];
};

// module_chg/confidence.py의 반환 구조 — level은 등급, factors는 그 등급이 나온 ± 사유 목록.
export type EvidenceConfidence = {
  level: "높음" | "보통" | "낮음";
  score: number;
  factors: { label: string; effect: number; detail: string }[];
};

export type Envelope<T> = {
  status: "ok" | "degraded" | "error";
  fallback_tier: number;
  data: T;
  warnings: string[];
};

export type Scene = {
  source: string;
  acquisition_date: string;
  cloud_cover_pct: number;
  indices: { ndvi_mean: number | null; ndmi_mean: number | null };
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export function fetchSites() {
  return getJson<Site[]>("/sites");
}

export function fetchPriorityQueue() {
  return getJson<Envelope<{ week_of: string; priority_queue: PriorityQueueEntry[]; queue_size: number; generated_at: string }>>(
    "/priority-queue"
  );
}

export function fetchEvidence(siteId: string) {
  return getJson<{
    site_id: string;
    inspection_priority_score: number | null;
    priority_tier: string | null;
    contributing_factors: ContributingFactor[];
    anomaly_score: number | null;
    change_type_hint: string;
    // 점수의 신뢰도 맥락 — weight_coverage는 "전체 가중치 중 몇 %의 근거로 계산됐는지",
    // changed_area_ratio_source는 변화면적이 픽셀 실측인지 근사치인지(§9 불확실성 표기).
    weight_coverage: number | null;
    changed_area_ratio_source: "pixel_diff" | "approximated" | null;
    evidence_confidence: EvidenceConfidence | null;
    anomaly_method: "season_matched" | "two_period_diff" | "sar_only" | null;
    seasonal_anomaly: SeasonalAnomaly | null;
  }>(`/sites/${encodeURIComponent(siteId)}/evidence`);
}

export function fetchTimeseries(siteId: string) {
  return getJson<{ site_id: string; baseline_scenes: Scene[]; current_scenes: Scene[] }>(
    `/sites/${encodeURIComponent(siteId)}/timeseries`
  );
}

// [좌상단, 우상단, 우하단, 좌하단] — MapLibre image source가 요구하는 순서(api_server.py와 동일)
type Corner = [number, number];
export type Thumbnail = { url: string; image_coordinates: [Corner, Corner, Corner, Corner]; acquisition_date: string };

export function fetchThumbnails(siteId: string) {
  return getJson<{ site_id: string; baseline: Thumbnail | null; current: Thumbnail | null; warnings: string[] }>(
    `/sites/${encodeURIComponent(siteId)}/thumbnails`
  );
}

// api_server.py의 GET /sites/{id}/highres — Esri Wayback 시기별 고해상도 타일.
// 서버가 이미지를 합성하지 않고 타일 URL만 주므로 프론트가 grid×grid로 배치한다.
export type HighResHistoryData = {
  site_id: string;
  grid: number;
  bounds: [number, number, number, number]; // [서, 북, 동, 남]
  geometry_geojson: GeoJSON.Geometry;
  epochs: { date: string; tiles: string[][] }[];
};

export function fetchHighRes(siteId: string) {
  return getJson<HighResHistoryData>(`/sites/${encodeURIComponent(siteId)}/highres`);
}

export async function postInspection(payload: {
  site_id: string;
  inspector_id: string;
  inspected_at: string;
  actual_anomaly_found: boolean;
  // "판단 보류"를 actual_anomaly_found=false와 구분해 기록한다 — 오탐 분석에서 둘은 다른 사례다.
  verdict?: "yes" | "no" | "uncertain";
  anomaly_category?: string;
  photo_refs?: string[];
  note?: string;
}) {
  const res = await fetch(`${API_BASE}/inspections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(JSON.stringify(body));
  return body as Envelope<{ site_id: string; inspection_id: string; status: string }>;
}

export type CoveragePoint = {
  coverage_pct: number;
  inspected_count: number;
  found_count: number;
  recall: number;
};

export type BacktestResult = {
  precision_at_k: { k: number; value: number | null };
  recall_at_top20pct: number | null;
  lift_at_k: number | null;
  baseline_comparison: { baseline: string; precision_at_k: number | null }[];
  coverage_curves: Record<string, CoveragePoint[]>;
  labeled_site_count: number;
  positive_count: number;
};

// module_o/routing.py — 예산 안의 대상지를 묶어 방문 순서를 정한 결과.
export type RouteStop = {
  site_id: string;
  rank: number;
  addr: string | null;
  inspection_priority_score: number | null;
  status: string;
  lonlat: [number, number] | null;
};

export type RouteCluster = {
  cluster_id: number;
  size: number;
  site_ids: string[];
  route_length_m: number;
  radius_m: number;
  top_rank: number;
  stops: RouteStop[];
};

export type RouteResult = {
  clusters: RouteCluster[];
  cluster_count: number;
  naive_order_length_m: number;
  clustered_order_length_m: number;
  saved_length_m: number;
  saved_pct: number;
  distance_basis: string;
};

export function fetchRoute(budget: number) {
  return getJson<Envelope<RouteResult>>(`/priority-queue/route?budget=${budget}`);
}

// module_verify/ablation.py — 라벨 없이 낼 수 있는 "방법 기여도" 근거.
export type AblationEntry = {
  site_id: string;
  two_period_rank: number;
  seasonal_rank: number;
  robust_z: number | null;
  within_normal_range: boolean;
};

export type AblationResult = {
  comparable_site_count: number;
  k: number;
  dropped_out_of_top_k: AblationEntry[];
  entered_top_k: AblationEntry[];
  within_normal_range_count: number;
  top_k_within_normal_range: string[];
};

export function fetchAblation(k: number) {
  return getJson<Envelope<AblationResult>>(`/verify/ablation?k=${k}`);
}

export function fetchBacktest(k: number) {
  return getJson<Envelope<BacktestResult>>(`/verify/backtest?period=current&k=${k}`);
}

export async function generateWeeklyReport(weekOf: string) {
  const res = await fetch(`${API_BASE}/reports/weekly`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ week_of: weekOf }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(JSON.stringify(body));
  return body as Envelope<{ week_of: string; report_text: string; tools_used: string[] }>;
}

export type AskTurn = { role: "user" | "agent"; text: string };

export async function askSite(siteId: string, question: string, history: AskTurn[] = []) {
  const res = await fetch(`${API_BASE}/sites/${encodeURIComponent(siteId)}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // 직전 대화를 함께 보낸다 — 없으면 "그럼 왜 그렇죠?" 같은 후속 질문이 맥락을 잃는다.
    body: JSON.stringify({ question, history }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(JSON.stringify(body));
  return body as Envelope<{ site_id: string; question: string; answer: string; tools_used: string[] }>;
}
