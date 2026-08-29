"use client";

import { useState } from "react";
import { postInspection } from "@/lib/api";

const CATEGORIES = ["식생교란", "침수흔적", "불법이용", "이상없음", "기타"];

export default function InspectionForm({ siteId, onSubmitted }: { siteId: string; onSubmitted: () => void }) {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await postInspection({
        site_id: siteId,
        inspector_id: "demo_user",
        inspected_at: new Date().toISOString(),
        actual_anomaly_found: category !== "이상없음",
        anomaly_category: category,
        note,
      });
      setNote("");
      onSubmitted();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded border border-neutral-200 p-3">
      <span className="text-xs font-semibold text-neutral-500">현장점검 결과 등록</span>
      <select
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        className="rounded border border-neutral-300 px-2 py-1 text-sm"
      >
        {CATEGORIES.map((c) => (
          <option key={c}>{c}</option>
        ))}
      </select>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="현장 메모"
        className="rounded border border-neutral-300 px-2 py-1 text-sm"
        rows={2}
      />
      <button
        onClick={submit}
        disabled={submitting}
        className="rounded bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
      >
        {submitting ? "등록 중..." : "점검 완료로 등록"}
      </button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
