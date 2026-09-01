"""1순위 필지를 선택해 근거 패널을 띄운 채, 지도는 전체 필지가 보이게 줌아웃해 찍는다.

필지를 고르면 지도가 그 필지로 확대되면서(MapView fitBounds maxZoom 18) 나머지 59필지가
화면 밖으로 나간다. 제안서에는 "전체 분포 + 선택한 1순위의 근거"가 한 장에 있어야 하므로
선택 상태는 유지한 채 지도만 되돌린다.
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
        ctx = browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=2, locale="ko-KR")
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(9000)

        page.locator("aside button").filter(has_text="대심리").first.click()
        page.wait_for_timeout(6000)  # 근거 조회 + NDVI 오버레이

        # 줌아웃은 키보드로 한다 — 휠은 한 번에 움직이는 양이 일정하지 않아
        # 몇 번 굴려야 할지 맞출 수 없다(9번엔 부족하고 40번이면 동아시아까지 나갔다).
        # MapLibre 키보드 핸들러의 '-'는 정확히 1줌 단계씩 내린다.
        page.locator("canvas").first.focus()
        for _ in range(8):  # 선택 시 z18 -> 전체 60필지가 들어오는 z10
            page.keyboard.press("Minus")
            page.wait_for_timeout(500)
        page.wait_for_timeout(7000)  # 위성 타일 재로드

        OUT.mkdir(parents=True, exist_ok=True)
        target = OUT / "11_전체필지_1순위선택.png"
        page.screenshot(path=str(target))
        print(f"저장: {target.name} ({target.stat().st_size / 1024:,.0f} KB)")
        browser.close()


if __name__ == "__main__":
    main()
