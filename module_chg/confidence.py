"""증거 신뢰도(evidence_confidence) 산정 — ARCHITECTURE.md §9 불확실성 표기 원칙.

**이건 "훼손될 확률"이 아니다.** "지금 이 대상지에 대해 우리가 가진 위성 증거를 얼마나
믿을 수 있는가"만 나타낸다. 중간점검 리서치(2026-08-30)가 지적한 두 가지를 반영한다:

1. 기존 `confidence_interval`은 current scene 평균들의 변동성을 anomaly score 주변에
   배치한 값이라 **통계적으로 calibration된 신뢰구간이 아니다** — 이름을 그대로 두면
   "95% CI인가? sampling distribution이 뭔가?"라는 공격을 받는다. `signal_variability`로
   이름을 바꾸고(module_chg/run.py), 신뢰도는 이 모듈이 별도로 계산한다.
2. 신뢰도는 단일 숫자보다 **"무엇 때문에 믿을 만한가/못한가"의 목록**이어야 화면에서
   근거로 쓸 수 있다 — 그래서 level만이 아니라 `factors`(± 사유)를 함께 반환한다.

가중치는 리서치의 신뢰도 표(§ evidence_confidence)를 그대로 옮긴 초기 가정치다.
"""
from __future__ import annotations

MIN_SCENES_FOR_CONFIDENCE = 3  # 유효 광학 장면이 이 개수 이상이면 가점
MAX_CLOUD_PCT_FOR_CONFIDENCE = 30.0  # 평균 구름비율이 이보다 높으면 감점
SENSOR_AGREEMENT_TOLERANCE = 0.02  # 이보다 큰 변화량만 방향 일치 판정에 쓴다(잡음 제외)
HEAVY_RAINFALL_MM = 50.0  # 최근 14일 누적강우가 이 이상이면 기상 교란 가능성을 경고

LEVEL_THRESHOLDS = [(3, "높음"), (1, "보통")]  # 그 미만은 "낮음"


def _mean_cloud_pct(scenes: list[dict]) -> float | None:
    values = [s.get("cloud_cover_pct") for s in scenes if s.get("cloud_cover_pct") is not None]
    return sum(values) / len(values) if values else None


def compute_evidence_confidence(
    baseline_scenes: list[dict],
    current_scenes: list[dict],
    *,
    ndvi_delta: float | None,
    ndmi_delta: float | None,
    sar_vv_delta: float | None,
    changed_area_ratio_source: str | None,
    recent_rainfall_mm: float | None = None,
) -> dict:
    """returns {"level": "높음"|"보통"|"낮음", "score": int, "factors": [{label, effect, detail}]}

    `effect`는 +2/+1/-1/-2 — UI가 그대로 ↑↓ 아이콘·색으로 그릴 수 있게 부호와 크기를 나눠 준다.
    """
    factors: list[dict] = []

    def add(label: str, effect: int, detail: str) -> None:
        factors.append({"label": label, "effect": effect, "detail": detail})

    # 1) 유효 광학 장면 수
    n_current = len(current_scenes)
    if n_current >= MIN_SCENES_FOR_CONFIDENCE:
        add("유효 광학 장면 충분", 1, f"현재기간 {n_current}장")
    elif n_current == 0:
        add("광학 관측 없음", -2, "구름 등으로 유효 장면 0장 — SAR 단독 판단")
    else:
        add("유효 광학 장면 부족", -1, f"현재기간 {n_current}장(기준 {MIN_SCENES_FOR_CONFIDENCE}장)")

    # 2) 기준기간 장면 수 — 비교 대상이 빈약하면 "정상 범위"를 알 수 없다
    n_baseline = len(baseline_scenes)
    if n_baseline >= MIN_SCENES_FOR_CONFIDENCE:
        add("기준기간 관측 충분", 1, f"기준기간 {n_baseline}장")
    elif n_baseline == 0:
        add("기준기간 관측 없음", -2, "비교 기준이 없어 변화량을 신뢰할 수 없음")
    else:
        add("기준기간 관측 부족", -1, f"기준기간 {n_baseline}장")

    # 3) 구름/유효픽셀 품질
    cloud = _mean_cloud_pct(current_scenes)
    if cloud is not None:
        if cloud > MAX_CLOUD_PCT_FOR_CONFIDENCE:
            add("구름 영향 큼", -2, f"현재기간 평균 구름 {cloud:.0f}%")
        else:
            add("영상 품질 양호", 1, f"현재기간 평균 구름 {cloud:.0f}%")

    # 4) NDVI·NDMI 방향 일치 — 서로 반대로 움직이면 해석이 갈린다
    if ndvi_delta is not None and ndmi_delta is not None:
        if abs(ndvi_delta) > SENSOR_AGREEMENT_TOLERANCE and abs(ndmi_delta) > SENSOR_AGREEMENT_TOLERANCE:
            if (ndvi_delta > 0) == (ndmi_delta > 0):
                add("NDVI·NDMI 방향 일치", 1, f"둘 다 {'증가' if ndvi_delta > 0 else '감소'}")
            else:
                add("NDVI·NDMI 방향 불일치", -1, "식생과 수분 지표가 반대로 움직임")

    # 5) 광학·SAR 센서 간 일치 — 서로 다른 물리 원리의 센서가 같은 방향이면 가장 강한 근거
    if ndvi_delta is not None and sar_vv_delta is not None:
        if abs(ndvi_delta) > SENSOR_AGREEMENT_TOLERANCE and abs(sar_vv_delta) > 0.5:
            # 식생이 줄면 후방산란이 보통 올라간다(지표 노출) — 부호가 반대일 때 "일치"로 본다
            if (ndvi_delta < 0) == (sar_vv_delta > 0):
                add("광학·SAR 센서 일치", 2, "서로 다른 센서가 같은 변화를 가리킴")
            else:
                add("광학·SAR 센서 불일치", -1, "두 센서가 다른 방향을 가리킴")

    # 6) 변화면적이 실측인지 근사인지
    if changed_area_ratio_source == "pixel_diff":
        add("변화면적 픽셀 실측", 1, "NDVI 픽셀 단위 차분으로 직접 측정")
    elif changed_area_ratio_source == "approximated":
        add("변화면적 근사치", -1, "이상도 크기로부터 추정 — 실측 아님")

    # 7) 기상 교란 가능성 — 강우 직후의 NDMI·SAR 변화는 훼손이 아니라 수분 변화일 수 있다
    if recent_rainfall_mm is not None and recent_rainfall_mm >= HEAVY_RAINFALL_MM:
        wet_signal = (ndmi_delta is not None and ndmi_delta > 0) or (sar_vv_delta is not None and sar_vv_delta < 0)
        if wet_signal:
            add(
                "강우 교란 가능성",
                -1,
                f"최근 14일 {recent_rainfall_mm:.0f}mm 강우 + 습윤 신호 — 기상에 의한 변화일 수 있음",
            )

    score = sum(f["effect"] for f in factors)
    level = "낮음"
    for threshold, name in LEVEL_THRESHOLDS:
        if score >= threshold:
            level = name
            break

    return {"level": level, "score": score, "factors": factors}
