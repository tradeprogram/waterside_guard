"use client";

import { useEffect, useRef, useState } from "react";
import { askSite } from "@/lib/api";
import TypewriterText from "./TypewriterText";

type Message = { role: "user" | "agent"; text: string; degraded?: boolean; typed?: boolean };

// 선택된 필지에 대한 대화 스레드. siteId가 바뀌면 부모가 key를 바꿔 이 컴포넌트를
// 통째로 리마운트시키므로, 여기서는 별도의 초기화 effect가 필요 없다.
function ChatThread({ siteId, siteLabel }: { siteId: string; siteLabel: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
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
        { role: "agent", text: `응답 생성에 실패했습니다. (${e instanceof Error ? e.message : String(e)})`, degraded: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const canSend = !loading && question.trim().length > 0;

  return (
    <>
      <div className="shrink-0 border-b border-line px-4 py-2.5">
        <p className="text-[13px] font-bold">AI 근거 조회</p>
        <p className="truncate text-[11px] text-ink-3">{siteLabel}</p>
      </div>

      <div ref={scrollRef} className="scroll-thin flex flex-1 flex-col gap-2 overflow-y-auto p-3">
        <div className="max-w-[88%] self-start rounded-xl rounded-tl-sm px-3 py-2 text-[13px] leading-relaxed text-ink-2" style={{ background: "var(--brand-soft)" }}>
          선택하신 필지의 우선순위 산정 근거와 위성 관측 내역을 질의하실 수 있습니다.
        </div>

        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[88%] whitespace-pre-wrap rounded-xl px-3 py-2 text-[13px] leading-relaxed ${
              m.role === "user" ? "self-end rounded-br-sm text-white" : "self-start rounded-tl-sm"
            }`}
            style={
              m.role === "user"
                ? { background: "linear-gradient(135deg, var(--brand), var(--brand-2))" }
                : m.degraded
                  ? { background: "var(--warn-soft)", color: "var(--ink)" }
                  : { background: "rgba(108,123,138,0.10)", color: "var(--ink)" }
            }
          >
            {m.role === "agent" && !m.typed ? <TypewriterText text={m.text} onDone={() => markTyped(i)} /> : m.text}
            {m.role === "agent" && m.degraded && m.typed && (
              <span className="mt-1.5 block text-[11px] opacity-70">
                생성형 AI 미연동 상태로, 표준 양식에 따라 작성된 응답입니다.
              </span>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-1 self-start rounded-xl rounded-tl-sm px-3 py-2.5" style={{ background: "rgba(108,123,138,0.10)" }}>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 animate-bounce rounded-full"
                style={{ background: "var(--ink-3)", animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2 border-t border-line p-2.5">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="질의 내용을 입력하십시오"
          aria-label="질의 내용"
          className="field min-w-0 flex-1 px-3 py-2 text-[13px]"
        />
        <button
          onClick={send}
          disabled={!canSend}
          aria-label="질의 전송"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white transition disabled:opacity-35"
          style={{ background: "linear-gradient(135deg, var(--brand), var(--brand-2))" }}
        >
          <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 19V5" />
            <path d="M5 12l7-7 7 7" />
          </svg>
        </button>
      </div>
    </>
  );
}

// 지도·목록과 별개로 항상 떠 있는 원형 AI 버튼 — 누르면 조회창이 열린다(§ARCHITECTURE.md
// Module AGENT). 사이드 패널에 고정돼 있던 이전 형태 대신, 필요할 때만 펼치는 방식.
export default function AgentChatWidget({ siteId, siteLabel }: { siteId: string | null; siteLabel: string | null }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      {open && (
        <div className="glass fixed bottom-24 right-6 z-50 flex h-[32rem] w-[23rem] flex-col overflow-hidden">
          {siteId ? (
            <ChatThread key={siteId} siteId={siteId} siteLabel={siteLabel ?? siteId} />
          ) : (
            <>
              <div className="shrink-0 border-b border-line px-4 py-2.5">
                <p className="text-[13px] font-bold">AI 근거 조회</p>
              </div>
              <div className="flex flex-1 items-center justify-center p-6 text-center text-[13px] leading-relaxed text-ink-3">
                지도 또는 목록에서 점검 필지를 먼저 선택해 주십시오.
              </div>
            </>
          )}
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "AI 근거 조회 닫기" : "AI 근거 조회 열기"}
        aria-expanded={open}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full text-sm font-bold text-white transition hover:scale-105"
        style={{
          background: "linear-gradient(135deg, var(--brand), var(--brand-2))",
          boxShadow: "0 8px 24px rgba(39,112,134,0.38)",
        }}
      >
        {open ? (
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        ) : (
          "AI"
        )}
      </button>
    </>
  );
}
