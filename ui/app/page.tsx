"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
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
  // 좌측 목록 접기 — 1024px에서 필지를 선택하면 지도에 296px밖에 안 남아 지도가
  // 기능을 잃는다(2026-08-31 실측). 접으면 그 폭이 지도로 넘어간다.
  const [queueOpen, setQueueOpen] = useState(true);
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
        `분석 서버(${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001"})에 연결할 수 없습니다. ` +
          `'python -m uvicorn api_server:app --port 8001' 실행 후 다시 시도해 주십시오. (${e instanceof Error ? e.message : e})`
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

  const uninspected = queue.filter((q) => q.status === "미점검").length;

  return (
    <>
      {/* 인쇄할 때 이 껍데기만 숨기면 보고서만 남는다 — 그래서 모달·AI 버튼을 형제로 둔다
          (조상이 display:none이면 후손도 함께 사라지므로 자식으로 두면 인쇄가 백지가 된다). */}
      <div className="app-shell flex h-screen w-screen flex-col bg-bg text-ink">
        <header className="glass-bar z-30 flex shrink-0 items-center justify-between px-5 py-2.5">
          <div className="flex items-center gap-3">
            {/* 기관 CI — 원본이 투명 배경(RGBA)이라 별도 배경판을 두지 않는다.
                375x226 비율을 유지하려고 높이만 고정하고 폭은 auto로 둔다. */}
            <Image
              src="/keci_logo.png"
              alt="한국환경보전원"
              width={375}
              height={226}
              priority
              className="h-10 w-auto"
            />
            {/* 기관 CI와 시스템명 사이 구분선 — 둘이 한 덩어리로 읽히지 않게 한다 */}
            <span className="h-8 w-px shrink-0 bg-line" aria-hidden />
            <div>
              <h1 className="text-[14px] font-bold leading-tight tracking-tight">수변생태벨트 점검 우선순위 지원시스템</h1>
              <p className="text-[11px] leading-tight text-ink-3">한강수계 매수토지 · 위성 변화탐지 기반 현장점검 순서 산정</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="mr-1 hidden items-center gap-3 text-[11px] text-ink-3 sm:flex">
              <span>
                점검대상 <strong className="font-semibold text-ink-2">{queue.length}</strong>필지
              </span>
              <span className="h-3 w-px bg-line" aria-hidden />
              <span>
                미점검 <strong className="font-semibold text-warn">{uninspected}</strong>필지
              </span>
            </div>
            <button
              onClick={() => setQueueOpen((v) => !v)}
              aria-pressed={!queueOpen}
              aria-label={queueOpen ? "점검 목록 접기" : "점검 목록 펼치기"}
              title={queueOpen ? "점검 목록 접기" : "점검 목록 펼치기"}
              className="btn-ghost flex h-8 w-8 items-center justify-center"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="4" width="18" height="16" rx="2" />
                <path d="M9 4v16" />
                {!queueOpen && <path d="M13 9l3 3-3 3" />}
              </svg>
            </button>
            <button onClick={() => setBacktestOpen(true)} className="btn-ghost px-3 py-1.5 text-xs font-medium">
              예측 성능 검증
            </button>
            <button onClick={() => setWeeklyReportOpen(true)} className="btn-ghost px-3 py-1.5 text-xs font-medium">
              주간 점검현황
            </button>
          </div>
        </header>

        {error && (
          <div
            className="shrink-0 px-5 py-2 text-sm"
            style={{ background: "var(--danger-soft)", color: "var(--danger)", borderBottom: "1px solid var(--line)" }}
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="flex min-h-0 flex-1 gap-2 p-2">
          {queueOpen && (
          <aside className="glass flex w-[19rem] shrink-0 flex-col overflow-hidden">
            <InspectionBudgetPanel
              entries={queue}
              budget={budget}
              onBudgetChange={setBudget}
              expectedRecall={expectedRecall}
            />
            <RoutePanel route={route} />
            <div className="scroll-thin min-h-0 flex-1 overflow-y-auto p-2">
              <PriorityQueueList
                entries={queue}
                sites={sites}
                selectedSiteId={selectedSiteId}
                onSelectSite={setSelectedSiteId}
                budget={budget}
              />
            </div>
          </aside>
          )}

          <main className="glass min-w-0 flex-1 overflow-hidden">
            <MapView
              sites={sites}
              selectedSiteId={selectedSiteId}
              onSelectSite={setSelectedSiteId}
              budgetSiteIds={queue.slice(0, budget).map((q) => q.site_id)}
              routeStops={route?.clusters.flatMap((c) => c.stops) ?? []}
            />
          </main>

          {selectedSite && (
            <aside className="glass w-[25rem] shrink-0 overflow-hidden">
              <EvidencePanel site={selectedSite} onInspectionSubmitted={reload} />
            </aside>
          )}
        </div>
      </div>

      <AgentChatWidget siteId={selectedSiteId} siteLabel={selectedSite?.addr ?? selectedSite?.site_id ?? null} />
      {backtestOpen && <BacktestModal onClose={() => setBacktestOpen(false)} />}
      {weeklyReportOpen && <WeeklyReportModal budget={budget} onClose={() => setWeeklyReportOpen(false)} />}
    </>
  );
}
