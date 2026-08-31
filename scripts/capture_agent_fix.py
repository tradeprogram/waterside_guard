"""AGENT 대화 캡처 재촬영 — 답변 전문과 근거 칩이 한 장에 들어가게.

첫 촬영본은 조회창 높이(32rem)에 답변이 다 안 들어가 문장이 잘리고, 답변 아래 붙는
근거 칩(어떤 tool을 읽고 답했는지)이 스크롤 밖으로 밀려 보이지 않았다. 근거 칩은
"답이 어디서 나왔는지 숨기지 않는다"는 이 시스템의 성격을 보여주는 부분이라 빠지면 안 된다.

캡처 시점에만 조회창 높이를 내용에 맞춰 늘린다 — 같은 화면의 같은 내용이고
스크롤을 대신 편 것뿐이다. 폭은 실제와 동일하게 둔다.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://waterside-guard.vercel.app"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screens")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1600, "height": 1400}, device_scale_factor=2, locale="ko-KR")
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(8000)

        page.locator("aside button").filter(has_text="대심리").first.click()
        page.wait_for_timeout(4000)
        page.locator('[aria-label="AGENT 조회창 열기"]').click()
        page.wait_for_timeout(1000)

        page.locator(".glass.fixed button", has_text="왜 우선순위에 올랐").click()
        print("AGENT 응답 대기(최대 3분)...")
        page.wait_for_selector("text=우선순위 근거", timeout=180_000)
        page.wait_for_timeout(9000)  # 타이핑 효과 종료까지

        # 조회창을 내용 높이에 맞춰 펼친다(캡처 전용)
        page.evaluate(
            """
            const panel = document.querySelector('.glass.fixed');
            const body = panel.querySelector('.scroll-thin');
            panel.style.height = 'auto';
            panel.style.maxHeight = 'none';
            panel.style.bottom = 'auto';
            panel.style.top = '24px';
            body.style.overflow = 'visible';
            body.style.maxHeight = 'none';
            """
        )
        page.wait_for_timeout(1200)

        OUT.mkdir(parents=True, exist_ok=True)
        target = OUT / "10_AGENT_근거조회_답변.png"
        page.locator(".glass.fixed").first.screenshot(path=str(target))
        print(f"저장: {target.name} ({target.stat().st_size / 1024:,.0f} KB)")
        browser.close()


if __name__ == "__main__":
    main()
