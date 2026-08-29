"use client";

import { useEffect, useRef, useState } from "react";

// 답변을 한 번에 보여주지 않고 한 글자씩 흘려보낸다 — onDone은 렌더마다 새로 만들어지는
// 인라인 함수라 ref에 담아 최신 값만 읽는다(§MapView.tsx의 onSelectSiteRef와 같은 패턴).
// AgentChatWidget/WeeklyReportModal 등 Gemini 응답을 보여주는 곳에서 공통으로 쓴다.
export default function TypewriterText({ text, onDone }: { text: string; onDone?: () => void }) {
  const [shown, setShown] = useState("");
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
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
  }, [text]);

  return <>{shown}</>;
}
