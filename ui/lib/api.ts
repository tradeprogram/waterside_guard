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

export async function postInspection(payload: {
  site_id: string;
  inspector_id: string;
  inspected_at: string;
  actual_anomaly_found: boolean;
  anomaly_category?: string;
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

export type BacktestResult = {
  precision_at_k: { k: number; value: number | null };
  recall_at_top20pct: number | null;
  baseline_comparison: { baseline: string; precision_at_k: number | null }[];
  labeled_site_count: number;
  positive_count: number;
};

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

export async function askSite(siteId: string, question: string) {
  const res = await fetch(`${API_BASE}/sites/${encodeURIComponent(siteId)}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(JSON.stringify(body));
  return body as Envelope<{ site_id: string; question: string; answer: string; tools_used: string[] }>;
}
