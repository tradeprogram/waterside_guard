"use client";

import { useState } from "react";
import type { PriorityQueueEntry } from "@/lib/api";

const PRESETS = [5, 10, 20];

/**
 * 주간 점검 가능 필지 수를 설정하면 상위 N필지를 배정하고, 그것이 전체의 몇 %인지 알려준다.
 *
 * 중간점검 리서치가 Operational Novelty의 핵심으로 꼽은 기능 — 구현 난이도는 낮은데
 * 정체성을 단순 지도 조회 화면에서 제한된 점검 인력을 배분하는 의사결정 지원 도구로 바꾼다.
 * 예상 확인율은 **실제 검증 데이터가 있을 때만** 표시한다(없으면 추측 숫자를 만들지 않는다, §9).
 */
export default function InspectionBudgetPanel({
  entries,
  budget,
  onBudgetChange,
  expectedRecall,
}: {
  entries: PriorityQueueEntry[];
  budget: number;
  onBudgetChange: (n: number) => void;
  expectedRecall?: number | null;
}) {
  const [custom, setCustom] = useState("");

  const total = entries.length;
  const coverage = total > 0 ? Math.round((budget / total) * 100) : 0;
  const uninspectedInBudget = entries.slice(0, budget).filter((e) => e.status === "미점검").length;

  return (
    <div className="border-b border-line px-3 py-2.5" style={{ background: "var(--brand-soft)" }}>
      <div className="mb-2 flex items-baseline justify-between">
        <span className="section-title">주간 점검 배정</span>
        <span className="text-[11px] text-ink-3">
          전체 {total}필지 중 <strong className="font-semibold text-brand">{coverage}%</strong>
        </span>
      </div>

      <div className="flex gap-1">
        {PRESETS.map((n) => {
          const active = budget === n && custom === "";
          return (
            <button
              key={n}
              onClick={() => {
                setCustom("");
                onBudgetChange(n);
              }}
              aria-pressed={active}
              className={`pill flex-1 px-2 py-1.5 text-xs font-medium ${
                active ? "pill-active" : "bg-white/70 text-ink-2 hover:bg-white"
              }`}
            >
              {n}필지
            </button>
          );
        })}
        <input
          type="number"
          min={1}
          max={total}
          value={custom}
          onChange={(e) => {
            setCustom(e.target.value);
            const n = Number(e.target.value);
            if (n >= 1) onBudgetChange(Math.min(n, total));
          }}
          placeholder="직접입력"
          aria-label="점검 가능 필지 수 직접 입력"
          className="field w-[4.5rem] px-2 py-1 text-xs"
        />
      </div>

      <p className="mt-2 text-[11px] text-ink-2">
        배정 {budget}필지 중 미점검 <strong className="font-semibold">{uninspectedInBudget}</strong>필지
        {expectedRecall != null && (
          <>
            {" · "}검증 이력 기준 예상 확인율{" "}
            <strong className="font-semibold text-brand">{Math.round(expectedRecall * 100)}%</strong>
          </>
        )}
      </p>
    </div>
  );
}
