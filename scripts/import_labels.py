"""판독 완료된 라벨 CSV를 현장점검 기록으로 되돌려 넣는다 — §Real Validation Pack의 후반부.

`build_label_candidates.py`가 내보낸 CSV에 사람이 verdict/change_type을 채워 넣으면,
이 스크립트가 그것을 Module FIELD 규약에 맞는 현장점검 레코드로 변환해 저장한다.
그 순간부터 `GET /verify/backtest`가 실제 라벨로 Precision@K·Recall@K를 계산할 수 있다.

**판독 라벨과 실제 현장점검을 구분한다**: `inspector_id`를 `reviewer:<이름>` 형태로 남기고
`label_source`를 "image_review"로 표시한다 — 고해상도 영상 판독은 현장 방문(Gold)보다
약한 근거(Silver)이므로, 나중에 둘을 섞어 쓰면서 그 차이를 숨기면 안 된다(§9).

사용법:
    python scripts/import_labels.py --csv data/labels/label_candidates.csv
    python scripts/import_labels.py --csv ... --dry-run   # 검증만
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from module_field.run import VALID_CATEGORIES, VALID_VERDICTS

OUTPUT_PATH = Path("data/labels/reviewed_labels.json")


def parse_rows(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """CSV 행 -> 현장점검 레코드. 순수 함수(파일·네트워크 접근 없음)라 테스트에서 그대로 쓴다.

    반환: (유효 레코드, 사람이 읽을 오류 메시지 목록)
    """
    records: list[dict] = []
    problems: list[str] = []

    for i, row in enumerate(rows, start=2):  # 2행부터가 데이터(1행은 헤더)
        verdict = (row.get("verdict") or "").strip()
        if not verdict:
            continue  # 아직 판독 안 한 행은 조용히 건너뛴다

        site_id = (row.get("site_id") or "").strip()
        if not site_id:
            problems.append(f"{i}행: site_id 없음")
            continue
        if verdict not in VALID_VERDICTS:
            problems.append(f"{i}행({site_id}): verdict '{verdict}'가 유효하지 않음 {sorted(VALID_VERDICTS)}")
            continue

        change_type = (row.get("change_type") or "").strip() or None
        if verdict == "yes" and not change_type:
            problems.append(f"{i}행({site_id}): verdict=yes인데 change_type이 비어 있음")
            continue
        if change_type and change_type not in VALID_CATEGORIES:
            problems.append(f"{i}행({site_id}): change_type '{change_type}'가 유효하지 않음 {sorted(VALID_CATEGORIES)}")
            continue

        reviewer = (row.get("reviewer") or "").strip() or "unknown"
        reviewed_at = (row.get("reviewed_at") or "").strip()
        if not reviewed_at:
            problems.append(f"{i}행({site_id}): reviewed_at이 비어 있음 — leakage 검사에 필요하다(§10)")
            continue

        records.append(
            {
                "site_id": site_id,
                "inspector_id": f"reviewer:{reviewer}",
                "inspected_at": reviewed_at,
                # "판단 보류"는 양성으로 세지 않는다 — Module VERIFY의 정답 라벨은 이 불리언이다.
                "actual_anomaly_found": verdict == "yes",
                "verdict": verdict,
                "anomaly_category": change_type,
                # 현장 방문(Gold)이 아니라 영상 판독(Silver)임을 기록에 남긴다
                "label_source": "image_review",
                "note": (row.get("note") or "").strip(),
                "stratum": (row.get("stratum") or "").strip(),
            }
        )

    return records, problems


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="data/labels/label_candidates.csv")
    parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 검증만")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"파일이 없습니다: {csv_path}")
        print("먼저 python scripts/build_label_candidates.py 로 후보를 만드세요.")
        return

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    records, problems = parse_rows(rows)

    if problems:
        print(f"검증 실패 {len(problems)}건:")
        for p in problems:
            print("  -", p)
        if not records:
            return
        print()

    positives = sum(1 for r in records if r["actual_anomaly_found"])
    by_stratum: dict[str, int] = {}
    for r in records:
        by_stratum[r["stratum"]] = by_stratum.get(r["stratum"], 0) + 1

    print(f"판독 완료 {len(records)}건 (양성 {positives}건 / 음성·보류 {len(records) - positives}건)")
    print(f"구간별: {by_stratum}")
    if len(records) < 30:
        print("경고: 30건 미만이면 Precision@K가 통계적으로 불안정합니다(리서치 권장 50~100건).")

    if args.dry_run:
        print("\n--dry-run 이므로 저장하지 않았습니다.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장 -> {OUTPUT_PATH}")
    print("api_server를 재시작하면 GET /verify/backtest가 이 라벨로 채점합니다.")


if __name__ == "__main__":
    main()
