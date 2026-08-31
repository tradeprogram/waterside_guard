"use client";

import { useEffect, useRef, useState } from "react";
import { askSite, type AskTurn } from "@/lib/api";
import TypewriterText from "./TypewriterText";

type Message = {
  role: "user" | "agent";
  text: string;
  degraded?: boolean;
  reason?: string | null;
  tools?: string[];
  typed?: boolean;
};

/**
 * 첫 화면에 띄우는 추천 질문 — 빈 입력창만 두면 실무자가 무엇을 물어야 할지 모른다
 * (tradeprogram/policymaps agent의 QUICK_PROMPTS 패턴).
 *
 * 아무 질문이나 넣지 않고 **이 시스템이 방어해야 하는 지점**을 그대로 질문으로 만들었다.
 * 심사에서 나올 공격이 곧 실무자가 품는 의심이라, 같은 질문이 두 상황을 모두 커버한다.
 */
const QUICK_PROMPTS = [
  "이 필지가 왜 우선순위에 올랐나요?",
  "계절 변화 때문은 아닌가요?",
  "최근 강우 영향일 가능성은요?",
  "현장에서 무엇을 확인해야 하나요?",
];

// tool 이름을 실무자가 읽을 수 있는 말로 — 답변이 무엇을 근거로 나왔는지 보여준다.
const TOOL_LABEL: Record<string, string> = {
  get_risk_evidence: "우선순위 근거",
  get_timeseries_summary: "위성 관측 시계열",
  get_inspection_history: "현장점검 이력",
};

/**
 * 폴백 사유를 실무자가 조치할 수 있는 문장으로 바꾼다.
 *
 * 이전에는 어떤 실패든 "생성형 AI 미연동"이라고만 표시했는데, 실제로는 키가 멀쩡한데
 * 사용량이 소진된 경우가 있었다(2026-08-31 실측: 429 RESOURCE_EXHAUSTED). 그 상태에서
 * "미연동"이라고 하면 담당자가 설정 파일을 뒤지게 된다 — 봐야 할 곳은 결제 페이지다.
 */
function degradedReason(warnings: string[] | undefined): string {
  const w = warnings?.[0] ?? "";
  if (w.includes("GEMINI_API_KEY")) return "생성형 AI 미연동(API 키 미설정) — 표준 양식으로 작성";
  if (w.includes("RESOURCE_EXHAUSTED") || w.includes("429")) return "생성형 AI 사용량 한도 초과 — 표준 양식으로 작성";
  if (w) return "생성형 AI 호출 실패 — 표준 양식으로 작성";
  return "표준 양식으로 작성된 응답";
}

