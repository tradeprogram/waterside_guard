"""라벨링 파이프라인(후보 추출 -> 판독 -> 재수입)의 순수 로직 테스트.

GEE·파일 접근이 없는 함수만 골라 테스트한다 — 표본 편향 방지와 입력 검증이 핵심이라
그 두 가지가 실제로 동작하는지 확인한다.
"""
from scripts.build_label_candidates import stratified_sample
from scripts.import_labels import parse_rows


def _sites(n: int) -> list[dict]:
    # 점수 100, 98, 96 ... 로 내림차순 배치
    return [{"site_id": f"S{i}", "inspection_priority_score": 100 - i * 2} for i in range(n)]


def test_stratified_sample_covers_all_score_ranges():
    """상위만 뽑으면 Recall을 못 잰다 — 하위 구간에서도 반드시 표본이 나와야 한다."""
    picked = stratified_sample(_sites(60), n=30)
    strata = {p["stratum"] for p in picked}
    assert strata == {"상위", "중위", "하위"}


def test_stratified_sample_is_reproducible():
    """같은 seed면 같은 표본 — 판독 결과를 나중에 재검증할 수 있어야 한다."""
    a = stratified_sample(_sites(60), n=20)
    b = stratified_sample(_sites(60), n=20)
    assert [p["site_id"] for p in a] == [p["site_id"] for p in b]


def test_stratified_sample_handles_small_population():
    picked = stratified_sample(_sites(3), n=30)
    assert len(picked) <= 3


def test_parse_rows_skips_unreviewed_without_error():
    rows = [{"site_id": "S1", "verdict": "", "change_type": "", "reviewer": "", "reviewed_at": ""}]
    records, problems = parse_rows(rows)
    assert records == [] and problems == []


def test_parse_rows_accepts_valid_review():
    rows = [
        {
            "site_id": "S1",
            "verdict": "yes",
            "change_type": "bare_ground",
            "reviewer": "kim",
            "reviewed_at": "2026-09-05T10:00:00+09:00",
            "note": "",
            "stratum": "상위",
        }
    ]
    records, problems = parse_rows(rows)
    assert problems == []
    assert records[0]["actual_anomaly_found"] is True
    assert records[0]["inspector_id"] == "reviewer:kim"
    # 현장 방문이 아니라 영상 판독임을 반드시 남긴다
    assert records[0]["label_source"] == "image_review"


def test_parse_rows_rejects_yes_without_change_type():
    rows = [{"site_id": "S1", "verdict": "yes", "change_type": "", "reviewer": "kim", "reviewed_at": "2026-09-05"}]
    records, problems = parse_rows(rows)
    assert records == []
    assert any("change_type" in p for p in problems)


def test_parse_rows_rejects_invalid_verdict_and_category():
    rows = [
        {"site_id": "S1", "verdict": "maybe", "change_type": "", "reviewer": "k", "reviewed_at": "2026-09-05"},
        {"site_id": "S2", "verdict": "yes", "change_type": "폭발", "reviewer": "k", "reviewed_at": "2026-09-05"},
    ]
    records, problems = parse_rows(rows)
    assert records == []
    assert len(problems) == 2


def test_parse_rows_requires_reviewed_at_for_leakage_check():
    rows = [{"site_id": "S1", "verdict": "no", "change_type": "", "reviewer": "kim", "reviewed_at": ""}]
    records, problems = parse_rows(rows)
    assert records == []
    assert any("reviewed_at" in p for p in problems)


def test_uncertain_verdict_is_not_counted_as_positive():
    rows = [{"site_id": "S1", "verdict": "uncertain", "change_type": "", "reviewer": "k", "reviewed_at": "2026-09-05"}]
    records, problems = parse_rows(rows)
    assert problems == []
    assert records[0]["actual_anomaly_found"] is False
    assert records[0]["verdict"] == "uncertain"  # 음성과 구분되게 원래 값도 남는다
