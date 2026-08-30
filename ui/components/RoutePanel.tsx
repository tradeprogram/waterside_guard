"use client";

import type { RouteResult } from "@/lib/api";

/**
 * 예산 안의 대상지를 가까운 것끼리 묶어 "몇 번 나가면 되는지"와 "얼마나 덜 움직이는지"를 보여준다.
 *
 * 우선순위 큐만으로는 1위가 여주, 2위가 가평이면 점수 순서대로 움직이게 되는데, 그건 같은
 * 인력으로 더 적게 보는 결과가 된다. 이 패널의 핵심 숫자는 군집 개수가 아니라 **절감률**이다 —
 * 그게 없으면 "묶었다"는 사실만 있고 왜 좋은지는 말할 수 없다(§module_o/routing.py).
 */
export default function RoutePanel({ route }: { route: RouteResult | null }) {
  if (!route || route.cluster_count === 0) return null;

  const multi = route.clusters.filter((c) => c.size > 1);
  const km = (m: number) => (m / 1000).toFixed(1);

  return (
    <div className="border-b border-neutral-200 px-3 py-2">
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-xs font-semibold text-neutral-600">출장 묶음</span>
        <span className="text-xs text-neutral-500">
          {route.cluster_count}회 이동
          {multi.length > 0 && ` · ${multi.length}곳은 묶음 방문`}
        </span>
      </div>

      {route.saved_pct > 0 && (
        <p className="text-xs text-neutral-600">
          순위대로 {km(route.naive_order_length_m)}km →{" "}
          <span className="font-semibold text-neutral-900">{km(route.clustered_order_length_m)}km</span>{" "}
          <span className="text-green-700">({route.saved_pct}% 절감)</span>
        </p>
      )}

      {multi.length > 0 && (
        <ul className="mt-1 flex flex-col gap-0.5">
          {multi.map((c) => (
            <li key={c.cluster_id} className="text-xs text-neutral-500">
              · {c.stops[0]?.addr?.split(" ").slice(1, 3).join(" ") ?? "묶음"} 일대{" "}
              <strong className="text-neutral-700">{c.size}곳</strong> (반경 {km(c.radius_m)}km)
            </li>
          ))}
        </ul>
      )}

      <p className="mt-1 text-[11px] text-neutral-400">
        직선거리 기준입니다 — 실제 도로 주행거리와 다를 수 있습니다.
      </p>
    </div>
  );
}