// 선택된 필지에 대한 대화 스레드. siteId가 바뀌면 부모가 key를 바꿔 이 컴포넌트를
// 통째로 리마운트시키므로, 여기서는 별도의 초기화 effect가 필요 없다.
function ChatThread({ siteId, siteLabel }: { siteId: string; siteLabel: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, loading]);

  function markTyped(index: number) {
    setMessages((prev) => prev.map((m, i) => (i === index ? { ...m, typed: true } : m)));
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || loading) return;
    setQuestion("");
    // 이번 질문 이전까지가 맥락이다 — 방금 보낸 질문은 서버가 question으로 따로 받는다.
    const history: AskTurn[] = messages.map((m) => ({ role: m.role, text: m.text }));
    setMessages((prev) => [...prev, { role: "user", text: q, typed: true }]);
    setLoading(true);
    try {
      const res = await askSite(siteId, q, history);
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: res.data.answer,
          degraded: res.status !== "ok",
          reason: res.status !== "ok" ? degradedReason(res.warnings) : null,
          tools: res.data.tools_used ?? [],
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: `응답 생성에 실패했습니다. (${e instanceof Error ? e.message : String(e)})`,
          degraded: true,
          reason: "분석 서버에 연결하지 못했습니다",
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  const canSend = !loading && question.trim().length > 0;

  return (
    <>
      <div className="shrink-0 border-b border-line px-4 py-2.5">
        <p className="text-[13px] font-bold tracking-wide" style={{ color: "var(--brand)" }}>
          AGENT
        </p>
        <p className="truncate text-[11px] text-ink-3">{siteLabel}</p>
      </div>

      <div ref={scrollRef} className="scroll-thin flex flex-1 flex-col gap-2 overflow-y-auto p-3">
        <div
          className="max-w-[88%] self-start rounded-xl rounded-tl-sm px-3 py-2 text-[13px] leading-relaxed text-ink-2"
          style={{ background: "var(--brand-soft)" }}
        >
          선택하신 필지의 우선순위 산정 근거와 위성 관측 내역을 질의하실 수 있습니다.
        </div>

        {/* 추천 질문 — 대화가 시작되면 사라진다 */}
        {messages.length === 0 && !loading && (
          <div className="flex flex-col items-start gap-1.5 pt-0.5">
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => send(p)}
                className="pill border px-2.5 py-1.5 text-left text-[12px] leading-snug transition hover:bg-black/[0.03]"
                style={{ borderColor: "var(--line-strong)", color: "var(--brand)" }}
              >
                {p}
              </button>
            ))}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex max-w-[88%] flex-col gap-1 ${m.role === "user" ? "self-end" : "self-start"}`}>
            <div
              className={`whitespace-pre-wrap rounded-xl px-3 py-2 text-[13px] leading-relaxed ${
                m.role === "user" ? "rounded-br-sm text-white" : "rounded-tl-sm"
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
            </div>

            {/* 답변이 무엇을 읽고 나왔는지 — 근거를 숨기지 않는다는 원칙을 대화에도 적용한다 */}
            {m.role === "agent" && m.typed && m.tools && m.tools.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {[...new Set(m.tools)].map((t) => (
                  <span
                    key={t}
                    className="rounded-full px-1.5 py-0.5 text-[10px]"
                    style={{ background: "var(--brand-soft)", color: "var(--brand)" }}
                  >
                    {TOOL_LABEL[t] ?? t}
                  </span>
                ))}
              </div>
            )}

            {m.role === "agent" && m.typed && m.degraded && m.reason && (
              <p className="text-[10px] leading-snug text-ink-3">{m.reason}</p>
            )}
          </div>
        ))}

        {loading && (
          <div
            className="flex items-center gap-1 self-start rounded-xl rounded-tl-sm px-3 py-2.5"
            style={{ background: "rgba(108,123,138,0.10)" }}
          >
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

      <div className="flex shrink-0 items-end gap-2 border-t border-line p-2.5">
        <textarea
          ref={inputRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          // Enter는 전송, Shift+Enter는 줄바꿈 — 여러 줄 질문도 쓸 수 있어야 한다.
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(question);
            }
          }}
          rows={1}
          placeholder="질의 내용을 입력하십시오 (Shift+Enter 줄바꿈)"
          aria-label="질의 내용"
          className="field scroll-thin max-h-24 min-w-0 flex-1 resize-none px-3 py-2 text-[13px]"
        />
        <button
          onClick={() => void send(question)}
          disabled={!canSend}
          aria-label="질의 전송"
          className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white transition disabled:opacity-35"
          style={{ background: "linear-gradient(135deg, var(--brand), var(--brand-2))" }}
        >
          <svg
            viewBox="0 0 24 24"
            className="h-[18px] w-[18px]"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
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

  // 조회창은 모달이 아니라 화면 위에 떠 있는 패널이라 포커스를 가두지는 않는다.
  // 다만 Esc로 닫히는 것은 기대되는 동작이므로 그것만 처리한다.
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      {open && (
        <div className="no-print glass fixed bottom-24 right-6 z-50 flex h-[32rem] w-[23rem] flex-col overflow-hidden">
          {siteId ? (
            <ChatThread key={siteId} siteId={siteId} siteLabel={siteLabel ?? siteId} />
          ) : (
            <>
              <div className="shrink-0 border-b border-line px-4 py-2.5">
                <p className="text-[13px] font-bold tracking-wide" style={{ color: "var(--brand)" }}>
                  AGENT
                </p>
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
        aria-label={open ? "AGENT 조회창 닫기" : "AGENT 조회창 열기"}
        aria-expanded={open}
        // 유리 재질 버튼 — 위성지도(어두운 영상) 위에 떠 있으므로 흰 유리에 브랜드 그린
        // 글자·테두리로 대비를 만든다. 불투명 원보다 화면을 덜 가리면서도 눈에 띈다.
        className="no-print glass-fab fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full text-sm font-bold transition hover:scale-105"
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
