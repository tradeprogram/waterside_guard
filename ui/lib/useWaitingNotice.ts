"use client";

import { useEffect, useState } from "react";

export type WaitingStage = { after: number; text: string };

/**
 * 오래 걸리는 요청에서 경과 시간에 따라 안내 문구를 바꿔 준다.
 *
 * **왜 스피너만으로는 부족한가**: AGENT 응답은 정상일 때도 30~40초 걸린다(실측). 여기에
 * 무료 티어 백엔드가 절전에서 깨어나는 40~60초가 겹치면 최대 1분 반이다. 그 동안 점 세 개만
 * 튀고 있으면 사용자는 고장인지 기다리는 중인지 구분할 수 없다.
 *
 * 단계별로 말을 바꾸면 같은 대기 시간이 "멈춘 화면"이 아니라 "진행 중인 작업"으로 읽힌다.
 * 각 호출부가 자기 상황에 맞는 문구를 준다 — 점검 등록은 원래 즉시 끝나므로 8초만 넘어도
 * 이상한 상황이지만, AGENT는 40초까지는 정상이기 때문이다.
 */
export function useWaitingNotice(active: boolean, stages: WaitingStage[]): string | null {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!active) return;
    const started = Date.now();
    // setState는 타이머 콜백과 cleanup에서만 일어난다 — effect 본문에서 동기로 부르면
    // 렌더 중 상태 변경이 되어 react-hooks/set-state-in-effect에 걸린다.
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    // 다음 요청이 이전 요청의 경과 시간을 물려받아 곧바로 마지막 단계 문구를 띄우지 않도록
    // 끝날 때 초기화한다.
    return () => {
      clearInterval(id);
      setElapsed(0);
    };
  }, [active]);

  if (!active) return null;
  let notice: string | null = null;
  for (const s of stages) {
    if (elapsed >= s.after) notice = s.text;
  }
  return notice;
}
