"use client";

import type { RouteResult } from "@/lib/api";

/**
 * 배정된 필지를 인접한 것끼리 묶어 "몇 개 권역으로 나뉘는지"와 "이동거리가 얼마나 줄어드는지"를
 * 보여준다.
 *
 * 우선순위 큐만으로는 1위가 여주, 2위가 가평이면 점수 순서대로 움직이게 되는데, 그건 같은
 * 인력으로 더 적게 보는 결과가 된다. 이 패널의 핵심 숫자는 권역 개수가 아니라 **단축률**이다 —
 * 그게 없으면 묶었다는 사실만 있고 왜 나은지는 말할 수 없다(§module_o/routing.py).
 */
export default function RoutePanel({ route }: { route: RouteResult | null }) {
  if (!route || route.cluster_count === 0) return null;

  const merged = route.clusters.filter((c) => c.size > 1);
  const km = (m: number) => (m / 1000).toFixed(1);

  return (
    <div className="border-b border-line px-3 py-2.5">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="section-title">권역별 점검 동선</span>
        <span className="text-[11px] text-ink-3">
          {route.cluster_count}개 권역
          {merged.length > 0 && ` · ${merged.length}개 권역 통합`}
        </span>
      </div>

      {route.saved_pct > 0 && (
        <div className="card px-2.5 py-2">
          <div className="flex items-baseline gap-1.5 text-xs">
            <span className="text-ink-3 line-through">{km(route.naive_order_length_m)}km</span>
            <span className="text-ink-3" aria-hidden>
              →
            </span>
            <span className="text-[15px] font-bold text-ink">{km(route.clustered_order_length_m)}km</span>
            <span className="ml-auto rounded-full px-1.5 py-0.5 text-[11px] font-semibold" style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>
              {route.saved_pct}% 단축
            </span>
          </div>
          <p className="mt-1 text-[11px] text-ink-3">순위 순차 방문 대비 권역 통합 시 이동거리</p>
        </div>
      )}

      {merged.length > 0 && (
        <ul className="mt-1.5 flex flex-col gap-0.5">
          {merged.map((c) => (
            <li key={c.cluster_id} className="text-[11px] text-ink-3">
              · {c.stops[0]?.addr?.split(" ").slice(1, 3).join(" ") ?? "해당 권역"} 일원{" "}
              <strong className="font-semibold text-ink-2">{c.size}필지</strong> (반경 {km(c.radius_m)}km)
            </li>
          ))}
        </ul>
      )}

      <p className="mt-1.5 text-[11px] text-ink-3">직선거리 기준으로, 실제 주행거리와는 차이가 있습니다.</p>
    </div>
  );
}
