"use client";

import { useState } from "react";
import type { PriorityQueueEntry } from "@/lib/api";

const PRESETS = [5, 10, 20];

/**
 * "이번 주 N곳 점검 가능"을 설정하면 Top-N을 잘라 보여주고, 그게 전체의 몇 %인지를 알려준다.
 *
 * 중간점검 리서치가 Operational Novelty의 핵심으로 꼽은 기능 — 구현 난이도는 낮은데
 * 정체성을 "지도 프로그램"에서 "제한된 자원을 배분하는 의사결정지원 시스템"으로 바꾼다.
 * 예상 발견율은 **실제 검증 데이터가 있을 때만** 표시한다(없으면 추측 숫자를 만들지 않는다, §9).
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
    <div className="border-b border-neutral-200 bg-neutral-50 px-3 py-2">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-xs font-semibold text-neutral-600">이번 주 점검 가능</span>
        <span className="text-xs text-neutral-500">
          전체 {total}곳 중 <span className="font-semibold text-neutral-800">{coverage}%</span>
        </span>
      </div>

      <div className="flex gap-1">
        {PRESETS.map((n) => (
          <button
            key={n}
            onClick={() => {
              setCustom("");
              onBudgetChange(n);
            }}
            className={`flex-1 rounded px-2 py-1 text-xs transition ${
              budget === n && custom === "" ? "bg-neutral-900 text-white" : "bg-white text-neutral-700 hover:bg-neutral-200"
            }`}
          >
            {n}곳
          </button>
        ))}
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
          placeholder="직접"
          className="w-14 rounded border border-neutral-300 px-1.5 py-1 text-xs"
        />
      </div>

      <p className="mt-1.5 text-xs text-neutral-500">
        상위 {budget}곳 중 미점검 {uninspectedInBudget}곳
        {expectedRecall != null && (
          <>
            {" · "}과거 검증 기준 예상 발견율{" "}
            <span className="font-semibold text-neutral-800">{Math.round(expectedRecall * 100)}%</span>
          </>
        )}
      </p>
    </div>
  );
}
