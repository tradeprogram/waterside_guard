"use client";

import { useState } from "react";
import { askSite } from "@/lib/api";

// Module AGENT(§ARCHITECTURE.md §5)에게 자연어로 물어본다. LLM은 숫자를 만들지 않고
// tool 결과만 인용해 답한다 — GEMINI_API_KEY가 없으면 서버가 템플릿 답변으로 대체한다.
export default function AskAgent({ siteId }: { siteId: string }) {
  const [question, setQuestion] = useState("왜 이 대상지가 우선순위에 있나요?");
  const [answer, setAnswer] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [loading, setLoading] = useState(false);

  async function ask() {
    setLoading(true);
    setAnswer(null);
    try {
      const res = await askSite(siteId, question);
      setAnswer(res.data.answer);
      setDegraded(res.status !== "ok");
    } catch (e) {
      setAnswer(`Agent 호출 실패: ${e instanceof Error ? e.message : String(e)}`);
      setDegraded(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded border border-neutral-200 p-3">
      <span className="text-xs font-semibold text-neutral-500">Evidence Agent에게 물어보기</span>
      <div className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="flex-1 rounded border border-neutral-300 px-2 py-1 text-sm"
        />
        <button
          onClick={ask}
          disabled={loading}
          className="rounded bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "..." : "질문"}
        </button>
      </div>
      {answer && (
        <p className={`rounded p-2 text-sm ${degraded ? "bg-amber-50 text-amber-900" : "bg-neutral-50"}`}>
          {answer}
          {degraded && <span className="mt-1 block text-xs opacity-70">(템플릿 응답 — GEMINI_API_KEY 미설정 또는 호출 실패)</span>}
        </p>
      )}
    </div>
  );
}
