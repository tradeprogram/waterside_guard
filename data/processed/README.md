# data/processed/

`data/raw/`를 가공한 결과. 재현 가능하면 커밋하지 않는 게 원칙이지만, 이 프로젝트는 검증 결과물이 곧 공모전 증거 자료이므로 작은 벡터 파일은 커밋한다(대용량 래스터 `*.tif`는 `.gitignore`로 제외).

## 파일

| 파일 | 생성 스크립트 | 내용 |
|---|---|---|
| `yongin_yubang_parcels.geojson` | `scripts/fetch_parcel_geometry.py` | 유방동 실증 AOI 85필지 중 82필지(96.5%) 복원. EPSG:5179 저장(ARCHITECTURE.md §4.1) |
| `yongin_yubang_parcels_미확인_pnu.txt` | 〃 | 못 찾은 PNU 3건(149-4/149-1/147-1) — 필지 합병·분할 추정 |
| `yongin_yubang_parcels_preview.png` | (수동 matplotlib 스크립트) | 시각 검증용 정적 미리보기 |
| `hanriver_maesu_parcels.geojson` | 〃 | 한강유역환경청 매수토지 전체 6,275건 중 **5,526건(88.1%) 복원**. bounds가 한강 수계(위도 37.05~37.85, 경도 127.20~127.89)와 일치함을 확인(2026-08-29) |
| `hanriver_maesu_parcels_미확인_pnu.txt` | 〃 | 못 찾은 PNU 749건 — 필지 합병·분할·연속지적도 미등재 추정, 원인 분석은 미착수 |
| `yongin_yubang_priority_queue.geojson` | `scripts/run_priority_queue_demo.py` | OBS→CHG→AGG→RISK 전체 파이프라인을 유방동 실제 필지 10건에 실행한 결과. `risk_score` 내림차순 정렬, `rank` 필드 포함 |
| `yongin_yubang_priority_queue.json` | 〃 | 위 결과의 geometry 없는 요약(표 형태) |
| `yongin_yubang_priority_queue_preview.png` | (수동 matplotlib 스크립트) | risk_score choropleth 시각 검증용 |

재현:

```bash
python scripts/fetch_parcel_geometry.py \
  --input data/raw/yongin_yubang_maesu.csv \
  --output data/processed/yongin_yubang_parcels.geojson

python scripts/fetch_parcel_geometry.py \
  --input data/raw/hanriver_maesu_raw.csv \
  --output data/processed/hanriver_maesu_parcels.geojson

# 전체 파이프라인(OBS→CHG→AGG→RISK) 실증 — repo 루트에서 실행
PYTHONPATH=. python scripts/run_priority_queue_demo.py --limit 10
```

전체 6,275건 기준 PNU당 개별 API 호출이라 약 25~40분 소요된다. `run_priority_queue_demo.py`는 필지당 Earth Engine 왕복이 많아(최대 8회) `--limit`를 82(유방동 전체)로 올리면 상당히 오래 걸린다 — ARCHITECTURE.md §12 B급 확장에서 `reduceRegions` 기반 배치 처리로 성능 개선 예정.
