"use client";

import type { PriorityQueueEntry } from "@/lib/api";

export default function PriorityQueueList({
  entries,
  selectedSiteId,
  onSelectSite,
}: {
  entries: PriorityQueueEntry[];
  selectedSiteId: string | null;
  onSelectSite: (siteId: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1 overflow-y-auto">
      {entries.map((e) => (
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
            <span className="font-semibold tabular-nums">{e.risk_score ?? "–"}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
