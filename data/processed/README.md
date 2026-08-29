# data/processed/

`data/raw/`를 가공한 결과. 재현 가능하면 커밋하지 않는 게 원칙이지만, 이 프로젝트는 검증 결과물이 곧 공모전 증거 자료이므로 작은 벡터 파일은 커밋한다(대용량 래스터 `*.tif`는 `.gitignore`로 제외).

## 파일

| 파일 | 생성 스크립트 | 내용 |
|---|---|---|
| `yongin_yubang_parcels.geojson` | `scripts/fetch_parcel_geometry.py` | 유방동 85필지 중 82필지(96.5%) 복원. EPSG:5179 저장(ARCHITECTURE.md §4.1) |
| `yongin_yubang_parcels_미확인_pnu.txt` | 〃 | 연속지적도에서 못 찾은 PNU 3건(149-4/149-1/147-1) — 필지 합병·분할 추정, ARCHITECTURE.md §3.2 참조 |
| `yongin_yubang_parcels_preview.png` | (수동 matplotlib 스크립트) | 시각 검증용 정적 미리보기 |

재현:

```bash
python scripts/fetch_parcel_geometry.py \
  --input data/raw/yongin_yubang_maesu.csv \
  --output data/processed/yongin_yubang_parcels.geojson
```
