# data/raw/

원본 데이터는 가공하지 않고 그대로 보존한다. 가공 결과는 `../processed/`에 둔다.

## 파일

| 파일 | 내용 | 출처 |
|---|---|---|
| `hanriver_maesu_raw.csv` | 한강유역환경청 매수토지 전체, 6,275행. 컬럼: `토지고유코드`(PNU 19자리)/`소재지`/`데이터기준일` | data.go.kr |
| `yongin_yubang_maesu.csv` | 위 데이터 중 용인시 처인구 유방동 필터링, 85행 — 실증 AOI | data.go.kr 원본에서 파생 |

두 파일 모두 좌표(geometry)가 없다 — PNU 코드만 있다. Milestone 1(`ARCHITECTURE.md` §3.2)에서 V-World 연속지적도(`LP_PA_CBND_BUBUN`)를 PNU로 조회해 필지 폴리곤을 복원한다.
