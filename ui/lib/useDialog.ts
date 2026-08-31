"use client";

import { useEffect, useRef } from "react";

/** 대화상자 안에서 Tab으로 순회 가능한 요소들. */
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * 모달 공통 키보드 동작 — Esc로 닫기, 열 때 포커스 진입, 닫을 때 원래 자리로 복귀,
 * 열려 있는 동안 Tab이 뒤 화면으로 새지 않도록 순환.
 *
 * 이게 없으면 키보드·스크린리더 사용자는 모달이 열린 사실을 모른 채 Tab을 눌러 뒤에 있는
 * 지도·목록으로 이동하게 된다(2026-08-31 실측: 모달을 열어도 activeElement가 body였다).
 *
 * 반환한 ref는 대화상자 컨테이너에 걸고 `tabIndex={-1}`을 함께 준다 — 그래야 컨테이너
 * 자체가 최초 포커스를 받을 수 있다.
 */
export function useDialog<T extends HTMLElement>(onClose: () => void) {
  const ref = useRef<T>(null);
  // onClose는 부모에서 매 렌더 새로 만들어지는 경우가 많다. 최신 값만 참조하고
  // effect 자체는 마운트/언마운트에만 돌게 해서 포커스가 매 렌더 튀지 않게 한다.
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  });

  useEffect(() => {
    const node = ref.current;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    node?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeRef.current();
        return;
      }
      if (e.key !== "Tab" || !node) return;

      const items = [...node.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
        (el) => el.offsetParent !== null // 화면에 안 보이는 요소는 건너뛴다
      );
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;

      if (e.shiftKey && (active === first || active === node)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, []);

  return ref;
}
