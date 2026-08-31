"use client";

import { useEffect, useRef, useState } from "react";

// 답변을 한 번에 보여주지 않고 한 글자씩 흘려보낸다 — onDone은 렌더마다 새로 만들어지는
// 인라인 함수라 ref에 담아 최신 값만 읽는다(§MapView.tsx의 onSelectSiteRef와 같은 패턴).
// AgentChatWidget/WeeklyReportModal 등 Gemini 응답을 보여주는 곳에서 공통으로 쓴다.
export default function TypewriterText({ text, onDone }: { text: string; onDone?: () => void }) {
  // 모션을 줄이도록 설정한 사용자에겐 타이핑 효과가 방해가 된다 — 전문을 바로 보여준다.
  // 마운트 시 한 번만 읽고, 이후에는 렌더에서 text를 그대로 쓴다(effect 안에서 setState 하지 않기 위함).
  const [reduceMotion] = useState(
    () => typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
  const [shown, setShown] = useState("");
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    if (reduceMotion) {
      onDoneRef.current?.();
      return;
    }
    let i = 0;
    let timer: ReturnType<typeof setTimeout>;
    const step = () => {
      i += 2;
      setShown(text.slice(0, i));
      if (i < text.length) timer = setTimeout(step, 15);
      else onDoneRef.current?.();
    };
    timer = setTimeout(step, 15);
    return () => clearTimeout(timer);
  }, [text, reduceMotion]);

  return <>{reduceMotion ? text : shown}</>;
}
