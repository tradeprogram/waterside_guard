"""배포용 정적 API 스냅샷 생성 — 실행 중인 로컬 API의 응답을 그대로 파일로 굽는다.

**왜 이렇게 배포하는가**: 이 프로토타입의 조회용 응답은 전부 사전계산된 결과를 읽는 것이라
요청 때마다 계산할 이유가 없다. 반면 실시간 계산이 필요한 것(GEE 썸네일, Gemini 응답)은
느리거나(30~40초) 자격증명이 필요해서 서버리스에 얹기 어렵다. 그래서 조회는 정적 파일로
내리고, 대화·등록만 최소 백엔드에 남긴다 — 심사 중 콜드스타트나 타임아웃으로 화면이
비는 사고를 원천 차단하는 게 목적이다.

**썸네일은 이미지까지 받아 온다**: GEE가 주는 URL은 만료되므로 링크만 저장하면 며칠 뒤
깨진다. 실제 PNG를 내려받아 `public/api/thumbnails/`에 두고 JSON의 url을 로컬 경로로
바꾼다. 반대로 고해상도 실사영상(Esri Wayback)은 자격증명 없는 공개 타일이라 URL을
그대로 둬도 배포 환경에서 동작한다.

사용법:
    python -m uvicorn api_server:app --port 8001   # 먼저 로컬 API를 띄운다
    python scripts/build_static_api.py
    -> ui/public/api/**.json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API_BASE = "http://localhost:8001"
OUT_DIR = Path("ui/public/api")

# UI의 점검 배정 슬라이더가 낼 수 있는 값 — 프리셋(5·10·20)과 직접입력을 모두 덮는다.
ROUTE_BUDGETS = range(1, 31)
# 성능검증 화면이 쓰는 K. 현장 라벨이 없는 동안 UI는 k 입력을 렌더하지 않으므로 기본값만 필요하다.
VERIFY_K = 10
# GEE 썸네일은 한 장에 1~3초 걸린다. 병렬로 받되 할당량을 자극하지 않게 적게 둔다.
MAX_WORKERS = 4


def _get(path: str) -> dict | list:
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=180) as r:
        return json.load(r)


def _write(rel: str, payload) -> Path:
    path = OUT_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _download(url: str, rel: str) -> bool:
    path = OUT_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            path.write_bytes(r.read())
        return True
    except Exception as e:  # noqa: BLE001 — 한 장 실패가 전체를 막지 않게 한다
        print(f"    썸네일 내려받기 실패({rel}): {type(e).__name__}")
        return False


def build_site(site_id: str) -> dict:
    """한 필지의 조회용 응답 4종을 굽는다. 썸네일은 이미지까지 내려받아 경로를 바꾼다."""
    result = {"site_id": site_id, "thumbs": 0, "failed": []}

    for name, path in (
        ("evidence", f"/sites/{site_id}/evidence"),
        ("timeseries", f"/sites/{site_id}/timeseries"),
        ("highres", f"/sites/{site_id}/highres"),
    ):
        try:
            _write(f"sites/{site_id}/{name}.json", _get(path))
        except Exception as e:  # noqa: BLE001
            result["failed"].append(f"{name}: {type(e).__name__}")

    # 썸네일 — URL이 만료되므로 이미지를 실제로 받아 두고 JSON을 로컬 경로로 고쳐 쓴다.
    try:
        thumbs = _get(f"/sites/{site_id}/thumbnails")
        for period in ("baseline", "current"):
            t = thumbs.get(period)
            if not t or not t.get("url"):
                continue
            rel = f"thumbnails/{site_id}_{period}.png"
            if _download(t["url"], rel):
                t["url"] = f"/api/{rel}"
                result["thumbs"] += 1
            else:
                thumbs[period] = None
        _write(f"sites/{site_id}/thumbnails.json", thumbs)
    except Exception as e:  # noqa: BLE001
        result["failed"].append(f"thumbnails: {type(e).__name__}")

    return result


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-thumbnails", action="store_true", help="GEE 썸네일을 건너뛴다(빠른 재생성용)")
    args = parser.parse_args()

    print(f"정적 스냅샷 생성 (API: {API_BASE}) -> {OUT_DIR}/\n")

    print("[전역]")
    sites = _get("/sites")
    _write("sites.json", sites)
    print(f"  sites.json ({len(sites)}필지)")

    _write("priority-queue.json", _get("/priority-queue"))
    print("  priority-queue.json")

    for k in (VERIFY_K,):
        _write(f"verify/ablation-{k}.json", _get(f"/verify/ablation?k={k}"))
        _write(f"verify/backtest-{k}.json", _get(f"/verify/backtest?period=current&k={k}"))
    print(f"  verify/ablation-{VERIFY_K}.json, verify/backtest-{VERIFY_K}.json")

    for b in ROUTE_BUDGETS:
        _write(f"route/{b}.json", _get(f"/priority-queue/route?budget={b}"))
    print(f"  route/{{{ROUTE_BUDGETS.start}..{ROUTE_BUDGETS.stop - 1}}}.json")

    print(f"\n[필지별] {len(sites)}건" + (" (썸네일 생략)" if args.skip_thumbnails else " · GEE 썸네일 포함이라 수 분 걸립니다"))
    site_ids = [s["site_id"] for s in sites]

    def work(sid: str) -> dict:
        if args.skip_thumbnails:
            for name, path in (
                ("evidence", f"/sites/{sid}/evidence"),
                ("timeseries", f"/sites/{sid}/timeseries"),
                ("highres", f"/sites/{sid}/highres"),
            ):
                _write(f"sites/{sid}/{name}.json", _get(path))
            return {"site_id": sid, "thumbs": 0, "failed": []}
        return build_site(sid)

    done = thumbs = 0
    problems: list[str] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for r in pool.map(work, site_ids):
            done += 1
            thumbs += r["thumbs"]
            if r["failed"]:
                problems.append(f"{r['site_id']}: {', '.join(r['failed'])}")
            if done % 10 == 0 or done == len(site_ids):
                print(f"  {done}/{len(site_ids)} 완료 (썸네일 {thumbs}장)")

    if problems:
        print(f"\n실패 {len(problems)}건:")
        for p in problems[:10]:
            print(f"  {p}")

    total = sum(1 for _ in OUT_DIR.rglob("*") if _.is_file())
    size = sum(f.stat().st_size for f in OUT_DIR.rglob("*") if f.is_file())
    print(f"\n완료 — 파일 {total}개, {size / 1_048_576:.1f}MB -> {OUT_DIR}/")


if __name__ == "__main__":
    main()
