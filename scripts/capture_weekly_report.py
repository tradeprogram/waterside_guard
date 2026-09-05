"""주간 점검현황 보고서만 다시 찍는다 — 도로 실거리 반영 후 이동거리 문구 갱신 확인용.

capture_screens.py 전체를 다시 돌리면 무관한 화면까지 재촬영해 몇 분이 더 걸린다.
이번에 바뀐 건 동선 거리뿐이므로 보고서 화면만 다시 찍는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://waterside-guard.vercel.app"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screens")
VIEWPORT = {"width": 1600, "height": 1000}
SCALE = 2


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE, locale="ko-KR")
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(9000)

        page.get_by_role("button", name="주간 점검현황").click()
        page.wait_for_timeout(1500)
        page.get_by_role("button", name="보고서 생성").click()
        print("보고서 생성 대기(최대 3분)...")
        page.wait_for_selector("text=총괄 요약", timeout=180_000)
        page.wait_for_timeout(4000)

        doc = page.locator(".report-doc")
        page.screenshot(path=str(OUT / "07_주간보고서_상단.png"))
        doc.screenshot(path=str(OUT / "08_주간보고서_전문.png"))
        print(f"저장: 07_주간보고서_상단.png, 08_주간보고서_전문.png -> {OUT}/")
        browser.close()


if __name__ == "__main__":
    main()
