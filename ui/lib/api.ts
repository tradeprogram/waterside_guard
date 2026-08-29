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
  risk_score: number | null;
  risk_tier: string | null;
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
  risk_score: number | null;
  status: "미점검" | "점검완료";
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
    risk_score: number | null;
    risk_tier: string | null;
    contributing_factors: ContributingFactor[];
    anomaly_score: number | null;
    change_type_hint: string;
  }>(`/sites/${encodeURIComponent(siteId)}/evidence`);
}

export function fetchTimeseries(siteId: string) {
  return getJson<{ site_id: string; baseline_scenes: Scene[]; current_scenes: Scene[] }>(
    `/sites/${encodeURIComponent(siteId)}/timeseries`
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
