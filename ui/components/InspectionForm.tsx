"use client";

import { useState } from "react";
import { postInspection } from "@/lib/api";

// 중간점검 리서치 §Field Verification Loop가 제시한 최소 taxonomy.
// 이 분류 하나가 (1) false positive 원인 분석, (2) 향후 ML label, (3) Backtest의 정답지가 된다 —
// 그래서 "이상있음/없음" 이분법이 아니라 *무엇이* 달라졌는지까지 받는다.
const VERDICTS = [
  { value: "yes", label: "변화 확인됨" },
  { value: "no", label: "변화 없음" },
  { value: "uncertain", label: "판단 보류" },
] as const;

// `natural_seasonal`·`mowing_agriculture`는 "변화는 있었지만 훼손이 아닌" 경우다 —
// 이 둘을 따로 받아야 오탐(false positive)의 원인을 구분할 수 있다.
const CHANGE_TYPES = [
  { value: "vegetation_loss", label: "식생 소실" },
  { value: "bare_ground", label: "나지 노출" },
  { value: "construction_earthwork", label: "공사·토공" },
  { value: "flooding_water_level", label: "침수·수위 변화" },
  { value: "mowing_agriculture", label: "예초·영농 활동" },
  { value: "restoration_work", label: "복원사업 시공" },
  { value: "natural_seasonal", label: "자연·계절 변화" },
  { value: "other", label: "기타" },
];

export default function InspectionForm({ siteId, onSubmitted }: { siteId: string; onSubmitted: () => void }) {
  const [verdict, setVerdict] = useState<(typeof VERDICTS)[number]["value"]>("yes");
  const [changeType, setChangeType] = useState(CHANGE_TYPES[0].value);
  const [note, setNote] = useState("");
  const [photoRef, setPhotoRef] = useState("");
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
        // Backtest의 정답 라벨 — "판단 보류"는 양성으로 세지 않는다(§Module VERIFY).
        actual_anomaly_found: verdict === "yes",
        verdict,
        anomaly_category: verdict === "yes" ? changeType : undefined,
        photo_refs: photoRef.trim() ? [photoRef.trim()] : [],
        note,
      });
      setNote("");
      setPhotoRef("");
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

      <div>
        <p className="mb-1 text-xs text-neutral-600">위성이 잡은 변화가 현장에서 확인되나요?</p>
        <div className="flex gap-1">
          {VERDICTS.map((v) => (
            <button
              key={v.value}
              onClick={() => setVerdict(v.value)}
              className={`flex-1 rounded px-2 py-1 text-xs transition ${
                verdict === v.value ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {verdict === "yes" && (
        <div>
          <p className="mb-1 text-xs text-neutral-600">무엇이 달라졌나요?</p>
          <select
            value={changeType}
            onChange={(e) => setChangeType(e.target.value)}
            className="w-full rounded border border-neutral-300 px-2 py-1 text-sm"
          >
            {CHANGE_TYPES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-neutral-400">
            &ldquo;예초·영농&rdquo;·&ldquo;자연·계절&rdquo;도 그대로 기록해주세요 — 오탐 원인을 구분하는 데 씁니다.
          </p>
        </div>
      )}

      <input
        value={photoRef}
        onChange={(e) => setPhotoRef(e.target.value)}
        placeholder="현장사진 참조(파일명·URL)"
        className="rounded border border-neutral-300 px-2 py-1 text-sm"
      />
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
