"""제안서용 화면 캡처 — 배포본을 실제로 조작하며 찍는다.

**왜 배포본을 찍는가**: 제안서에 들어갈 화면은 심사위원이 링크로 여는 화면과 같아야 한다.
로컬 dev 서버는 정적 모드가 꺼져 있어 배포본과 데이터 경로가 다르다.

**해상도**: device_scale_factor=2로 찍어 실제 픽셀은 지정 뷰포트의 2배가 된다
(1600x1000 -> 3200x2000). 제안서를 인쇄해도 글자가 뭉개지지 않게 하기 위함이다.

**대기 시간**: AGENT 응답은 30~40초, 주간보고서는 필지별 근거 조회까지 겹쳐 더 걸린다.
Render 무료 티어가 절전 상태면 여기에 40~60초가 더 붙는다 — 타임아웃을 넉넉히 잡는다.

사용법:
    python scripts/capture_screens.py [--url https://...] [--out <폴더>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

DEFAULT_URL = "https://waterside-guard.vercel.app"
VIEWPORT = {"width": 1600, "height": 1000}
SCALE = 2


def _shot(target, path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    target.screenshot(path=str(path))
    kb = path.stat().st_size / 1024
    print(f"  저장: {path.name}  ({kb:,.0f} KB)  — {label}")


def _select_top_site(page: Page) -> None:
    """목록 첫 그룹의 최상위 필지를 선택한다(대심리 47-16, 86점 1순위)."""
    page.locator("aside button").filter(has_text="대심리").first.click()
    page.wait_for_timeout(6000)  # 근거 조회 + NDVI 오버레이 로드


def capture(url: str, out: Path) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE, locale="ko-KR")
        page = ctx.new_page()

        print(f"대상: {url}\n")
        page.goto(url, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(9000)  # 위성 타일

        # 1. 메인 대시보드 — 제안서 대표 이미지
        _shot(page, out / "01_메인_대시보드.png", "전체 화면")

        # 2. 근거 카드 (F2) — 리서치가 "발표에서 Agent보다 10배 중요"라고 한 화면
        _select_top_site(page)
        _shot(page, out / "02_전체화면_필지선택.png", "필지 선택 상태 전체")
        panel = page.locator("aside").last
        _shot(panel, out / "03_근거카드_EvidenceCard.png", "F2 우선순위 산정 근거 패널")

        # 3. 점검 예산 시뮬레이터 (F4) — 예산 밖 항목이 흐려진 목록
        left = page.locator("aside").first
        _shot(left, out / "04_점검예산_시뮬레이터.png", "F4 주간 배정 + 권역 동선 + 목록")

        # 4. 고해상도 시기별 영상 (F6)
        try:
            hi = page.locator("h3", has_text="시기별 고해상도").locator("..")
            hi.scroll_into_view_if_needed()
            page.wait_for_timeout(4000)
            _shot(hi, out / "05_고해상도_시기별영상.png", "F6 Esri Wayback 시기별 비교")
        except Exception as e:  # noqa: BLE001
            print(f"  건너뜀(고해상도 영상): {type(e).__name__}")

        # 5. 예측 성능 검증 — 계절 기준선 6건 -> 0건 (라벨 없이 낼 수 있는 핵심 근거)
        page.get_by_role("button", name="예측 성능 검증").click()
        page.wait_for_timeout(6000)
        _shot(page.locator("[role=dialog]"), out / "06_예측성능검증_계절기준선.png", "오탐 6건→0건")
        page.keyboard.press("Escape")
        page.wait_for_timeout(1200)

        # 6. 주간 점검현황 보고 — 생성까지 시간이 걸린다
        page.get_by_role("button", name="주간 점검현황").click()
        page.wait_for_timeout(1500)
        page.get_by_role("button", name="보고서 생성").click()
        print("  보고서 생성 대기(최대 3분)...")
        page.wait_for_selector("text=총괄 요약", timeout=180_000)
        page.wait_for_timeout(4000)
        doc = page.locator(".report-doc")
        _shot(page, out / "07_주간보고서_상단.png", "보고서 화면")
        _shot(doc, out / "08_주간보고서_전문.png", "보고서 전체(세로 긴 이미지)")
        page.keyboard.press("Escape")
        page.wait_for_timeout(1200)

        # 7. AGENT 근거 조회 — 추천 질문 + 실제 답변
        page.locator('[aria-label="AGENT 조회창 열기"]').click()
        page.wait_for_timeout(1200)
        chat = page.locator(".glass.fixed").first
        _shot(chat, out / "09_AGENT_추천질문.png", "추천 질문 4종")
        page.locator(".glass.fixed button", has_text="왜 우선순위에 올랐").click()
        print("  AGENT 응답 대기(최대 3분)...")
        page.wait_for_selector("text=우선순위 근거", timeout=180_000)
        page.wait_for_timeout(8000)  # 타이핑 효과 종료
        _shot(chat, out / "10_AGENT_근거조회_답변.png", "근거 칩 포함 답변")

        browser.close()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", default="docs/screens")
    args = ap.parse_args()
    out = Path(args.out)
    capture(args.url, out)
    print(f"\n완료 -> {out}/")


if __name__ == "__main__":
    main()
