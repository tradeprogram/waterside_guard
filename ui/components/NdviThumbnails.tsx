"use client";

import { useEffect, useState } from "react";
import { fetchThumbnails, type Thumbnail } from "@/lib/api";

// 지도가 왜 "위성지도"인지에 대한 답 — 위험도 점수만 보여주지 않고, 실제로
// 위성이 관측한 NDVI(식생지수) 컬러 이미지를 Before/After로 보여준다.
// Earth Engine 호출이라 첫 로드가 1~3초 걸릴 수 있다(§ module_obs/thumbnail.py).
function ThumbnailImg({ label, thumb }: { label: string; thumb: Thumbnail | null }) {
  return (
    <div className="flex flex-1 flex-col gap-1">
      <span className="text-xs text-neutral-500">
        {label}
        {thumb ? ` (${thumb.acquisition_date})` : ""}
      </span>
      {thumb ? (
        // eslint-disable-next-line @next/next/no-img-element -- 외부(Earth Engine) 동적 이미지, next/image 최적화 불필요
        <img src={thumb.url} alt={`${label} NDVI`} className="aspect-square w-full rounded object-cover" />
      ) : (
        <div className="flex aspect-square w-full items-center justify-center rounded bg-neutral-100 text-xs text-neutral-400">
          관측 없음
        </div>
      )}
    </div>
  );
}

export default function NdviThumbnails({ siteId }: { siteId: string }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchThumbnails>> | null>(null);
  // data가 다른 site의 이전 응답일 수 있으니(비동기 응답이 늦게 온 경우), site_id로 신선도를
  // 판단한다 — 별도의 loading state를 두지 않고 파생시켜서 effect 본문의 동기 setState를 없앤다.
  const loading = data?.site_id !== siteId;

  useEffect(() => {
    let cancelled = false;
    fetchThumbnails(siteId)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData({ site_id: siteId, baseline: null, current: null, warnings: ["로드 실패"] }));
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  return (
    <div>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        위성 NDVI 컬러 이미지 (적색=낮음 · 녹색=높음)
      </h3>
      {loading ? (
        <p className="text-sm text-neutral-400">Earth Engine에서 이미지 생성 중...</p>
      ) : (
        <div className="flex gap-2">
          <ThumbnailImg label="기준기간(2024)" thumb={data?.baseline ?? null} />
          <ThumbnailImg label="현재기간(2026)" thumb={data?.current ?? null} />
        </div>
      )}
    </div>
  );
}
