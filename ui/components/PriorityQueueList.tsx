"use client";

import type { PriorityQueueEntry, Site } from "@/lib/api";
import { TIER_COLOR } from "@/lib/tiers";

// addr(예: "경기도 여주시 대신면 양촌리 369-5")에서 "시군구 읍면동"만 뽑아 그룹 키로 쓴다.
// PNU 기반 주소는 항상 [시/도, 시/군/구, 읍/면/동, 리, 지번] 순서라 토큰 인덱스로 충분하고,
// 별도의 행정동 경계 shapefile 조인 없이도 그룹핑이 가능하다.
function parseDong(addr?: string): string {
  if (!addr) return "주소 미상";
  const tokens = addr.split(/\s+/);
  if (tokens.length < 3) return addr;
  return `${tokens[1]} ${tokens[2]}`;
}

// 그룹 제목이 "시군구 읍면동"이므로 항목에는 그 뒤(리·지번)만 남긴다 — 같은 정보를
// 두 번 읽게 하지 않는다. 주소가 없으면 내부 식별자로 폴백한다.
function parseJibun(addr: string | undefined, siteId: string): string {
  if (!addr) return siteId.replace(/^(HANRIVER|YUBANG)_/, "");
  const rest = addr.split(/\s+/).slice(3).join(" ");
  return rest || addr;
}

export default function PriorityQueueList({
  entries,
  sites,
  selectedSiteId,
  onSelectSite,
  budget,
}: {
  entries: PriorityQueueEntry[];
  sites: Site[];
  selectedSiteId: string | null;
  onSelectSite: (siteId: string) => void;
  /** 주간 배정 필지 수 — 이 순위를 넘어가는 항목은 흐리게 표시한다(§InspectionBudgetPanel). */
  budget?: number;
}) {
  const siteById = new Map(sites.map((s) => [s.site_id, s]));

  // entries는 이미 순위(rank)순으로 정렬돼 있으므로, Map의 삽입 순서를 그대로 쓰면
  // 최우선 필지가 속한 읍면동이 자연히 맨 위 그룹으로 온다 — 별도 그룹 정렬 불필요.
  const groups = new Map<string, PriorityQueueEntry[]>();
  for (const e of entries) {
    const key = parseDong(siteById.get(e.site_id)?.addr);
    const list = groups.get(key);
    if (list) list.push(e);
    else groups.set(key, [e]);
  }

  return (
    <div className="flex flex-col gap-3">
      {[...groups.entries()].map(([dong, group]) => (
        <div key={dong}>
          <div
            className="sticky top-0 z-10 mb-1 flex items-center justify-between rounded px-2 py-1.5 text-[11px] font-bold"
            style={{ background: "var(--surface-glass-strong)", backdropFilter: "var(--glass-blur)", color: "var(--ink-2)" }}
          >
            <span>{dong}</span>
            <span className="rounded-full bg-black/[0.06] px-1.5 py-0.5 text-[10px] font-medium text-ink-3">
              {group.length}필지
            </span>
          </div>

          <div className="flex flex-col gap-1">
            {group.map((e) => {
              const site = siteById.get(e.site_id);
              const selected = e.site_id === selectedSiteId;
              const tier = site?.priority_tier ?? null;
              const outOfBudget = budget != null && e.rank > budget;

              return (
                <button
                  key={e.site_id}
                  onClick={() => onSelectSite(e.site_id)}
                  aria-current={selected ? "true" : undefined}
                  className={`group flex items-center gap-2 rounded-md py-1.5 pl-1 pr-2 text-left transition ${
                    selected ? "text-white shadow-sm" : "text-ink hover:bg-black/[0.045]"
                  } ${outOfBudget ? "opacity-45" : ""}`}
                  style={selected ? { background: "linear-gradient(135deg, var(--brand), var(--brand-2))" } : undefined}
                >
                  {/* 등급 표시 점 — 선택 상태에서도 등급이 사라지지 않도록 항상 왼쪽에 둔다.
                      선택 시 배경이 청록이라 흰 링을 둘러 점이 묻히지 않게 한다. */}
                  <span className="flex w-4 shrink-0 justify-center" aria-hidden>
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{
                        background: tier ? TIER_COLOR[tier] ?? "var(--ink-3)" : "var(--line-strong)",
                        boxShadow: selected ? "0 0 0 1.5px rgba(255,255,255,0.9)" : "none",
                      }}
                    />
                  </span>
                  <span
                    className={`w-6 shrink-0 text-right text-[11px] font-semibold ${selected ? "text-white/75" : "text-ink-3"}`}
                  >
                    {e.rank}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] leading-tight">
                      {parseJibun(site?.addr, e.site_id)}
                    </span>
                    <span className={`text-[10px] leading-tight ${selected ? "text-white/70" : "text-ink-3"}`}>
                      {tier ?? "등급 미산정"}
                      {e.status === "점검완료" && " · 점검완료"}
                    </span>
                  </span>
                  <span className={`shrink-0 text-[15px] font-bold ${selected ? "text-white" : "text-ink"}`}>
                    {e.inspection_priority_score ?? "–"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
