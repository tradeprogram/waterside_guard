"use client";

import { useState } from "react";
import { postInspection } from "@/lib/api";

// 중간점검 리서치 §Field Verification Loop가 제시한 최소 taxonomy.
// 이 분류 하나가 (1) 오탐 원인 분석, (2) 향후 학습 라벨, (3) 성능검증의 정답지가 된다 —
// 그래서 이상 유무 이분법이 아니라 *무엇이* 달라졌는지까지 받는다.
export const VERDICTS = [
  { value: "yes", label: "변화 확인" },
  { value: "no", label: "변화 없음" },
  { value: "uncertain", label: "판단 보류" },
] as const;

// `natural_seasonal`·`mowing_agriculture`는 변화는 있었으나 훼손이 아닌 경우다 —
// 이 둘을 따로 받아야 오탐의 원인을 구분할 수 있다.
export const CHANGE_TYPES = [
  { value: "vegetation_loss", label: "식생 소실" },
  { value: "bare_ground", label: "나지 노출" },
  { value: "construction_earthwork", label: "공사·토공" },
  { value: "flooding_water_level", label: "침수·수위 변화" },
  { value: "mowing_agriculture", label: "예초·영농 활동" },
  { value: "restoration_work", label: "복원사업 시공" },
  { value: "natural_seasonal", label: "자연·계절 변화" },
  { value: "other", label: "기타" },
];

export const CHANGE_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  CHANGE_TYPES.map((c) => [c.value, c.label])
);
export const VERDICT_LABEL: Record<string, string> = Object.fromEntries(VERDICTS.map((v) => [v.value, v.label]));

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
        // 성능검증의 정답 라벨 — 판단 보류는 양성으로 세지 않는다(§Module VERIFY).
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
    <div className="card flex flex-col gap-2.5 p-3">
      <span className="section-title">현장점검 결과 등록</span>

      <div>
        <p className="mb-1.5 text-[11px] text-ink-2">위성 탐지 변화의 현장 확인 결과</p>
        <div className="flex gap-1">
          {VERDICTS.map((v) => {
            const active = verdict === v.value;
            return (
              <button
                key={v.value}
                onClick={() => setVerdict(v.value)}
                aria-pressed={active}
                className={`pill flex-1 px-2 py-1.5 text-xs font-medium ${
                  active ? "pill-active" : "bg-black/[0.05] text-ink-2 hover:bg-black/[0.09]"
                }`}
              >
                {v.label}
              </button>
            );
          })}
        </div>
      </div>

      {verdict === "yes" && (
        <div>
          <p className="mb-1.5 text-[11px] text-ink-2">변화 유형</p>
          <select
            value={changeType}
            onChange={(e) => setChangeType(e.target.value)}
            aria-label="변화 유형"
            className="field w-full px-2 py-1.5 text-[13px]"
          >
            {CHANGE_TYPES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <p className="mt-1.5 text-[11px] text-ink-3">
            예초·영농 활동과 자연·계절 변화도 그대로 기록해 주십시오. 오탐 원인을 구분하는 근거가 됩니다.
          </p>
        </div>
      )}

      <input
        value={photoRef}
        onChange={(e) => setPhotoRef(e.target.value)}
        placeholder="현장사진 파일명 또는 URL"
        aria-label="현장사진 파일명 또는 URL"
        className="field px-2 py-1.5 text-[13px]"
      />
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="현장 특이사항"
        aria-label="현장 특이사항"
        className="field px-2 py-1.5 text-[13px]"
        rows={2}
      />
      <button onClick={submit} disabled={submitting} className="btn-primary px-3 py-2 text-[13px] font-semibold">
        {submitting ? "등록 중" : "점검결과 등록"}
      </button>
      {error && (
        <p className="rounded px-2 py-1.5 text-[11px]" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
          등록에 실패했습니다: {error}
        </p>
      )}
    </div>
  );
}
