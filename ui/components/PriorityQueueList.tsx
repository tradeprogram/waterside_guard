"use client";

import type { PriorityQueueEntry, Site } from "@/lib/api";

// addr(예: "경기도 여주시 대신면 양촌리 369-5")에서 "시군구 읍면동"만 뽑아 그룹 키로 쓴다.
// PNU 기반 주소는 항상 [시/도, 시/군/구, 읍/면/동, 리, 지번] 순서라 토큰 인덱스로 충분하고,
// 별도의 행정동 경계 shapefile 조인 없이도 그룹핑이 가능하다.
function parseDong(addr?: string): string {
  if (!addr) return "미분류";
  const tokens = addr.split(/\s+/);
  if (tokens.length < 3) return addr;
  return `${tokens[1]} ${tokens[2]}`;
}

export default function PriorityQueueList({
  entries,
  sites,
  selectedSiteId,
  onSelectSite,
}: {
  entries: PriorityQueueEntry[];
  sites: Site[];
  selectedSiteId: string | null;
  onSelectSite: (siteId: string) => void;
}) {
  const addrBySiteId = new Map(sites.map((s) => [s.site_id, s.addr]));

  // entries는 이미 순위(rank)순으로 정렬돼 있으므로, Map의 삽입 순서를 그대로 쓰면
  // "가장 급한 대상지가 속한 동"이 자연히 맨 위 그룹으로 온다 — 별도 그룹 정렬 불필요.
  const groups = new Map<string, PriorityQueueEntry[]>();
  for (const e of entries) {
    const key = parseDong(addrBySiteId.get(e.site_id));
    const list = groups.get(key);
    if (list) list.push(e);
    else groups.set(key, [e]);
  }

  return (
    <div className="flex flex-col gap-3 overflow-y-auto">
      {[...groups.entries()].map(([dong, group]) => (
        <div key={dong}>
          <div className="sticky top-0 z-10 mb-1 flex items-center justify-between bg-white px-3 py-1 text-xs font-semibold text-neutral-500">
            <span>{dong}</span>
            <span className="rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] tabular-nums">
              {group.length}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            {group.map((e) => (
              <button
                key={e.site_id}
                onClick={() => onSelectSite(e.site_id)}
                className={`flex items-center justify-between rounded px-3 py-2 text-left text-sm transition ${
                  e.site_id === selectedSiteId
                    ? "bg-neutral-800 text-white"
                    : "bg-neutral-100 hover:bg-neutral-200 text-neutral-900"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="w-6 shrink-0 text-xs font-semibold opacity-70">#{e.rank}</span>
                  <span className="truncate font-mono text-xs">{e.site_id.replace("YUBANG_", "")}</span>
                </span>
                <span className="flex items-center gap-2 shrink-0">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                      e.status === "점검완료" ? "bg-green-200 text-green-900" : "bg-amber-200 text-amber-900"
                    }`}
                  >
                    {e.status}
                  </span>
                  <span className="font-semibold tabular-nums">{e.inspection_priority_score ?? "–"}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
