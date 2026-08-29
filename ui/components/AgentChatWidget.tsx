"use client";

import { useEffect, useRef, useState } from "react";
import { askSite } from "@/lib/api";
import TypewriterText from "./TypewriterText";

type Message = { role: "user" | "agent"; text: string; degraded?: boolean; typed?: boolean };

// 선택된 대상지에 대한 대화 스레드. siteId가 바뀌면 부모가 key를 바꿔 이 컴포넌트를
// 통째로 리마운트시키므로, 여기서는 별도의 "site 바뀌면 초기화" effect가 필요 없다.
function ChatThread({ siteId, siteLabel }: { siteId: string; siteLabel: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages.length]);

  function markTyped(index: number) {
    setMessages((prev) => prev.map((m, i) => (i === index ? { ...m, typed: true } : m)));
  }

  async function send() {
    const q = question.trim();
    if (!q || loading) return;
    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", text: q, typed: true }]);
    setLoading(true);
    try {
      const res = await askSite(siteId, q);
      setMessages((prev) => [...prev, { role: "agent", text: res.data.answer, degraded: res.status !== "ok" }]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: `Agent 호출 실패: ${e instanceof Error ? e.message : String(e)}`, degraded: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="border-b border-neutral-200 px-4 py-3">
        <p className="text-sm font-semibold">Evidence Agent</p>
        <p className="truncate text-xs text-neutral-500">{siteLabel}</p>
      </div>

      <div ref={scrollRef} className="flex flex-1 flex-col gap-2 overflow-y-auto p-3">
        <div className="max-w-[85%] self-start rounded-lg bg-neutral-100 px-3 py-2 text-sm text-neutral-700">
          이 대상지가 왜 우선순위에 올라왔는지, 위성 관측 근거가 뭔지 물어보세요.
        </div>
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
              m.role === "user"
                ? "self-end bg-neutral-900 text-white"
                : m.degraded
                  ? "self-start bg-amber-50 text-amber-900"
                  : "self-start bg-neutral-100 text-neutral-900"
            }`}
          >
            {m.role === "agent" && !m.typed ? (
              <TypewriterText text={m.text} onDone={() => markTyped(i)} />
            ) : (
              m.text
            )}
            {m.role === "agent" && m.degraded && m.typed && (
              <span className="mt-1 block text-xs opacity-70">(템플릿 응답 — GEMINI_API_KEY 미설정 또는 호출 실패)</span>
            )}
          </div>
        ))}
        {loading && <div className="self-start rounded-lg bg-neutral-100 px-3 py-2 text-sm text-neutral-400">...</div>}
      </div>

      <div className="flex gap-2 border-t border-neutral-200 p-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="메시지를 입력하세요"
          className="flex-1 rounded border border-neutral-300 px-2 py-1.5 text-sm"
        />
        <button
          onClick={send}
          disabled={loading || !question.trim()}
          className="rounded bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          전송
        </button>
      </div>
    </>
  );
}

// 지도/리스트와 별개로 항상 떠 있는 원형 AI 버튼 — 누르면 채팅창이 열린다(§ARCHITECTURE.md
// Module AGENT). 사이드 패널에 고정으로 박혀있던 이전 형태 대신, 필요할 때만 펼치는 방식.
export default function AgentChatWidget({ siteId, siteLabel }: { siteId: string | null; siteLabel: string | null }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[32rem] w-96 flex-col rounded-xl border border-neutral-200 bg-white shadow-2xl">
          {siteId ? (
            <ChatThread key={siteId} siteId={siteId} siteLabel={siteLabel ?? siteId} />
          ) : (
            <>
              <div className="border-b border-neutral-200 px-4 py-3">
                <p className="text-sm font-semibold">Evidence Agent</p>
              </div>
              <div className="flex flex-1 items-center justify-center p-4 text-center text-sm text-neutral-400">
                먼저 지도나 목록에서 점검 대상지를 선택해주세요.
              </div>
            </>
          )}
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Evidence Agent 채팅 열기"
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-sm font-bold text-white shadow-lg transition hover:scale-105"
      >
        {open ? "✕" : "AI"}
      </button>
    </>
  );
}
