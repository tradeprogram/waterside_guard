"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  fetchBacktest,
  fetchPriorityQueue,
  fetchRoute,
  fetchSites,
  type PriorityQueueEntry,
  type RouteResult,
  type Site,
} from "@/lib/api";
import PriorityQueueList from "@/components/PriorityQueueList";
import EvidencePanel from "@/components/EvidencePanel";
import AgentChatWidget from "@/components/AgentChatWidget";
import BacktestModal from "@/components/BacktestModal";
import WeeklyReportModal from "@/components/WeeklyReportModal";
import InspectionBudgetPanel from "@/components/InspectionBudgetPanel";
import RoutePanel from "@/components/RoutePanel";

// MapLibre는 window에 의존하므로 SSR을 끈다
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default function Home() {
  const [sites, setSites] = useState<Site[]>([]);
  const [queue, setQueue] = useState<PriorityQueueEntry[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [backtestOpen, setBacktestOpen] = useState(false);
  const [weeklyReportOpen, setWeeklyReportOpen] = useState(false);
  // "이번 주 몇 곳 갈 수 있는가" — 이 값이 Top-N 경계를 정한다(§InspectionBudgetPanel).
  const [budget, setBudget] = useState(10);
  // 예산 범위에서 실제로 몇 %를 잡을 수 있는지는 **검증 데이터가 있을 때만** 표시한다.
  const [expectedRecall, setExpectedRecall] = useState<number | null>(null);
  // 예산 안의 대상지를 묶어 만든 출장 계획 — 예산이 바뀌면 다시 계산된다.
  const [route, setRoute] = useState<RouteResult | null>(null);

  const reload = useCallback(async () => {
    try {
      const [sitesData, queueEnvelope] = await Promise.all([fetchSites(), fetchPriorityQueue()]);
      setSites(sitesData);
      setQueue(queueEnvelope.data.priority_queue);
      setError(null);

      // 커버리지 곡선에서 현재 예산 비율에 해당하는 recall을 읽어온다 — 라벨이 없으면
      // 곡선 자체가 비어 있어 null이 되고, 화면에도 아무 숫자를 만들어 쓰지 않는다.
      try {
        const backtest = await fetchBacktest(10);
        const curve = backtest.data.coverage_curves?.proposed ?? [];
        const total = queueEnvelope.data.priority_queue.length;
        if (curve.length > 0 && total > 0) {
          const targetPct = (budget / total) * 100;
          const nearest = curve.reduce((best, p) =>
            Math.abs(p.coverage_pct - targetPct) < Math.abs(best.coverage_pct - targetPct) ? p : best
          );
          setExpectedRecall(nearest.recall);
        } else {
          setExpectedRecall(null);
        }
      } catch {
        setExpectedRecall(null); // 검증 정보는 부가 기능 — 실패해도 큐는 그대로 보여준다
      }

      try {
        setRoute((await fetchRoute(budget)).data);
      } catch {
        setRoute(null); // 출장 묶음도 부가 기능 — 실패해도 우선순위 큐는 살아 있어야 한다
      }
    } catch (e) {
      setError(
        `API 서버(${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001"})에 연결할 수 없습니다. ` +
          `'python -m uvicorn api_server:app --port 8001'로 백엔드를 먼저 띄워주세요. (${e instanceof Error ? e.message : e})`
      );
    }
  }, [budget]);

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
          <p className="text-xs text-neutral-500">한강유역 6개 시/군/구 — 오늘 먼저 가봐야 할 곳</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-neutral-400">
            Top-{queue.length} · 미점검 {queue.filter((q) => q.status === "미점검").length}
          </span>
          <button
            onClick={() => setBacktestOpen(true)}
            className="rounded border border-neutral-300 px-2 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-100"
          >
            성과 검증
          </button>
          <button
            onClick={() => setWeeklyReportOpen(true)}
            className="rounded border border-neutral-300 px-2 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-100"
          >
            주간보고서
          </button>
        </div>
      </header>

      {error && <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-72 shrink-0 flex-col border-r border-neutral-200">
          <InspectionBudgetPanel
            entries={queue}
            budget={budget}
            onBudgetChange={setBudget}
            expectedRecall={expectedRecall}
          />
          <RoutePanel route={route} />
          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            <PriorityQueueList
              entries={queue}
              sites={sites}
              selectedSiteId={selectedSiteId}
              onSelectSite={setSelectedSiteId}
              budget={budget}
            />
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <MapView
            sites={sites}
            selectedSiteId={selectedSiteId}
            onSelectSite={setSelectedSiteId}
            budgetSiteIds={queue.slice(0, budget).map((q) => q.site_id)}
            routeStops={route?.clusters.flatMap((c) => c.stops) ?? []}
          />
        </main>

        {selectedSite && (
          <aside className="w-96 shrink-0 border-l border-neutral-200">
            <EvidencePanel site={selectedSite} onInspectionSubmitted={reload} />
          </aside>
        )}
      </div>

      <AgentChatWidget siteId={selectedSiteId} siteLabel={selectedSite?.addr ?? selectedSite?.site_id ?? null} />
      {backtestOpen && <BacktestModal onClose={() => setBacktestOpen(false)} />}
      {weeklyReportOpen && <WeeklyReportModal onClose={() => setWeeklyReportOpen(false)} />}
    </div>
  );
}
