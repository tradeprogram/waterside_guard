"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { fetchPriorityQueue, fetchSites, type PriorityQueueEntry, type Site } from "@/lib/api";
import PriorityQueueList from "@/components/PriorityQueueList";
import EvidencePanel from "@/components/EvidencePanel";

// MapLibre는 window에 의존하므로 SSR을 끈다
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default function Home() {
  const [sites, setSites] = useState<Site[]>([]);
  const [queue, setQueue] = useState<PriorityQueueEntry[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [sitesData, queueEnvelope] = await Promise.all([fetchSites(), fetchPriorityQueue()]);
      setSites(sitesData);
      setQueue(queueEnvelope.data.priority_queue);
      setError(null);
    } catch (e) {
      setError(
        `API 서버(${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001"})에 연결할 수 없습니다. ` +
          `'python -m uvicorn api_server:app --port 8001'로 백엔드를 먼저 띄워주세요. (${e instanceof Error ? e.message : e})`
      );
    }
  }, []);

  useEffect(() => {
    // reload()의 setState는 await 뒤(마이크로태스크)에서 일어나 실제로는 동기 호출이 아니지만,
    // react-hooks/set-state-in-effect 규칙이 useCallback으로 감싼 함수까지 보수적으로 잡아낸다 —
    // 최초 마운트 시 1회 데이터를 불러오는 표준 fetch-on-mount 패턴이라 의도적으로 예외 처리한다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, [reload]);

  const selectedSite = sites.find((s) => s.site_id === selectedSiteId) ?? null;

  return (
    <div className="flex h-screen w-screen flex-col bg-white text-neutral-900">
      <header className="flex items-center justify-between border-b border-neutral-200 px-4 py-2">
        <div>
          <h1 className="text-lg font-bold">수변가드 AI</h1>
          <p className="text-xs text-neutral-500">유방동 실증 AOI — 오늘 먼저 가봐야 할 곳</p>
        </div>
        <span className="text-xs text-neutral-400">
          Top-{queue.length} · 미점검 {queue.filter((q) => q.status === "미점검").length}
        </span>
      </header>

      {error && <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}

      <div className="flex min-h-0 flex-1">
        <aside className="w-72 shrink-0 overflow-y-auto border-r border-neutral-200 p-2">
          <PriorityQueueList entries={queue} selectedSiteId={selectedSiteId} onSelectSite={setSelectedSiteId} />
        </aside>

        <main className="min-w-0 flex-1">
          <MapView sites={sites} selectedSiteId={selectedSiteId} onSelectSite={setSelectedSiteId} />
        </main>

        {selectedSite && (
          <aside className="w-96 shrink-0 border-l border-neutral-200">
            <EvidencePanel site={selectedSite} onInspectionSubmitted={reload} />
          </aside>
        )}
      </div>
    </div>
  );
}
