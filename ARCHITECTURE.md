# 수변생태벨트 점검 우선순위 지원시스템 — 아키텍처 확정안 v1.0

> 이 문서는 이 프로젝트의 정본(Source of Truth)이다. 배경지식이 없는 Claude Code 세션이 이 문서 하나만 읽고 바로 작업을 이어갈 수 있도록 쓰였다. **§0을 반드시 먼저 읽어라** — "무엇을 왜 만드는지"를 이해하지 못한 채 §5의 모듈 계약만 구현하면 숫자는 맞아도 프로젝트의 목적을 놓친 코드가 나온다.
>
> 참고 벤치마크: [tradeprogram/Aquaguard](https://github.com/tradeprogram/Aquaguard) — envelope 규약·폴백계층·상태머신·모듈 계약 패턴 출처. [tradeprogram/policymaps](https://github.com/tradeprogram/policymaps) — 검증배지·데이터 출처 공시·MCP tool화 패턴 출처.
>
> 원본 리서치: [`docs/2026_KECI_공모전_수상전략_리서치.pdf`](docs/2026_KECI_공모전_수상전략_리서치.pdf), 핸드오프 브리프: [`docs/개발_핸드오프_브리프.md`](docs/개발_핸드오프_브리프.md).

**프로젝트명**: 수변생태벨트 점검 우선순위 지원시스템 (저장소명 `waterside_guard`) — 한국환경보전원(KECI)이 관리하는 전국 수변녹지·매수토지의 현장점검 우선순위를 위성 변화탐지 + GIS 다요인 점수로 자동 산출하는 의사결정지원 시스템.

**명칭 변경(2026-08-31)**: 옛 이름 "수변가드 AI"를 버렸다. 리서치가 기관 적합성에서 7점과 10점을 가르는 기준으로 "공식 사업명을 제안서에 직접 연결"을 꼽았는데 KECI의 공식 핵심사업명이 「수변생태벨트 조성·관리」이고, 같은 리서치가 "AI를 핵심으로 과장하지 않는다"·"전면은 수변녹지 관리 의사결정 시스템"이라고 못박았기 때문이다. '가드'의 감시·단속 어감도 국민 재산을 매수해 관리하는 사업의 성격과 맞지 않는다. 저장소명은 remote URL이 깨지므로 그대로 둔다.

**공모전**: 2026년 한국환경보전원 대국민 환경혁신 아이디어 공모전(부제: 환경을 잇다, 미래를 잇다). 접수 2026.9.1.~9.30. 18:00. 공모분야는 **환경사업·정책 혁신**을 1순위로 지원한다(디지털·ESG보다 "기존 수변생태 관리사업의 성과를 높인다"는 프레이밍이 기관 고유성·문제 중요성을 더 잘 살림).

---

## 0. 프로젝트 배경 — 왜 이걸 만드는가 (반드시 먼저 읽을 것)

### 0.1 기관이 이미 만든 것과 아직 없는 것

한국환경보전원(KECI)은 4대강 수계의 대규모 수변녹지·매수토지를 관리한다. 수변생태벨트는 상수원 수질개선·생태복원 기능을 수행하며 일부는 생태교육 공간으로도 운영된다.

2025년 말 KECI는 약 **591만㎡·전국 1,700여 개소**의 수변녹지 준공도면을 GIS 공간정보로 전환했고, 향후 AI 기반 수변생태 관리에 활용하겠다는 방향을 공개했다. 매수토지 현장 확인·모니터링에는 이미 드론을 운용 중이며, 2026년 8월에는 국토지리정보원과 국토위성·항공·드론 영상 및 공간정보를 활용한 환경관리 고도화 협력을 시작했다.

**따라서 "위성으로 수변녹지를 모니터링하자"는 아이디어 자체는 이미 늦었다.** 그대로 제출하면 "이미 보전원이 하고 있는 일 아닌가?"라는 공격을 받는다. 공개자료상 KECI는 이미 GIS 기반 데이터 구축, 드론 모니터링, 국토위성 활용을 향해 이동하고 있기 때문이다.

**그런데 그 데이터 기반 위에 없는 것이 하나 있다**: 많은 공간자산과 다양한 영상 중 **"어느 곳을 오늘 먼저 사람이 확인해야 하는지"를 자동으로 결정하는 운영 layer**다. GIS 자산관리와 영상정보가 있어도 그것이 "행동 우선순위"로 변환되지 않으면 데이터 구축의 효과는 제한된다.

### 0.2 이 프로젝트가 푸는 문제

**"많은 공간자산과 다양한 영상 중 어느 곳을 먼저 사람이 확인해야 하는지 결정하는 비용"** — 이것이 문제의 정확한 정의다. 데이터 부족이 아니다.

현재 KECI의 흐름: `복원·식재 → GIS 구축 → 순찰·드론 확인 → 식생관리·주민참여 → 보고`

본 시스템이 끼워 넣는 고부가가치 단계: `복원·식재 → 지속 관측 → 이상변화 자동 선별 → 우선점검 → 현장 확인 → 전후 효과 자동 검증 → 다음 관리 우선순위`

### 0.3 한 문장 포지셔닝

> 본 시스템은 새로운 위성 모니터링 플랫폼이 아니다. 한국환경보전원이 이미 구축한 GIS·드론·위성 기반 위에서, "오늘 어디를 먼저 가야 하는가"를 자동으로 계산하고, 현장 결과로 그 판단을 검증·환류하는 마지막 운영 layer다.

가장 중요한 방어 논리 — **중복성 공격에 대한 답**:

> "변화탐지 기술은 이미 성숙했다. 본 제안의 혁신은 이를 한국환경보전원의 수변녹지 자산·현장점검 프로세스에 연결하여 '관측 → 우선순위 → 현장검증 → 성과기록'으로 운영화하는 데 있다."

### 0.4 왜 Agent를 전면에 내세우지 않는가

심사위원에게 먼저 보여줄 것은 "AI Agent"가 아니라 **전국 수변녹지 중 오늘 현장직원이 먼저 가봐야 할 Top-N을 증거와 함께 제시하는 지도**다. Agent는 그 뒤에서 데이터 조회, 알림 설명, 현장점검표 생성, 주간보고서 작성을 담당한다. **Agent가 위험도를 계산하지 않는다** — 위험도는 reproducible한 GIS/ML 파이프라인(§5 Module RISK)이 계산하고, Agent는 그 결과를 tool 호출로 읽어서 설명만 한다. 숫자를 만들어내지 않는다.

Multi-Agent(Remote Sensing Agent + GIS Agent + Weather Agent...)는 하지 않는다. 단일 orchestrator(Module O)가 deterministic tool들을 호출하는 것으로 충분하다 — 이름을 여러 개 붙인다고 심사점수가 오르지 않는다.

### 0.5 기술적 해자 — 왜 이 팀이 이걸 만들 자격이 있는가

경쟁우위를 "Sentinel-2를 쓸 줄 안다"로 정의하면 약하다(다른 팀도 흉내낼 수 있음). 진짜 해자는 다음 연쇄를 혼자 구현할 수 있다는 것이다.

```
Earth Observation → 시계열 변화 → 공간 객체화 → 위험도 모델 → 현장 의사결정 → 현장 피드백 → 자동 보고
```

- **Multisensor Fusion**: Sentinel-2 광학 + Sentinel-1 SAR + DEM + 기상·수문 + 관리구역 벡터 + 현장사진을 같은 공간단위로 결합
- **Pixel-to-Decision 전환**: NDVI 지도가 아니라 대상지·필지·복원구역별 priority score로 변환
- **실제 Backtest**: "예측할 수 있습니다"에서 끝나지 않고 baseline 대비 정량 검증 (§10)
- **Human-in-the-loop Agent**: 환경판단을 대신하지 않고 분석 API를 설명·기록
- **AI가 실패해도 서비스가 작동하는 설계**: rule-based 위험점수만으로 최소기능이 항상 동작하고, label이 쌓이면 ML로 고도화 (§4.2 envelope의 `fallback_tier`가 이 원칙을 코드 레벨로 강제)

### 0.6 스코프 확정 — 반드시 하지 말아야 할 것

| 하지 않는 것 | 이유 |
|---|---|
| Sentinel-2로 위해덩굴 종(種) 자동 판별 | 10m 해상도로는 species-level 분류가 불가능, ground truth 공격에 취약 |
| 정확한 생물다양성·수질정화량·탄소흡수량 산정 | 각각 별도 과학적 검증이 필요, 범위를 넓힐수록 신뢰도 하락 — §5 Module RISK는 "이상 선별"만 하지 "정밀 측정"은 하지 않는다 |
| Multi-Agent 협업(Agent 여러 개) | 심사점수에 기여 안 함(§0.4) |
| 3D Digital Twin, autonomous drone mission | 기간 대비 구현범위 과다, 핵심 의사결정과 무관 |
| 전국 1,700개소 완성형 서비스 | MAWP(§11.2)는 1개 실증지역에서 완전히 작동하고 동일 구조를 전국에 붙일 수 있음을 증명하는 것으로 충분 |
| DNN segmentation을 처음부터 사용 | label 없이는 설명 불가능한 블랙박스가 됨 — §6 참조, rule+통계 baseline이 먼저 |
| native 모바일 앱, 실시간 전국 서비스 | 공모전 프로토타입 범위 밖 |

---

## 1. 사용자 시나리오

**Primary User**: 수변생태관리단·지역지사 현장관리 담당자.

1. 담당자가 월요일 오전 본 시스템에 접속한다. 화면에는 전체 대상지 대신 **"이번 주 확인 필요 N개소"**가 먼저 나타난다.
2. 1순위 대상지를 클릭하면 한 화면에 나타난다: 최근 영상 변화 → 변화 발생 위치 → 과거 정상시기와 비교 → 강우 이벤트 → 위험도 구성요인 → 권고 점검항목.
3. 담당자는 "현장점검 등록"을 누르고 현장에 간다.
4. 현장에서 사진·점검결과를 업로드한다(Module FIELD).
5. 시스템은 예측이 맞았는지 기록하고, 후속 영상으로 전후 변화를 다시 확인한다(Module VERIFY).
6. 주말에는 Agent가 주간보고서를 생성한다: "이번 주 고위험 N개소 중 M개소 점검 완료. K개소에서 실제 이상 확인. Precision@N = …"

---

## 2. 시스템 아키텍처

```
 [KECI 기존 관리기반]
 ┌──────────────────────────────────────────┐
 │ 수변녹지 GIS / 식재·준공정보 / 점검이력 (매수토지 PNU) │
 └──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────── Module OBS — 관측 수집·전처리 ────────────────┐
│ Sentinel-2 │ Sentinel-1 │ 국토위성* │ 드론* │ 기상·수문 API │
│ cloud mask / compositing / co-registration / index 산출     │
└───────────────────────────────────────────────────────────┘
                    │
                    ▼
            [Module CHG — 변화탐지]
        시계열 이상도 + 전후(before/after) 변화탐지
                    │
                    ▼
       [Module AGG — GIS 공간 집계]
     pixel → 관리대상지(PNU/복원구역) 단위 feature
                    │
                    ▼
            [Module RISK — 위험도 산정]
   변화크기 + 자산중요도 + 최근 이벤트 + 점검이력
        → 현장점검 Priority Score 0~100
                    │
                    ▼
       [Module O — 오케스트레이션 / 상태머신]
     지도 → Top-N 우선순위 큐 → 담당자 의사결정
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
 [Module FIELD — 현장 피드백]   [Module AGENT — Evidence Agent]
   사진/점검결과 등록            점검표 자동 생성 · 자연어 설명
         │                     │
         ▼                     │
 [Module VERIFY — 검증/Backtest] ◄──┘
  예측 vs 실측 비교, Precision@K, baseline 대비 성능
                    │
                    ▼
           다음 주기 Risk Engine 개선 (규칙 → ML)
```

`*` 국토위성·내부 드론은 실제 기관 도입 단계에서 연결하는 데이터다. 공모전 프로토타입은 Sentinel 등 공개·접근 가능한 데이터만으로 완성 가능하도록 설계한다. KECI가 이미 국토위성 협력을 추진하고 매수토지 모니터링용 드론을 운영한다는 사실은 실제 도입 경로의 근거로만 쓴다.

### 2.1 7단계 상태머신

`관측(OBS) → 변화탐지(CHG) → 공간집계(AGG) → 우선순위산정(RISK) → 우선순위생성(O) → 현장점검(FIELD) → 검증환류(VERIFY)`

Module AGENT는 별도 상태가 아니라 O/FIELD/VERIFY 위에 얹히는 설명·보고 layer다.

### 2.2 재해 대응형 확장 — 이벤트 트리거 모드

평시에는 주기적(예: 10일) 배치로 OBS→CHG→AGG→RISK가 돌지만, 호우 등 이벤트 발생 시 Module O가 event-triggered 모드로 전환해 Sentinel-1 SAR 우선 처리로 즉시 재실행한다(§10 Backtest C의 event-based 시나리오와 연결). MVP 범위에서는 배치 모드만 구현하고, 이벤트 트리거는 §12 로드맵의 B급 확장 항목으로 둔다.

---

## 3. 데이터 스택

### 3.1 실증 AOI (관심지역) — 확보 완료

| 데이터 | 내용 | 비고 |
|---|---|---|
| `hanriver_maesu_raw.csv` | 한강유역환경청 매수토지 전체, **6,275행** | data.go.kr 원본. 컬럼: `토지고유코드`(PNU 19자리)/`소재지`/`데이터기준일`. **좌표 없음** — §3.2 참조 |
| `yongin_yubang_maesu.csv` | 용인시 처인구 유방동 필터링, **85행** | 삼성전자·한강유역환경청 협력 묵논습지·수변녹지 복원사업(약 33만㎡) 부지와 일치하는 법정동. 데모 앵커 겸 다건 랭킹 검증용 후보군 |

배치: `data/raw/hanriver_maesu_raw.csv`, `data/raw/yongin_yubang_maesu.csv`(원본 보존, 2026-08-29 배치 완료). 가공 결과는 `data/processed/`로 분리.

### 3.2 필지 폴리곤 복원 (Milestone 1 핵심)

PNU 코드만으로는 GIS 분석이 불가능하다 — geometry가 없기 때문. **V-World WFS 연속지적도 서비스**(서비스ID `LP_PA_CBND_BUBUN`)를 PNU로 필터링해 폴리곤을 복원한다.

**추천 경로**: raw WFS 직접 호출보다 오픈소스 파이썬 라이브러리 [`PublicDataReader`](https://github.com/WooilJeong/PublicDataReader)(`pip install PublicDataReader`)를 먼저 시도한다.

```python
from PublicDataReader import VworldData
api = VworldData(SERVICE_KEY)
geo = api.get_data("연속지적도", attrFilter="pnu:like:4146110500100780003")
# GeoJSON dict 반환
```

raw WFS 엔드포인트·CQL_FILTER 문법을 직접 조사하는 대신 이 라이브러리로 85건(유방동)부터 조인 테스트 → 성공하면 6,275건 전체로 확장. **완료 기준**: 유방동 85필지의 polygon GeoJSON을 확보하고 실제 위치(용인시 처인구)와 대략 일치하는지 시각 검증.

**막히면**: V-World 개발자 문서(vworld.kr/dev)는 봇 접근을 막아둬서 자동 크롤링이 안 된다 — 사용자가 브라우저로 직접 확인하거나 `PublicDataReader`의 `VworldData` 클래스 소스코드를 직접 읽는 게 빠르다.

**진행 상태(2026-08-29, 완료)**: `scripts/fetch_parcel_geometry.py`로 유방동 85필지 중 **82필지(96.5%) 복원 성공**. 미확인 3필지(149-4/149-1/147-1)는 연속지적도에 없는 코드 — 필지 합병·분할로 PNU가 갱신됐을 가능성. 복원 결과의 중심좌표는 (127.2095E, 37.2622N)로 용인시 처인구 유방동 실제 위치와 일치 확인(`data/processed/yongin_yubang_parcels.geojson`, 내부 EPSG:5179 저장). `PublicDataReader.VworldData.get_data()`의 `attrFilter="pnu:like:{PNU}"` 문법이 그대로 동작함을 확인 — 라이브러리를 감싸지 않고 동일한 요청 패턴을 직접 구현했다(응답 페이지네이션·재시도 제어를 위해).

**6,275건 전체 확장도 완료**: `data/processed/hanriver_maesu_parcels.geojson` — **5,526건(88.1%) 복원**, 미확인 749건은 `hanriver_maesu_parcels_미확인_pnu.txt`. 복원 결과의 전체 범위(위도 37.05~37.85, 경도 127.20~127.89)가 한강유역환경청 관할인 한강 수계와 일치함을 확인. 미확인 749건의 원인 분석(합병·분할 vs 다른 사유)은 아직 미착수 — §12 TODO.

### 3.3 정적 레이어

| 데이터 | 소스 | 용도 |
|---|---|---|
| DEM 유도 지형(경사·곡률·TWI) | 국토정보플랫폼 DEM | Module AGG 공통 feature |
| 토지피복 | 환경부 토지피복지도 | 노출자산 분류 |
| 매수토지 PNU 폴리곤 | V-World 연속지적도(§3.2) | 관리대상지 기본 단위 |

### 3.4 동적 레이어 — Earth Observation

| 데이터 | 해상도/주기 | 용도 | 비고 |
|---|---|---|---|
| Sentinel-2 (광학) | 10m, ~5일 재방문, 13개 분광밴드 | NDVI/EVI(식생), NDMI(수분), bare/open ground 변화, 계절 정규화 이상도 | 토지피복·식생·내륙수 모니터링에 적합 |
| Sentinel-1 (SAR) | VV/VH backscatter | 구름 낀 집중호우 전후에도 광역 변화 후보 탐지 | all-weather, day-and-night. 정밀 종 분류 목적 아님 — 광역 screening 전용 |
| 강우·수문 | 기상청 API허브 등 | 이벤트 트리거, 유출위험 보조 feature | MVP는 배치 모드, 이벤트 연동은 §12 B급 |

**접근 경로**: Sentinel Hub/CDSE가 아니라 **Google Earth Engine**(`COPERNICUS/S2_SR_HARMONIZED`)으로 접근한다(2026-08-29 확정 — 사용자가 이미 GEE 접근권한을 보유). `reduceRegion`으로 AOI 단위 서버사이드 집계만 받아오므로 픽셀 래스터 전체를 내려받지 않는다. Sentinel-1은 MVP 범위에서는 미구현 — `ee.ImageCollection('COPERNICUS/S1_GRD')`로 동일 패턴 확장 가능(§12 B급).

**매우 중요한 범위 제한** — Sentinel-2로 "칡이 발생했다" 같은 종 단위 판독을 주장하지 않는다. 프로토타입이 말할 수 있는 것은: **"이 대상지는 정상적인 계절패턴과 다른 식생·피복 변화가 나타났으므로 고해상도 영상 또는 현장확인이 필요하다"**까지다. 이 정직한 범위 설정이 신뢰도를 높인다.

### 3.5 벡터 데이터

| 데이터 | 소스 |
|---|---|
| 매수토지 PNU·폴리곤 | 한강유역환경청 CSV + V-World 연속지적도 |
| 대피소·하천 등 참고 레이어 | 필요시 WAMIS 등 공개 API (MVP 범위 밖) |

---

## 4. 통합 규약 (모든 모듈 필수 준수)

솔로 개발이라도 모듈 경계를 명확히 하는 이유는: (1) Change Engine → Risk Engine → Agent 순서로 단계적으로 만들 것이므로 각 단계가 독립적으로 테스트 가능해야 하고, (2) 규칙기반 baseline에서 ML로 넘어갈 때 인터페이스가 안 바뀌어야 하기 때문이다.

### 4.1 값 표기 규칙

| 항목 | 규칙 |
|---|---|
| 좌표계 | 내부 분석·저장은 **EPSG:5179**(한국 UTM-K/중부원점 통합좌표계 — 국내 DEM·V-World 데이터가 원래 이 계열이라 거리·면적 계산이 왜곡되지 않음). 지점은 `x_5179`/`y_5179`, 폴리곤은 `geometry_5179`. **웹 지도(MapLibre) 출력 직전에만** EPSG:4326으로 재투영해 `*_geojson` 필드명으로 내보낸다 |
| 시간 | ISO 8601 + 타임존 명시. 예: `"2026-09-05T09:00:00+09:00"`(KST). UTC 금지 |
| 확률/점수 | `inspection_priority_score`는 0~100 정수, 그 외 확률형 값은 float 0.0~1.0 |
| 거리/면적 | 미터(`_m`), 헥타르(`_ha`) 또는 제곱미터(`_m2`) — 필드명에 단위 명시 필수 |
| 결측치 | `null` 사용, 빈 문자열/0으로 대체 금지 |
| 식별자 | 관리대상지는 `site_id`(내부 발급, PNU 기반), `pnu`(원본 19자리 코드) 둘 다 보존 |

### 4.2 모듈 호출 규약

모든 모듈은 Python 패키지로 구현하고 표준 진입점 함수 하나로 노출한다: `def run(input: dict) -> dict`

통합은 FastAPI 서버 하나(`api_server.py`)가 각 모듈을 import해서 순서대로 호출한다(REST로 쪼개지 않음 — 초기 복잡도를 낮추기 위함, Aquaguard/MOFOM 패턴 재사용).

`common/envelope.py`(envelope 생성 헬퍼)·`common/geo.py`(5179↔4326 변환, 외부 API 경계에서만 4326 사용)가 전 모듈이 공유하는 유틸리티다. 모듈은 `common`을 통해서만 좌표를 변환한다 — pyproj를 직접 import하지 않는다.

모든 모듈 출력은 공통 봉투(envelope) 형식을 따른다:

```json
{
  "status": "ok",
  "fallback_tier": 1,
  "data": {},
  "warnings": []
}
```

- `status`: `"ok"` | `"degraded"` | `"error"`
- `fallback_tier`: `1`=정상(예: Sentinel-2+Sentinel-1 융합), `2`=2순위 폴백(예: Sentinel-2만), `3`=3순위 폴백(예: 규칙기반 최소기능)
- 모듈은 예외를 던져서 죽지 않는다. 실패해도 `status: "degraded"` + 폴백값을 반환해야 Module O가 나머지를 보존한다(graceful degradation을 코드 레벨 계약으로 강제 — §0.5의 "AI가 실패해도 서비스가 작동하는 설계"를 구현하는 지점이 바로 여기)

### 4.3 폴백 계층

| 모듈 | 1순위 | 2순위 | 3순위 |
|---|---|---|---|
| CHG (변화탐지) | Sentinel-2 + Sentinel-1 융합 | Sentinel-2 단독 | 최근 유효 관측치 없음 → `status: "degraded"`, 이전 주기 값 유지 |
| RISK (위험도) | ML ranking(label 충분 시) | rule-based 가중합(§6) | 최소 feature만(면적·최근점검일)으로 산정, `warnings`에 명시 |
| AGENT | LLM tool-calling 설명 | 템플릿 기반 텍스트 생성 | 원자료(숫자·표)만 노출, 자연어 설명 생략 |

---

## 5. 모듈 계약 — 입출력 예시

### Module OBS — 관측 수집·전처리 (`module_obs`)

```jsonc
// input — aoi_geometry_4326은 GeoJSON geometry(EPSG:4326). site_geometry_5179를 가진 호출부는
// common.geo.geometry_5179_to_4326()으로 변환해서 넘긴다(외부 관측 API 경계에서만 4326 사용, §4.1)
{ "aoi_id": "YONGIN_YUBANG", "date_range": ["2026-06-01", "2026-08-25"],
  "aoi_geometry_4326": { "type": "Polygon", "coordinates": [] } }

// output (data) — composite_ref는 예약 필드, 현재 구현은 항상 null(§ 구현 상태 참조)
{ "aoi_id": "YONGIN_YUBANG", "scenes": [
    { "source": "sentinel2", "acquisition_date": "2026-08-20", "cloud_cover_pct": 8.2,
      "indices": { "ndvi_mean": 0.61, "ndmi_mean": 0.34 } }
  ],
  "composite_ref": null }
```

**폴백**: 구름 20% 이상인 장면은 자동 제외 후 최근 유효 장면으로 대체, `warnings`에 대체 사유 기록.

**구현 상태(2026-08-29, 실증 완료)**: `module_obs/run.py` — 원래 Sentinel Hub Statistical API로 구현했으나, 사용자가 이미 보유한 **Google Earth Engine**(`COPERNICUS/S2_SR_HARMONIZED`)으로 전환했다(CDSE도 검토했으나 GEE로 확정). `ee.ImageCollection.map()`으로 장면마다 SCL 기반 구름마스크·NDVI·NDMI를 서버 사이드에서 계산하고 `reduceRegion`으로 AOI 평균만 받는다 — 픽셀 래스터 전체를 로컬로 내려받지 않는다. `aggregate_array()`로 시계열 전체를 4번의 `getInfo()` 호출로 가져오므로 장면 수만큼 왕복하지 않는다. `GEE_PROJECT_ID`가 `.env`에 없거나 초기화가 실패하면 예외 대신 `status:"degraded", fallback_tier:3, data.scenes:[]`를 반환 — §0.5 "AI가 실패해도 서비스가 작동하는 설계"를 코드로 강제한 지점. **2026-08-30 정정**: 최초 구현은 Sentinel-2만 지원했으나(아래 원문 그대로 남겨둠), 이제 `sar_vv_mean`(Sentinel-1 IW/VV backscatter 기간평균, `_fetch_sar_vv_mean`)을 함께 반환한다 — 자세한 배경은 § Module CHG 구현 상태의 "SAR 융합 추가" 참조. `composite_ref`는 여전히 항상 `null`이다 — 대신 같은 목적(지도에 실제 위성영상을 얹는 것)을 별도 모듈 `module_obs/thumbnail.py`가 담당하게 됐다(§8 Before/After 구현 상태 참조). `composite_ref` 필드 자체를 채우는 대신 완전히 분리된 이유: Module OBS의 `run()`(시계열 통계 조회)과 썸네일 생성은 호출 빈도·비용 특성이 달라서(전자는 배치, 후자는 site 1건씩 on-demand) 같은 함수에 얹으면 배치 조회 성능(§12 B급)이 오염된다.

**유방동 AOI로 실제 검증됨** — `GEE_PROJECT_ID` 등록 후(Earth Engine API가 해당 Cloud 프로젝트에서 비활성 상태였던 걸 콘솔에서 활성화) 2026-06-01~08-25 구간에서 NDVI 0.51~0.58 수준의 실제 관측치를 받았다. **실증 중 발견·수정한 버그**: `CLOUDY_PIXEL_PERCENTAGE`는 Sentinel-2 타일(최대 110×110km) 전체 기준이라, 우리 AOI처럼 작은 영역은 타일 다른 곳의 구름 때문에 실제로는 맑은 장면도 걸러지는 문제가 실측으로 확인됐다. 그래서 타일 메타데이터 필터는 후보를 줄이는 넓은 예비필터(80%)로만 쓰고, 실제 채택 기준은 `reduceRegion`으로 계산한 **AOI 자체의 유효(비구름) 픽셀 비율**(`MIN_AOI_VALID_RATIO=0.5`)로 바꿨다. `pytest module_obs/tests/ -v`의 라이브 테스트(`test_live_fetch_returns_scenes_when_credentials_present`)가 실제 API 호출로 통과함을 확인 — `conftest.py`가 `.env`를 자동 로드해 pytest에서도 자격증명을 인식한다.

**배치 조회 추가(`module_obs/batch.py`, 2026-08-29, 사용자 지적 반영)**: "왜 유방동만 보는가"라는 실제 질문에 답하려고 여러 시/군/구로 확대하려니, `run()`(site 1개당 개별 `reduceRegion`+`aggregate_array` 4회 호출) 방식으로는 site가 늘어날수록 API 왕복이 site 수에 비례해 폭증해서 비현실적이었다. `run_batch(sites, date_range)`는 `Image.reduceRegions(collection=<여러 site의 FeatureCollection>)`를 이미지(관측 장면)마다 한 번만 호출하고 `.flatten()`으로 합쳐 **전체를 단일 `getInfo()` 호출**로 가져온다 — 왕복 횟수가 site 수가 아니라 이미지 수에만 비례한다. 실측: 5개 시/군/구·50필지를 기준기간·현재기간 각 1회씩, 총 2번의 배치 호출로 전부 처리(50필지를 개별 호출했다면 최대 400회 왕복이 필요했을 것). `pytest module_obs/tests/test_batch.py -v` 라이브 테스트로 2개 site 동시 조회 확인.

### Module CHG — 변화탐지 (`module_chg`)

```jsonc
// input — Module OBS의 output(composite 시계열)을 받음
{ "aoi_id": "YONGIN_YUBANG", "site_geometry_5179": { "type": "Polygon", "coordinates": [] },
  "baseline_period": ["2024-06-01", "2024-08-31"], "current_period": ["2026-06-01", "2026-08-31"] }

// output (data) — sar_vv_delta/sar_anomaly는 2026-08-30, changed_area_ratio_source는
// 2026-08-31 추가(아래 "SAR 융합 추가"·"요인 실측화" 참조)
{ "anomaly_score": 0.72, "changed_area_ratio": 0.18, "changed_area_ratio_source": "pixel_diff", // "pixel_diff" | "approximated"
  "change_type_hint": "vegetation_decline", // "vegetation_decline" | "moisture_increase" | "bare_ground_increase" | "no_significant_change" | "possible_change_sar_only"
  "source": "observed", "signal_variability": [0.61, 0.83], // 통계적 신뢰구간이 아니라 장면 간 흔들림 폭
  "evidence_confidence": { "level": "높음", "score": 6, "factors": [] }, // 증거 신뢰도(훼손 확률 아님)
  "sar_vv_delta": 2.5, "sar_anomaly": 0.833 }
```

`change_type_hint`는 원인 진단이 아니라 **"무엇이 달라졌는지"에 대한 힌트**일 뿐이다 — §3.4의 범위 제한 원칙(종 판독 금지)을 지킨다. 폴백: Sentinel-2+1 융합 → Sentinel-2 단독 → Sentinel-1 단독(§4.3, 2026-08-30부터 실제로 이 3단계가 다 구현됨).

**구현 상태(2026-08-29)**: `module_chg/run.py` — Module OBS를 baseline/current 두 번 호출해 NDVI/NDMI **scene 평균의 편차**로 `anomaly_score`를 계산한다. **중요한 근사**: 현재 `changed_area_ratio`는 진짜 픽셀 단위 변화면적이 아니라 이상도 크기로부터 근사한 값이다(§12 로드맵 B급 확장에서 Earth Engine `reduceRegion` histogram 기반 pixel-wise diff로 교체 예정) — Backtest A(§10)에서 이 근사가 실제와 얼마나 다른지 반드시 검증할 것. `python -m pytest module_chg/tests/ -v`로 mock 기반 단위 테스트(자격증명 불필요) 통과 확인됨.

**리팩터링(2026-08-29)**: 이상도 계산 로직을 `compute_change_from_scenes(baseline_scenes, current_scenes)` 순수 함수로 분리했다 — `run()`은 이 함수를 부르기 전에 Module OBS를 호출할 뿐이다. 배치 파이프라인(`scripts/run_priority_queue_batch.py`)이 `module_obs.batch.run_batch()`로 얻은 scene 리스트에 이 함수를 그대로 재사용해서, 분류 임계치·정규화 상수(`ANOMALY_THRESHOLD_FOR_CHANGE` 등)가 단일/배치 두 경로에서 따로 놀지 않는다.

**P2 구현 — 공간 군집화·경로·변화 이력(2026-08-31)**: 리서치가 P2로 분류한 세 가지를 모두 구현했다(주간보고서는 이미 구현돼 있었다).

- **공간 군집화 + 방문 순서**(`module_o/routing.py`, `GET /priority-queue/route`): 우선순위 큐만으로는 1위가 여주, 2위가 가평이면 점수 순서대로 움직이게 되는데, 그건 같은 인력으로 더 적게 보는 결과다. 서로 3km(초기 가정치) 안의 필지를 single-linkage로 묶고(밀도 기반 DBSCAN이 아니라 단순 연결로 충분한 이유는 목적이 "밀집 구역 탐지"가 아니라 "한 번에 갈 수 있는 묶음"이라서다), nearest-neighbor + 2-opt로 순서를 정한다. **군집 정렬은 거리가 아니라 그 안의 최우선 순위를 따른다** — 거리만 보면 한가한 군집을 먼저 가라고 말하게 된다. **핵심 지표는 군집 개수가 아니라 절감률**이다: 실측으로 상위 10곳 145.5km→122.0km(16.2%), 상위 20곳 415.1km→252.4km(**39.2%, 163km 절감**). 이 비교가 없으면 "묶었다"는 사실만 있고 왜 좋은지는 말할 수 없다. **한계를 데이터에 명시**: `distance_basis: "straight_line"` — EPSG:5179 평면 직선거리이지 실제 도로 주행거리가 아니다(산·강을 사이에 두면 크게 달라진다). UI가 이 값을 보고 "직선거리 기준" 문구를 띄우고, 지도 경로선도 점선으로 그려 실제 주행 경로가 아님을 시각적으로 구분한다.
- **변화 이력 타임라인**(`ui/components/SiteTimeline.tsx`): 과거 같은 계절 관측·현재기간 장면·현장점검 기록이 각각 다른 화면에 흩어져 있어 "이 필지가 어떻게 변해왔나"를 읽을 수 없었다. 하나의 시간축에 모으고 정상범위 이탈을 색으로 표시한다. 실측 예(양서면 대심리 47-16): 2023~2025년 같은 계절 NDVI가 0.685→0.723→0.738로 안정적이었는데 2026-06-05에 0.430으로 급락했다가 08-04에 0.639로 일부 회복 — 숫자 하나가 아니라 경과가 보인다.

**검증 전략 전환 — 영상 판독 라벨링 폐기(2026-08-31)**: 중간점검 리서치는 Silver-A(고해상도 Before/After 이중 판독)를 주력 검증법으로 권했고, 그에 맞춰 도구를 만들었다(`common/wayback.py`, `scripts/build_label_candidates.py` — Esri Wayback 시기별 서브미터 영상 + 층화추출 + 판독 HTML). 55개 필지 판독 자료까지 실제로 생성했다. **그런데 사용자가 "이건 현장에서 봐야 판독 가능하다"고 지적했고, 검증해보니 그 판단이 옳았다.**

0.5m급 영상으로 판별 **가능한** 것: 건물 신축/철거, 토공, 새 도로, 대규모 벌목. 판별 **불가능한** 것: 예초 vs 식생 소실, 자연 고사 vs 인위적 훼손, 덩굴(칡 등) 번성. **KECI가 실제로 관리하는 건 후자다.** 원 리서치가 "Sentinel-2로 '칡이 발생했다'를 직접 판독한다고 주장하면 안 된다"고 못박은 그 원칙이, 알고리즘뿐 아니라 **사람 판독자에게도 똑같이 적용된다**는 점을 처음엔 놓쳤다. 필지가 작아서(중앙값 883㎡)가 아니라 **판별 대상의 성격 때문에** 불가능하다.

**이건 실패가 아니라 설계 근거다.** 본 시스템의 핵심 명제 "위성은 확정하지 않는다, 현장이 확정한다"의 실증적 근거를 얻은 셈이다 — 제안서에서 "왜 AI가 판정하지 않나?"라는 질문에 대한 가장 강한 답이 된다(회피가 아니라 근거 있는 범위 설정).

**대체 검증 — `module_verify/ablation.py` + `GET /verify/ablation`**: 라벨 없이도 정직하게 말할 수 있는 것은 **정확도가 아니라 방법의 기여도**다. 같은 `compute_change_from_scenes()`를 계절 기준선 유무로 두 번 돌려 순위를 비교한다(값이 어긋날 수 없도록 실제 파이프라인과 동일 함수를 쓴다). **60개 site 실측 결과**: 두 기간 차분 방식의 상위 10위 중 **6건**이 과거 3년 같은 계절 정상 범위 안(|robust_z|<2)에 있는 필지였고 — 즉 계절 오탐 — 계절 기준선이 이들을 22~54위로 밀어냈다(기존 1·2·3·4위가 전부 여기 해당). 반대로 진짜 이상치 7건이 17~44위에서 2~10위로 올라왔다. 새 상위 10위의 정상범위 필지는 **0건**이다. 이 주장은 라벨이 필요 없다 — "과거 3년 같은 계절 범위 안에 있다"는 사실 자체가 근거이기 때문이다. 다만 이건 **정확도가 아니며**, Precision@K는 실제 현장점검 결과가 입력돼야 나온다(채점 엔진·화면은 이미 완성돼 있어 데이터만 들어오면 코드 수정 없이 산출된다).

**Wayback 영상의 용도 전환**: 라벨링용으로는 폐기했지만 **Evidence Card에 재활용했다**(`GET /sites/{id}/highres`, `ui/components/HighResHistory.tsx`). NDVI 썸네일은 Sentinel-2 10m라 필지가 3×3 픽셀이라 무엇이 달라졌는지 볼 수 없는데, Wayback 서브미터 영상은 건물·토공·나지화가 실제로 보인다 — 현장직원이 **출동 전에 "갈 만한가"를 판단**해 헛걸음을 줄이는 데 직접 쓰인다. 서버가 이미지를 합성하지 않고 타일 URL만 내려줘(site당 36회 왕복이 응답시간에 얹히지 않도록) 브라우저가 3×3으로 배치하고 필지 경계를 SVG로 얹는다. 시기 탐색 결과는 `data/processed/wayback_epochs.json`에 캐시해 커밋한다(지역당 75회 왕복이라 매번 조회하면 느리다).

**계절 정합 기준선(2026-08-31, 중간점검 리서치 P0)**: 변화탐지가 "기준기간(2024 여름) 평균 vs 현재기간(2026 여름) 평균" 단순 차분이라, *"작년 6월 녹음기와 올해 4월을 비교하면 NDVI가 떨어지는 게 당연하지 않나?"*라는 가장 흔한 공격을 막지 못했다. `module_obs/seasonal.py`가 **같은 계절(현재 관측일 ±20일)의 과거 3년**을 모아 median·MAD를 구하고, `module_chg.compute_seasonal_anomaly()`가 현재값의 robust z-score를 낸다 — 이제 "지난달보다 떨어졌다"가 아니라 **"지난 3년 같은 시기의 정상 범위를 N배 벗어났다"**고 말할 수 있다. BFAST/CCDC를 구현하지 않은 것은 의도적이다(리서치가 "한 달 기회비용이 너무 크고 Ground Truth 부재를 해결하지 못한다"고 명시 권고) — 그 문제의식인 계절성 통제만 경량으로 반영했다. 평균/표준편차가 아니라 median/MAD를 쓰는 이유는 과거 3년 중 한 해에 구름 낀 장면이 섞여도 기준선이 통째로 흔들리지 않기 때문이다.

**실측으로 조정한 값 — MAD 하한**: 용인 유방동 실측에서 동일계절 3년 NDVI가 0.820/0.838/0.847(MAD 0.009)로 **연간 변동이 매우 작게** 나왔다. 이걸 그대로 쓰면 0.05 변화도 3.7σ가 돼 대부분의 site가 최대점으로 포화되고 **우선순위 변별력이 사라진다**. 그래서 `MIN_MAD_FLOOR`를 단순한 0-나눗셈 방지값이 아니라 **센서 자체의 측정 노이즈**(Sentinel-2 NDVI는 대기보정·BRDF·관측각 차이로 대략 ±0.02~0.05 불확실)로 정의해 0.03으로 뒀다 — 그보다 미세한 차이를 "정상범위를 벗어났다"고 주장하면 과잉해석이다. **적용 효과(50개 site 실측)**: 전부 `season_matched`로 계산됐고 이상도 분포가 min 0.007 / median 0.382 / max 1.000(포화 4건)으로 변별력이 확보됐다. 등급도 **1순위 4건 / 2순위 18건 / 3순위 19건 / 정상 9건**(점수 17~86)이 되어, 재정규화만 했을 때(1순위 0건)보다 훨씬 실제 운영에 가까운 분포가 됐다. 계절 기준선 연도가 2년 미만이면 `compute_seasonal_anomaly()`가 None을 반환해 기존 두 기간 차분으로 자동 폴백하며, 어느 방식을 썼는지는 `anomaly_method`("season_matched" | "two_period_diff" | "sar_only")로 항상 표시한다.

**신뢰도 표기 정리(2026-08-31, 중간점검 리서치 P0 반영)**: `confidence_interval` → **`signal_variability`**로 이름을 바꾸고, 별도로 **`evidence_confidence`**(`module_chg/confidence.py`)를 신설했다. 기존 `confidence_interval`은 현재기간 scene 평균들의 표준편차를 anomaly score 주변에 배치한 값이라 통계적으로 calibration된 신뢰구간이 아니었다 — 이름을 그대로 두면 "95% CI인가? sampling distribution이 뭔가?"라는 질문에 답할 수 없다(리서치 §Red-Team). 새 `evidence_confidence`는 **"훼손될 확률"이 아니라 "지금 확보된 위성 증거를 얼마나 믿을 수 있는가"**만 나타내며, 단일 숫자가 아니라 `level`(높음/보통/낮음) + `factors`(± 사유 목록)를 함께 반환한다 — 화면에서 "구름은 어떻게 걸렀나", "SAR와 광학이 안 맞으면?" 같은 질문을 바로 확인할 수 있게 하기 위해서다. 판정 요소는 유효 장면 수·기준기간 장면 수·구름 비율·NDVI/NDMI 방향 일치·광학·SAR 센서 일치(가장 큰 가점 +2)·변화면적 실측 여부·강우 교란 가능성이다. **강우의 역할도 함께 바뀌었다**: 리서치가 지적한 대로 강우는 hazard이기도 하지만 NDMI·SAR 변화를 설명하는 confounder이기도 하므로, 습윤 신호(NDMI 증가 또는 SAR 감소)와 함께 나타나면 신뢰도를 깎는다. 실측 예: 여주시 양촌리 369-5는 다른 요소가 모두 가점인데 "최근 14일 127mm 강우 + 습윤 신호"로 -1이 붙어 근거가 화면에 그대로 노출된다.

**SAR 융합 추가(2026-08-30, 리서치 정합성 점검 반영)**: 원 리서치(수상전략 심층 리서치 PDF)를 다시 확인해보니 "Top 1 — 수변가드 AI"의 "핵심 기술"은 명시적으로 **"S1/S2 변화탐지"**였고, 5대 기술적 해자 1번이 "Multisensor Spatial-Temporal Fusion"이었다 — 그런데 최초 구현은 Sentinel-2(NDVI/NDMI)만 넣고 Sentinel-1 SAR를 빠뜨렸다(사용자가 "NDVI만으로 완성도가 있는가"를 되짚어보자고 지적해서 발견, 2026-08-30). 리서치는 이 신호가 왜 필요한지도 명시한다: "원격탐사 참가자의 흔한 결과는 NDVI 지도다" — 즉 NDVI/NDMI만으로는 딱 흔한 baseline에 머무른다는 뜻. `compute_change_from_scenes()`에 `baseline_sar_vv_mean`/`current_sar_vv_mean`(Module OBS의 `sar_vv_mean`, Sentinel-1 IW/VV backscatter dB) 파라미터를 추가했다. **역할을 두 가지로 제한**: (1) 광학 scene이 둘 다 있으면 SAR는 판정을 바꾸지 않고 `sar_vv_delta`/`sar_anomaly`(0~1 정규화, `SAR_VV_DELTA_NORMALIZATION_DB=3.0`)로 보조 근거만 얹는다 — `change_type_hint`는 여전히 NDVI/NDMI 기준. (2) 광학 scene이 구름 등으로 아예 없는데 SAR 평균은 둘 다 있으면(all-weather 특성), SAR 단독으로 `anomaly_score`를 근사하고 `change_type_hint="possible_change_sar_only"`, `source="observed_sar_fallback"`으로 표시해 낮은 신뢰도임을 숨기지 않는다. **의도적으로 안 한 것**: SAR backscatter 변화로 "식생/토양/구조물 중 무엇이 바뀌었는지" 판독하지 않는다 — 그건 리서치의 "매우 중요한 범위 제한"이 명시적으로 경고한 과잉해석이다. `module_obs/run.py`(단일 site, `reduceRegion`)와 `module_obs/batch.py`(다중 site, `reduceRegions`)에 각각 SAR 조회를 추가했는데, **실측으로 발견한 함정**: 단일 밴드("VV") 이미지를 `reduceRegions`로 여러 site에 한 번에 돌리면 출력 컬럼명이 밴드명이 아니라 reducer 기본 출력명인 `"mean"`이 된다(다중 밴드였던 NDVI/NDMI 배치 조회와 다름) — 처음엔 `"VV"`로 읽어서 50개 site 전부 `sar_vv_delta:null`이 나왔고, 실제 site 하나로 직접 `getInfo()` 결과를 찍어봐서 원인을 찾았다. `pytest module_chg/tests/ -v`에 SAR 단독/병행 케이스 테스트 추가, `data/processed/hanriver_priority_queue.geojson`·`yongin_yubang_priority_queue.geojson` 60개 site 전부 재생성해 실제 SAR 값(`sar_vv_delta` 대략 -5.4~+3.7dB)이 반영됨을 확인.

### Module AGG — GIS 공간 집계 (`module_agg`)

```jsonc
// input — Module CHG 출력을 관리대상지 단위로 묶음
{ "site_id": "A1037", "pnu": "4146110500100780003",
  "chg_results": [ { "anomaly_score": 0.72, "changed_area_ratio": 0.18, "sar_anomaly": 0.4 } ],
  "site_attributes": { "restoration_elapsed_days": 420, "last_inspection_days_ago": 63,
    "adjacent_to_water": true, "past_anomaly_count": 1, "recent_rainfall_mm": 20.0 } }

// output (data)
{ "site_id": "A1037", "features": {
    "anomaly_score_mean": 0.72, "changed_area_ratio": 0.18, "sar_anomaly_mean": 0.4,
    "adjacent_to_water": true, "restoration_elapsed_days": 420,
    "last_inspection_days_ago": 63, "past_anomaly_count": 1, "recent_rainfall_mm": 20.0 } }
```

**구현 상태(2026-08-29)**: `module_agg/run.py` — Module CHG 결과(들)를 평균해 `anomaly_score_mean`/`changed_area_ratio`를 만들고, `site_attributes`는 그대로 통과시킨다. **중요한 제약**: `site_attributes`(복원경과일·최근점검일·인접수계여부·과거이상이력)는 KECI 내부 자산 DB에서 와야 하는데 이 프로토타입은 접근권한이 없다(개발_핸드오프_브리프 §2). 현재는 호출부가 채울 수 있는 값만 채우고 나머지는 `null`로 둔다 — Module RISK가 `null`을 "0 기여"로 안전하게 처리한다(아래 참조). `pytest module_agg/tests/ -v` 통과.

**요인 추가(2026-08-30)**: `sar_anomaly_mean`(Module CHG의 `sar_anomaly` 평균 — § Module CHG "SAR 융합 추가" 참조)과 `recent_rainfall_mm`(`site_attributes`로 통과, 호출부가 `common/weather.py`로 채움)을 추가했다. 원 리서치의 Top1 개념 설명이 "대상지 속성·**최근 기상**·과거 점검결과를 결합해... 위험도를 산정한다"라고 명시했는데 최초 구현엔 기상 요인이 아예 없었다 — `recent_rainfall_mm`도 이 SITE_ATTRIBUTE_KEYS 목록에 추가해서 같은 결측 처리 원칙(없으면 0 기여)을 그대로 적용한다.

### Module RISK — 위험도 산정 (`module_risk`)

> **방법론 확정**: 처음부터 DNN을 쓰지 않는다. 1단계는 **규칙+통계 이상탐지**(explainable, label 불필요), label이 충분히 쌓이면 2단계로 **LightGBM/XGBoost ranking**을 얹는다(§6). 공모전에서 DNN을 억지로 넣는 것은 오히려 감점 요소가 될 수 있다.

```jsonc
// input — Module AGG의 features를 받음
{ "site_id": "A1037", "features": {
    "anomaly_score_mean": 0.72, "changed_area_ratio": 0.18, "sar_anomaly_mean": 0.4,
    "adjacent_to_water": true, "restoration_elapsed_days": 420,
    "last_inspection_days_ago": 63, "past_anomaly_count": 1, "recent_rainfall_mm": 20.0 } }

// output (data) — inspection_priority_score가 최종 output. 아래는 module_risk/run.py 실제 실행 결과
// (2026-08-31 재검증, contracts/module_risk.example.json과 동일). 이 값은 "훼손 확률"이 아니라
// 운영상 ranking이다 — 아래 "명칭 정리" 참조.
{ "site_id": "A1037", "inspection_priority_score": 50, "priority_tier": "2순위",
  // priority_tier ∈ {"1순위"(>=70),"2순위"(>=50),"3순위"(>=30),"정상"}. "rank"(대기열 순번, §Module O)와는 별개 개념
  "contributing_factors": [
    { "factor": "anomaly_score_mean", "value": 0.72, "weight": 0.30 },
    { "factor": "changed_area_ratio", "value": 0.18, "weight": 0.15 },
    { "factor": "last_inspection_days_ago", "value": 63, "weight": 0.15 },
    { "factor": "sar_anomaly_mean", "value": 0.4, "weight": 0.10 },
    { "factor": "recent_rainfall_mm", "value": 20.0, "weight": 0.10 },
    { "factor": "adjacent_to_water", "value": true, "weight": 0.10 },
    { "factor": "past_anomaly_count", "value": 1, "weight": 0.10 }
  ],
  "weight_coverage": 1.0, // 전체 가중치 중 실제로 확보된 근거의 비율(결측 재정규화 투명성, 아래 참조)
  "model_version": "rule_v1", "source": "rule_based" } // "rule_based" | "ml_ranking"
```

`inspection_priority_score` 산출식(1단계, rule baseline, 2026-08-30 재조정):

```
inspection_priority_score = 100 × clip(
  0.30 × anomaly_score_mean
  + 0.15 × changed_area_ratio
  + 0.10 × sar_anomaly_mean            // 2026-08-30 추가 — 광학 이상도의 보조 근거(§Module CHG)
  + 0.10 × min(recent_rainfall_mm / 50, 1.0)  // 2026-08-30 추가 — "최근 기상" 요인(common/weather.py)
  + 0.15 × min(last_inspection_days_ago / 180, 1.0)
  + 0.10 × adjacent_to_water(0|1)
  + 0.10 × min(past_anomaly_count / 3, 1.0)
, 0, 1) ÷ weight_coverage   // ← 결측 요인의 가중치를 뺀 나머지로 재정규화(2026-08-31, 아래 참조)
```

가중치는 초기 가정값 — Backtest B(§10)에서 실제 이상사례 기준으로 보정한다. `contributing_factors`는 Module AGENT가 "왜 1순위인가"를 설명할 때 그대로 인용하는 근거 데이터다(숫자를 만들지 않고 tool output을 읽는 원칙, §0.4).

**구현 상태(2026-08-29, 2026-08-31 갱신)**: `module_risk/run.py` — 위 산출식을 그대로 구현. `features`의 특정 항목이 `null`이면(§ Module AGG의 KECI 내부 데이터 접근 제약 참조) 해당 가중항을 빼고 **남은 가중치로 재정규화**하며, `status:"degraded"` + `weight_coverage`로 "이 점수는 일부 요인 없이 계산됐다"는 사실을 숨기지 않는다. `priority_tier` 경계값은 70/50/30(§ 위 주석)으로 확정.

**명칭 정리·재정규화 수정(2026-08-31, 중간점검 리서치 P0 반영)**:
- **`risk_score` → `inspection_priority_score`, `risk_tier` → `priority_tier`**: 이 값은 환경피해 발생확률로 calibration된 게 아니라 0~100으로 정규화된 운영상 ranking이다. "위험도 82점"이라 부르면 심사에서 "82점이면 82% 위험인가?"라는 질문에 통계적으로 답해야 하는데 답할 근거가 없다(리서치 §Red-Team). "점검 우선순위 82점"은 ranking임이 자명해 방어된다. 상태머신 단계명도 `위험도산정` → `우선순위산정`으로 함께 바꿨다.
- **결측 요인 재정규화(실제 버그 수정)**: 예전에는 결측 요인의 가중치를 그냥 빼먹고 더해서, KECI 내부 DB 접근이 안 되는 필지가 실제 상태와 무관하게 구조적으로 낮은 점수를 받았다. **실측으로 확인한 영향**: 결측 3개(복원경과일·최근점검일·과거이상이력)인 우리 60개 site는 4개 요인이 전부 만점이어도 65점이 천장이라 **1순위(≥70)가 구조적으로 불가능**했다 — 실제 분포도 1순위 0건 / 2순위 1건 / 3순위 15건 / 정상 44건(최고 50점)으로, "먼저 가볼 곳"을 알려주는 서비스인데 최상위 등급이 비어 있었다. 재정규화 후 같은 데이터에서 **2순위 8건 / 3순위 29건 / 정상 23건(최고 67점)**으로 분포가 정상화됐다. 여전히 1순위 0건인 것은 이제 구조적 한계가 아니라 "실제로 70점을 넘는 필지가 없다"는 정직한 결과다 — 임계값을 낮춰 1순위를 인위적으로 만들지 않았다.

**가중치 재조정(2026-08-30, 리서치 정합성 점검 반영)**: 원 리서치를 다시 확인해 SAR(`sar_anomaly_mean`)과 최근 강우(`recent_rainfall_mm`) 요인을 추가하면서(§ Module CHG·AGG "추가" 참조), 기존 5개 요인 합 1.0을 유지하려고 전체 가중치를 재분배했다: `anomaly_score_mean` 0.35→0.30, `changed_area_ratio` 0.20→0.15, `adjacent_to_water`·`past_anomaly_count` 각 0.15→0.10, `last_inspection_days_ago`는 0.15 유지, 새 요인 둘은 각 0.10. 광학 이상도(`anomaly_score_mean`)를 여전히 가장 큰 비중으로 남긴 이유는, 리서치의 방어 논리 자체가 "판정의 중심은 광학, SAR는 보조 근거"라는 데 있기 때문이다(SAR로 변화 종류까지 판독하려 들면 리서치가 경고한 과잉해석이 된다). `pytest module_risk/tests/ -v`의 A1037 회귀 테스트를 새 가중치·새 요인 기준으로 갱신(54점→51점) — 가중치를 다시 바꾸면 이 테스트도 함께 갱신할 것.

### Module O — 오케스트레이션 (`module_o`)

**역할**: 전체 AOI의 Module RISK 결과를 모아 Top-N 우선순위 큐를 생성하고, 담당자 의사결정을 위한 상태를 관리한다.

```jsonc
// output (data)
{ "week_of": "2026-09-01", "priority_queue": [
    { "rank": 1, "site_id": "A1037", "inspection_priority_score": 54, "status": "미점검" }
  ],
  "queue_size": 12, "generated_at": "2026-09-01T09:00:00+09:00" }
```

**상태머신**(대상지 단위): `관측 → 변화탐지 → 집계 → 우선순위산정 → 우선순위큐등록 → 현장점검등록 → 결과입력 → 검증완료`. 담당자 승인 게이트는 없다(재난 대응형 시스템이 아니므로 human-in-the-loop이 이미 "현장점검을 실제로 갈지 말지" 판단 자체에 있음 — Aquaguard의 관공서 모드 승인 게이트 같은 별도 장치 불필요).

**구현 상태(2026-08-29)**: `module_o/run.py` + `module_o/store.py` — Module RISK 결과를 받아 정렬·순번 부여만 한다(위험도 계산은 하지 않음, §0.4). `SiteStateStore`는 프로세스 인메모리 dict(Aquaguard의 `AlertStore` 패턴)로 8단계 상태를 추적하지만, **현장점검이 들어와도 "검증완료"로 자동 전이시키지 않는다** — Module VERIFY가 아직 없어서 검증됐다고 주장하면 거짓이 되기 때문(§ Module FIELD 구현 상태 참조). 대신 "결과입력" 단계에 머문다. `pytest module_o/tests/ -v` 통과.

### Module FIELD — 현장 피드백 (`module_field`)

```jsonc
// input
{ "site_id": "A1037", "inspector_id": "staff_003",
  "inspected_at": "2026-09-02T10:15:00+09:00",
  "actual_anomaly_found": true,
  "anomaly_category": "식생교란", // "식생교란" | "침수흔적" | "불법이용" | "이상없음" | "기타"
  "photo_refs": ["field/A1037/2026-09-02_01.jpg"], "note": "동측 사면 나지 노출 확인" }

// output (data)
{ "site_id": "A1037", "inspection_id": "INSP-20260902-A1037", "status": "완료" }
```

**구현 상태(2026-08-29)**: `module_field/run.py` — 입력 검증과 `inspection_id` 발급만 한다. 상태 저장(결과입력 단계로 전이)은 이 모듈이 아니라 호출부(`api_server.py`)가 `module_o.store.record_inspection()`을 별도로 호출해서 한다 — Module FIELD는 "무엇을 기록할지 검증"만, Module O는 "상태를 어떻게 바꿀지"만 책임지는 경계를 유지한다. `pytest module_field/tests/ -v` 통과.

### Module VERIFY — 검증/Backtest 엔진 (`module_verify`)

> Aquaguard의 Module V(검증 엔진)와 동일한 이유로 존재한다 — "예측 정확도는 어디 있습니까?"라는 심사질문에 답할 화면 자체가 이 모듈 없이는 없다. Module RISK와 **동급 우선순위**.

```jsonc
// input — Module RISK의 과거 예측과 Module FIELD의 실제 현장결과를 매칭.
// baseline_predictions는 선택 — Module VERIFY는 "recency"/"ndvi_threshold"가 무엇인지 모른다(구현 상태 참조),
// 호출부가 이미 계산한 대체 랭킹 점수만 넘겨받아 채점한다. predicted_at/inspected_at도 선택(leakage 검사용).
{ "period": ["2026-09-01", "2026-09-30"], "k": 10,
  "predictions": [ { "site_id": "A1037", "inspection_priority_score": 54, "predicted_at": "2026-09-01" } ],
  "field_results": [ { "site_id": "A1037", "actual_anomaly_found": true, "inspected_at": "2026-09-05" } ],
  "baseline_predictions": { "ndvi_threshold": [ { "site_id": "A1037", "score": 0.3 } ] } }

// output (data) — random은 항상 자동 계산(라벨 중 양성 비율), 나머지는 baseline_predictions에 있는 것만
{ "precision_at_k": { "k": 10, "value": 0.7 },
  "recall_at_top20pct": 0.65,
  "labeled_site_count": 20, "positive_count": 6,
  "baseline_comparison": [
    { "baseline": "random", "precision_at_k": 0.3 },
    { "baseline": "ndvi_threshold", "precision_at_k": 0.5 },
    { "baseline": "proposed", "precision_at_k": 0.7 }
  ] }
```

**엄격히 지킬 것 — data leakage 금지**: `field_results`는 반드시 예측 시점 **이후**에 확보된 값이어야 하고, `predictions`는 그 예측 시점 이전 데이터로만 재실행한 결과여야 한다(§10 Backtest 절차 참조). 섞으면 "검증"이 아니라 "사후 끼워맞추기"가 된다.

**구현 상태(2026-08-29)**: `module_verify/run.py` — Precision@K·Recall@Top20%·baseline 비교를 실제로 계산한다. **경계 설계**: 이 모듈은 "recency"·"ndvi_threshold" 같은 baseline을 스스로 계산하지 않는다 — GIS/NDVI 도메인 지식이 필요한 부분은 호출부 책임이고, Module VERIFY는 이미 계산된 랭킹을 채점만 한다("위험도를 계산하지 않는다"는 §0.4 경계 원칙을 검증에도 동일하게 적용). `random` baseline만 분석적으로 자동 계산(기대 정밀도 = 라벨 중 양성 비율). **leakage 가드가 실제로 동작**: `predicted_at`/`inspected_at`이 둘 다 있고 `inspected_at <= predicted_at`이면 `status:"degraded"` + 경고 문자열로 표시(§10 원칙을 말로만 안 하고 코드로 확인). `api_server.py`의 `GET /verify/backtest`가 이 모듈을 감싸는데, **아직 진짜 leakage-free backtest는 아니다** — 과거 특정 시점의 예측을 재현하는 게 아니라 store에 있는 "현재" risk_score를 predictions로 그대로 쓴다(예측 스냅샷 시계열 저장 인프라가 없음, §12 TODO). `pytest module_verify/tests/ -v` 7개 통과.

### Module AGENT — Evidence Agent (`module_agent`)

```
User
 ↓
Evidence Agent
 ├─ GIS Query Tool        (site_id → 속성)
 ├─ Time-Series Query Tool (site_id → OBS/CHG 시계열)
 ├─ Risk Result Tool       (site_id → RISK 결과·contributing_factors)
 ├─ Field Inspection DB    (site_id → 과거 점검이력)
 └─ Report Generator       (주간 Top-N → 1페이지 요약)
```

질문 예: "왜 A1037이 이번 주 1위야?" → Agent는 Risk Result Tool의 `contributing_factors`를 그대로 읽어 문장으로 풀어낸다 — **LLM은 숫자를 만들지 않는다.** 예시 응답: "최근 20일 식생지표가 계절평균 대비 크게 감소했고(anomaly_score 0.72), 변화면적이 대상지의 18%이며, 마지막 현장확인은 63일 전입니다. 따라서 위험점수 54점(2순위)으로 이번 주 우선순위 1위입니다." (대기열 순번 "1위"와 위험도 등급 "1순위"는 다른 개념이다 — 최고점 대상지라도 등급은 2순위일 수 있다.)

폴백은 §4.3 참조.

**구현 상태(2026-08-29)**: `module_agent/`(Gemini function calling, 모델은 `GEMINI_MODEL` 환경변수로 지정 — 기본값 `gemini-3.6-flash`). `run.py`는 위 다이어그램의 Risk Result Tool/Time-Series Query Tool/Field Inspection DB 세 개를 구현했다(GIS Query Tool은 별도 지리 조회가 필요 없어 생략 — site 속성은 이미 Risk Result Tool에 포함). **중요한 설계**: tool 함수는 `site_id`를 인자로 받지 않는다 — API가 요청의 `site_id`에 고정된 클로저를 매번 새로 만들어 모델에 넘긴다. 모델이 엉뚱한 site_id를 지어내 다른 대상지 정보를 조회하는 경로 자체를 차단하기 위해서다. `report.py`가 Report Generator를 구현(§7 `POST /reports/weekly`). `GEMINI_API_KEY`가 없거나 API 호출이 실패하면 예외 대신 템플릿 폴백(§4.3)으로 전환 — `pytest module_agent/tests/ -v` 13개가 전부 mock으로 통과.

**실제 Gemini로 실증 완료(2026-08-29)**: `gemini-3.6-flash` 모델로 Q&A·주간보고서 둘 다 실제 호출해 확인. 예시 응답: "해당 대상지(A1037)는 위험 점수 54점으로 2순위 관리 대상에 포함되었습니다. 주요 근거 요인으로는 평균 이상 점수가 0.72로 높게 측정되었으며..." — `tools_used: ["get_risk_evidence"]`로 실제 tool 호출이 확인되고, 답변이 tool이 반환한 숫자(54, 2순위, 0.72)를 정확히 인용함(지어낸 숫자 없음). 알려진 사소한 이슈: SDK가 `Models.generate_content`에서의 automatic function calling 사용에 대해 "`Chat.send_message`를 대신 쓰라"는 안내성 경고를 콘솔에 출력한다 — 기능에는 영향 없음, 필요시 §12 B급 확장에서 Chat 기반으로 리팩터링 가능.

---

## 6. AI 모델 전략

**두 단계 구조**(Aquaguard와 동일 원칙 — physics/rule baseline 없이 AI surrogate부터 만들지 않는다):

1. **1단계 — 규칙+통계 이상탐지**(§5 Module RISK의 `inspection_priority_score` 산출식). 설명 가능하고 label 없이도 작동한다. **공모전 프로토타입의 기본값.**
2. **2단계 — LightGBM/XGBoost ranking**. Module FIELD로 현장점검 label이 충분히 쌓이면(§12 로드맵 B급) 붙인다. 입력: AGG의 features 전체. 목표: `field_verification_required = 1/0` 또는 `maintenance_priority` ranking.

DNN segmentation은 고해상도 영상과 충분한 label이 있을 때만 후속 고도화로 검토한다(MVP 범위 밖).

---

## 7. API 설계 (프로토타입 범위)

```
GET  /sites
GET  /sites/{site_id}
GET  /sites/{site_id}/timeseries
GET  /priority-queue?week_of=...
GET  /sites/{site_id}/evidence
GET  /sites/{site_id}/thumbnails     -- §7 원안에 없던 추가: 선택 대상지의 NDVI Before/After 이미지(on-demand, §8)
POST /inspections
GET  /verify/backtest?period=...&k=10
POST /reports/weekly
POST /sites/{site_id}/ask            -- §7 원안에 없던 추가: Module AGENT Q&A(§5)를 실제로 쓰려면 필요했음
```

**구현 상태(2026-08-29)**: `api_server.py` — 위 목록 전부 구현·테스트 완료(`tests/test_api_server.py`, FastAPI `TestClient` 사용, GEE/Gemini 자격증명 불필요 — 둘 다 없으면 각 모듈이 자체 폴백으로 응답). 서버 시작 시 스냅샷들(Module RISK 조기 실증 결과, §5 Module RISK)을 읽어 Module O의 인메모리 store를 채운다 — 매 요청마다 Earth Engine을 다시 부르지 않는다(§2.2 배치 모드 원칙). `/verify/backtest`는 store의 현재 inspection_priority_score + 등록된 현장점검 이력을 Module VERIFY로 채점한다 — 진짜 leakage-free backtest는 아직 아니다(§5 Module VERIFY 구현 상태 참조). `/sites/{site_id}/ask`·`/reports/weekly`는 Module AGENT를 감싼다 — `GEMINI_API_KEY`가 없으면 템플릿 폴백 응답을 그대로 반환한다(200 OK, `status:"degraded"`). `/sites/{site_id}/thumbnails`만 예외적으로 Earth Engine을 실시간으로 부른다(선택된 site 1건에 한해서만, §5 Module OBS 구현 상태 참조) — 나머지 엔드포인트는 전부 사전 계산된 스냅샷만 읽는다.

---

## 8. UI·대시보드 설계

첫 화면은 "예쁜 환경대시보드"가 아니라 **업무화면**처럼 보여야 한다. 핵심 위젯 6개면 충분하다.

| 화면 | 보여줄 것 |
|---|---|
| Map | 관리구역 + 위험도 색상 |
| Priority Queue | 이번 주 확인할 Top-N |
| Before/After | 최근 정상시기 vs 이상시기 위성영상 |
| Time Series | 식생·수분·SAR 변화 그래프 |
| Evidence Card | 왜 위험한가(contributing_factors) |
| Inspection | 현장결과 입력·완료 처리 |

메인 KPI: `전체 대상지 / 고위험 대상지 / 미점검 고위험 / 이번주 점검완료 / 실제 이상확인 / Precision@K`

**구현 상태(2026-08-29)**: `ui/`(Next.js + MapLibre GL JS)가 6개 중 5개를 구현했다 — Map, Priority Queue, **Before/After**, Time Series, Evidence Card, Inspection. **Time Series**는 SAR 없이 NDVI만 순수 SVG 스파크라인으로 표시 중(외부 차트 라이브러리 없음, `components/TimeSeriesChart.tsx`). 메인 KPI 중 `Precision@K`는 Module VERIFY가 구현됐지만 UI에는 아직 노출하지 않았다(백테스트는 `/verify/backtest`로만 조회 가능, §12 TODO — **2026-08-30 해소, 아래 참조**). 실제 브라우저에서 지도 클릭 → Evidence Card → 현장점검 등록 → Priority Queue 상태 갱신까지 end-to-end로 확인됨.

**Before/After 완료(2026-08-29, 사용자 지적 반영)**: "왜 위성지도인가"라는 질문에 답하기 위해 `module_obs/thumbnail.py`(Earth Engine `getThumbURL()`)로 실제 NDVI 컬러 이미지를 만들어 (1) Evidence Card에 기준기간·현재기간 나란히, (2) 선택된 대상지 위치에 지도 위 실제 좌표로 겹쳐서 보여준다(`components/NdviThumbnails.tsx`, `MapView.tsx`의 `ndvi-overlay` image source). 60개 전부를 미리 만들지 않고 선택한 site 1건만 그때 생성한다(§7 `GET /sites/{id}/thumbnails`, on-demand) — 배치 조회(§12 B급)의 이점을 스스로 깎아먹지 않기 위해서다. 실제 확인: 여주시 대신면 양촌리 369-5 필지에서 2024-06-10/2026-06-15 두 장의 실제 위성 이미지(각 6.4KB PNG)를 받아 브라우저에서 렌더링 확인.

**버그 발견·수정(2026-08-29)**: 사용자가 "왼쪽 리스트에서 클릭하면 지도가 그 위치로 이동해야 한다"고 요청해서 재현했더니, 실제로 **지도가 전혀 움직이지 않는 버그**가 있었다. 원인: `MapView.tsx`의 두 effect가 전부 `if (map.isStyleLoaded()) X(); else map.once("load", X);` 패턴을 썼는데, 이 샌드박스 환경에서는 래스터 베이스맵 타일이 끝까지 로드되지 않아 `isStyleLoaded()`가 계속 `false`를 반환했다. 그러면 매번 `map.once("load", ...)`로 다시 구독하는데, `"load"`는 1회성 이벤트라 맵 생성 시 이미 한 번 발생한 뒤로는 다시 오지 않는다 — 그래서 대상지를 선택해도 콜백이 영원히 실행 안 됐다. **수정**: `isStyleLoaded()` 대신 `map.getSource("sites")`/`map.getSource("ndvi-overlay")`가 이미 존재하는지(= `"load"` 핸들러가 이미 실행됐는지)로 판단하도록 바꿨다 — 존재하면 즉시 실행, 없으면만 `"load"`를 기다린다. `window.__debugMap` 임시 훅으로 `map.getCenter()`/`getZoom()`/소스 좌표를 직접 찍어 수정 전후를 실측 비교해 확인했다(수정 전: 클릭해도 카메라 고정, overlay 좌표가 placeholder인 채 그대로. 수정 후: 여러 site를 연속 선택해도 매번 정확한 필지 위치로 확대되고 NDVI 오버레이 좌표가 실제 bbox로 갱신됨). 이 버그는 처음 커밋했을 때부터 있었다 — 그 세션에서는 데이터 흐름(네트워크 요청 성공, 이미지 렌더링)만 확인하고 지도 카메라의 실제 이동은 확인하지 않아서 놓쳤다.

**추가 UX 정리(2026-08-29~30, 사용자 지적 반영)**:
- **"Map data not yet available" 깜빡임**: Esri World Imagery 타일을 직접 떠서 확인해보니 시골 지역(용인/여주/가평 등)은 zoom 19부터 실제 이미지 없이 저 placeholder를 그대로 반환한다(실측 확인). 대상지 확대 애니메이션 중 순간적으로 그 줌에 걸려서 생긴 문제였다 — `esri` 래스터 소스에 `maxzoom: 18` 캡을 걸어서, 그 이상은 z18 타일을 확대(overzoom)해 쓰게 했다.
- **위성 이미지 로딩 표시**: NDVI 오버레이 fetch 중에는 지도 위에 "위성 이미지 불러오는 중..." 배너를 띄운다(§ Earth Engine 응답이 보통 3~7초 걸림, 오류로 오해하지 않도록) — `overlayReadySiteId` 상태를 selectedSiteId와 비교해 파생시키는 방식이라 effect 본문에서 동기 setState를 안 쓴다.
- **Priority Queue 행정동 그룹핑**: 60개 site 플랫 리스트가 안 읽혀서, 각 site의 `addr`(PNU 기반, 예: "경기도 여주시 대신면 양촌리 369-5")에서 "시군구 읍면동"만 뽑아 그룹 헤더로 묶었다(`PriorityQueueList.tsx`의 `parseDong()`) — 별도 shapefile 조인 없이 이미 있는 주소 문자열만으로 충분했다. 그룹 순서는 원래 순위(rank) 순서를 그대로 따라가므로 가장 급한 동이 자연히 맨 위에 온다.
- **행정동 경계 배경 레이어(데이터만 보존, 지도 통합은 보류)**: "대상지 폴리곤이 배경 없이 사각형처럼 보인다"는 지적에 대해, 실은 NDVI 썸네일의 bounding box일 뿐이라고 설명했지만, 사용자가 전국 읍면동 경계 shapefile(`BND_ADM_DONG_PG`, EPSG:5186, 필드 ADM_CD/ADM_NM/BASE_DATE만 존재)을 제공해서 실제 시각적 맥락까지 추가하려 했다. `scripts/build_admin_dong_boundaries.py`가 대상지 60건의 경계상자(+5km 버퍼)와 교차하는 읍면동만 골라(3559건→144건) `ui/public/admin_dong_boundaries.geojson`으로 저장한다(0.0001도 단순화로 6MB→1.4MB) — 이 스크립트와 파일은 그대로 남아있다. **하지만 `MapView.tsx`에 실제로 붙이는 건 뺐다** — 이 선이 화면에 안 보인다는 조사가 아래 "MapLibre GL v6 벡터 레이어 렌더링 회귀" 버그 발견으로 이어졌고, 그 버그 자체가 admin-dong과 무관하게 sites-fill 등 다른 벡터 레이어에도 이미 있었다는 게 밝혀지면서 admin-dong 통합은 우선순위가 낮아졌다. 필요해지면 저장된 GeoJSON을 `MapView.tsx`에 GeoJSON 소스+line 레이어로 다시 붙이기만 하면 된다.
- **Evidence Agent 채팅 위젯으로 재설계**: 사이드 패널에 고정 박혀있던 "Evidence Agent에게 물어보기"를 빼고, 화면 우하단 원형 AI 버튼을 누르면 펼쳐지는 채팅창(`AgentChatWidget.tsx`)으로 바꿨다(참고 스크린샷의 Aqua Guard.AI 패턴). 대상지를 바꾸면 `key={siteId}`로 채팅 스레드가 통째로 리마운트돼 새 대화로 초기화된다. 답변은 `TypewriterText.tsx`(공용 컴포넌트, 주간보고서와 공유)로 한 글자씩 흘려보낸다. Module AGENT의 시스템 프롬프트 답변 길이 한도도 "3문장 이내"→"6문장 이내"로 완화했다(`module_agent/run.py`).
- **성과 검증(Backtest)·주간보고서 화면 추가**: 백엔드에만 있던 `GET /verify/backtest`, `POST /reports/weekly`를 각각 모달로 노출했다(`BacktestModal.tsx`, `WeeklyReportModal.tsx`, 헤더의 "성과 검증"/"주간보고서" 버튼). Backtest 모달은 Precision@K·Recall@Top20%·baseline 비교표·leakage 경고를 그대로 보여준다 — "예측 정확도는 어디 있나"라는 심사질문에 답할 화면이 이제 실제로 존재한다.
- **필지 고정 크기 마커 추가**: 대상지 폴리곤이 수백 m²라, 한강유역 6개 시/군/구를 한 화면에 담는 줌에서는 진짜 모양(`sites-fill`)이 화면에 몇 픽셀도 안 나온다는 사용자 지적("색깔 필지가 안 보인다") — 줌과 무관하게 항상 일정 크기(선택 시 10px, 평시 6px)로 보이는 `circle` 레이어를 대상지 centroid 위치에 별도로 얹었다(`sites-markers` 레이어, `sites-points` 소스). `circle` 레이어는 Point/MultiPoint geometry만 그리고 Polygon 피처는 조용히 무시하므로, 기존 `sites`(Polygon) 소스에 그대로 얹을 수 없어 Point 전용 소스를 새로 만들고 `approxCentroid()`(꼭짓점 평균, turf 없이 계산)로 좌표를 구했다. 클릭·hover 핸들러도 `sites-fill`과 `sites-markers` 양쪽에 다 걸었다.

**버그 발견·수정(2026-08-30) — MapLibre GL v6.6.0 벡터 레이어 렌더링 회귀**: 위 마커를 추가했는데도 "여전히 안 보인다"는 신고가 이어졌다. 원인 조사 과정(아래)에서 이 프로젝트 최대 규모의 버그를 찾았다:

1. 처음엔 `map.on("load", ...)`가 이 환경에서 전혀 안 오는 걸로 보였다(진단 배지로 확인) — "load"/"idle"/"styledata" 3중 이벤트 + `isStyleLoaded()` 가드 + 1초 폴링까지 다 걸어 자가복구하도록 `setupLayers()`를 재작성했다(`waitForSource()` 헬퍼도 같은 이유로 도입 — `map.once("load", cb)`는 "load"가 이미 소비된 뒤엔 다시 안 온다는, §5 Module UI-3D 위 항목과 동일 계열의 함정).
2. 그렇게 고친 뒤에도 색깔 필지가 안 보였다. 브라우저 콘솔에서 `"sitesDebug is not defined"` 크래시를 발견 — 이미 지운 변수를 낡은 Turbopack HMR 빌드가 계속 참조하고 있었다(`.next` 캐시 삭제 + 완전히 새 탭으로 해결).
3. 크래시를 고친 뒤에도 안 보였다. **진짜 원인**: `queryRenderedFeatures()`/`querySourceFeatures()`/`canvas.toDataURL()` 등 모든 JS 레벨 진단이 실제 화면 상태와 안 맞는(값이 다 0이거나 빈 캔버스인) 환경에서, 실제 스크린샷(`computer` 도구)만이 신뢰할 수 있는 근거였다 — 반경 30px 새빨간 원을 화면 정중앙에 강제로 찍어도 전혀 안 보였다. `esri` 래스터 레이어는 정상 렌더링되는데 `fill`/`line`/`circle` 등 **벡터 레이어만 전부 안 그려지는** 패턴이었다. 브라우저의 WebGL2 컨텍스트 정보를 직접 찍어보니 `renderer: "WebKit WebGL"` — Claude Code 브라우저 패널 자체가 (테스트 환경 한정으로) Chromium이 아닌 렌더링 백엔드를 쓰고 있었다.
4. 사용자가 실제 Chrome/Edge에서 별도로 테스트해준 결과, **Chrome은 되고 Edge는 안 됨**을 확인 — 완전히 같은 "래스터만 되고 벡터는 안 됨" 패턴이 사용자의 실제 브라우저에서도 재현됐다. `maplibre-gl`을 `6.6.0`(당시 최신)에서 `5.24.0`(직전 메이저)으로 다운그레이드하니 테스트 환경·사용자 환경(Edge 포함) 전부 즉시 해결됐다 — **v6.6.0이 특정 WebGL 백엔드(구형 ANGLE/D3D 경로 등)에서 벡터 레이어를 그리지 못하는 회귀 버그**였던 것으로 결론. `ui/package.json`의 `maplibre-gl`을 `^5.24.0`으로 고정(caret가 메이저 버전 경계는 넘지 않으므로 향후 `npm install`로 6.x가 다시 딸려올 일은 없음).

**교훈**: 이 세션에서 나온 "지도 데이터가 이상하다"류 버그 대부분이 실은 이 하나의 라이브러리 회귀에서 비롯됐을 가능성이 크다(admin-dong 경계선이 안 보였던 것도 포함). JS 레벨 진단(`isStyleLoaded()`, `queryRenderedFeatures()` 등)이 서로 모순되게 나올 때는 라이브러리/렌더링 백엔드 자체를 의심하고, 실제 스크린샷과 사용자의 다른 브라우저(Chrome vs Edge) 비교가 가장 확실한 증거였다.

---

## 9. 불확실성 표기 원칙 (전 모듈 공통)

- 모든 위험점수는 `contributing_factors`(근거)를 항상 함께 노출 — 숫자만 던지지 않는다
- `source: "observed" | "rule_based" | "ml_ranking"`을 명시해 어떤 방법으로 나온 값인지 구분
- Module CHG의 `change_type_hint`는 힌트일 뿐 확정 판정이 아님을 UI에 명시(§3.4)
- 구름 등으로 최근 관측이 없으면 "관측 공백" 배지를 명시적으로 표시(조용히 이전 값을 재사용하지 않음)

---

## 10. 실증·Backtest 전략

공모전 제안서에서 가장 강력한 증거는 "AI Accuracy 93%"가 아니라 **"같은 현장관리 효과를 더 적은 현장점검으로 달성한다"**는 증거다.

### Backtest A — 변화탐지 자체 검증
과거의 명확한 토지피복·식생 교란 사례를 고해상도 영상 또는 사람이 판독한 reference polygon으로 라벨링. 측정: `IoU / F1 / changed-area error`.

### Backtest B — 우선순위 검증
실제 이상지역 N개와 정상지역을 구성하고 시스템이 위험순위를 산출. 지표: `Precision@10`, `Recall@Top20%`, `Average Precision`. random 대비 몇 배의 이상사례를 포착했는가로 직관적으로 설명한다(random 기대 발견률 ≈ 20% 수준).

### Backtest C — 기존 방식 비교 (baseline 최소 3개)
`Random inspection` / `오래 미점검한 순서` / `단순 NDVI threshold` vs `Proposed multi-source risk ranking`(§5 Module VERIFY의 `baseline_comparison` 필드가 이 결과를 담는다). **AI가 baseline보다 별로 낫지 않으면 그것도 솔직히 보여주고 rule-based model을 유지한다** — 이것이 "AI가 꼭 필요한가?" 공격에 대한 가장 좋은 답이다.

### Backtest D — 업무효과 (선택, 시간 남으면)
환경·GIS 전공자 3~5명에게 "지도 없이 이상지역 찾기" vs "Priority Queue 사용해 찾기" 두 task를 시켜 판단 소요시간·정확도를 비교.

---

## 11. 공모전 전략 요약

### 11.1 Working Rubric (공식 배점 미확인 — 사용자가 지정한 가중치)

**중요**: 공식 붙임1 공모전 공고문 PDF의 심사표 원문은 아직 확인되지 않았다. **제출 전 반드시 공식 PDF를 재확인**하고 실제 배점이 나오면 아래를 재계산할 것.

가상 가중치: 기관·공모 적합성(최상) · 문제 중요성(높음) · 창의·차별성(높음) · 실현가능성(최상) · 효과성(최상) · 지속·확장성(중상) · 국민체감(중상) · 제안 구체성(최상, architecture+화면+backtest).

### 11.2 MAWP (Minimum Award-Worthy Product)

전국 1,700개소를 완성하는 시스템이 아니라 **"한 개 실증지역(유방동)에서 완전히 작동하며, 동일 구조를 전국 GIS에 붙일 수 있음을 증명하는 제품"**.

**반드시 구현**: 실제 AOI(유방동) · Sentinel-2 시계열 · (가능하면) Sentinel-1 이벤트 변화 · PNU 폴리곤 단위 집계 · 이상변화 score · Top-N priority queue · Before/After evidence card · 현장점검 입력 workflow · baseline 비교 · 실제 backtest 결과 · 1-page evidence report.

**과감히 버림**: §0.6 참조.

### 11.3 Red-Team 방어 — 가장 치명적인 공격과 답

| 공격 | 방어 |
|---|---|
| "이미 KECI가 AI 수변관리 추진 중 아닌가?" | 기존 인프라를 인정하고 "현장 우선순위·closed loop"로 범위를 좁힌다(§0.3) |
| "Sentinel 10m로 작은 이상을 잡을 수 있나?" | broad screening 전용, 고해상도/드론 후속 확인이 전제(§3.4) |
| "AI가 꼭 필요한가?" | Backtest C로 baseline과 정직하게 비교, 필요하면 rule-based로도 충분함을 인정(§10) |
| "내부 GIS가 없으면 prototype이 가능한가?" | 공개 Sentinel + V-World 연속지적도만으로 완성(§3.2) |
| "실제로 업무시간이 줄어드는가?" | Recall@Top20% / inspection effort reduction at equal recall이 핵심 KPI(§8) |

### 11.4 심사위원에게 보여줄 가장 강력한 한 장

```
실제 KECI 수변녹지 지도
기존 방식: 100개 대상지 확인
본 시스템: 점검 우선순위 상위 20필지만 확인
→ 그 20개에서 실제 이상사례의 대부분을 포착
→ 동일한 현장인력으로 더 많은 수변녹지를 관리
```

정확도 90%보다 이 한 장이 훨씬 강하다.

---

## 12. 개발 로드맵

현재 날짜 기준 접수 마감은 2026-09-30 18:00. 약 한 달을 모델 고도화가 아니라 **증거를 완성하는 데** 쓴다.

| 기간 | 목표 | 산출물 |
|---|---|---|
| 8/29–8/31 | Scope Lock, 리포 세팅(이 문서) | README/ARCHITECTURE 확정, 공식 붙임1 PDF 재확인 |
| 8/29 | **Data MVP 완료** — 유방동 82/85필지(96.5%) + 한강유역 전체 5,526/6,275필지(88.1%) polygon 복원·시각 검증(§3.2) | `data/processed/yongin_yubang_parcels.geojson`, `hanriver_maesu_parcels.geojson` |
| 9/6–9/10 | **Module OBS + CHG 완료** (2026-08-29 조기 착수, GEE 실증까지 완료; SAR 융합은 2026-08-30 추가) | Sentinel-2 시계열 파이프라인, vegetation/moisture/**SAR** anomaly, before-after |
| 9/11–9/14 | **Module AGG + RISK(rule) 완료** (2026-08-29 조기 착수) — 유방동 실제 필지 10건으로 end-to-end 파이프라인(OBS→CHG→AGG→RISK) 실증까지 완료 | 대상지 단위 feature, rule baseline, `data/processed/yongin_yubang_priority_queue.geojson` |
| 9/15–9/18 | Module RISK(ML, 선택) | LightGBM은 label 충분할 때만 추가 |
| 9/19–9/22 | **Module O + FIELD + API 서버 + UI 전부 완료**(2026-08-29 조기 착수) | `api_server.py`(FastAPI, 6개 엔드포인트), `ui/`(Next.js+MapLibre) — 지도 클릭→Evidence Card→현장점검 등록→큐 갱신까지 브라우저에서 end-to-end 확인 |
| 9/23–9/25 | **Module VERIFY 완료**(2026-08-29 조기 착수) — Precision@K·Recall@Top20%·baseline 비교·leakage 가드, `GET /verify/backtest` 연결 | baseline 비교, Precision@K, Recall@K |
| 9/26–9/27 | **Module AGENT 완료 + 실제 Gemini 검증까지 끝남**(2026-08-29 조기 착수) | `/sites/{id}/ask`, `POST /reports/weekly`, `gemini-3.6-flash`로 실제 응답 확인 |
| — | **B급 확장 일부 조기 완료(2026-08-29, 사용자 지적 반영)** — "왜 유방동만 보는가"에 답하기 위해 여러 시/군/구로 확대·배치 처리 성능 개선 | `module_obs/batch.py`(`reduceRegions` 기반, 이미지 수에만 비례하는 호출), `scripts/run_priority_queue_batch.py`, `data/processed/hanriver_priority_queue.geojson`(5개 시/군/구 50필지) |
| 9/28 | Red-Team | §11.3 공격 방어 리허설 |
| 9/29 | 제출본 Lock | 문장·도표·수치·인용 최종 검증 |
| 9/30 이전 | 제출 | 마감 당일이 아니라 전날 제출 권장 |

**B급 확장(MVP 이후 시간 남으면)**: Sentinel-1 이벤트 트리거 모드(§2.2), ML ranking, 강우·수문 API 연동. ~~여러 수계 확대~~는 위에서 조기 완료(단, 5,526필지 전체가 아니라 5개 시/군/구·50필지 표본 — 전체 확장은 여전히 후속 과제).

**코딩과 별개로 진행되는 작업**(이 리포 담당 아님): 참가신청서·개인정보동의서 작성, 제안서 초안→공식 붙임2 HWP 양식 이관(익명성 유지 필수), Backtest 수치 확보 후 기대효과 섹션 반영, ZIP 패키징(`공모분야번호_신청자명`).

---

## 13. 세션 브리핑 — 다음에 이 리포를 여는 Claude Code 세션에게

이 프로젝트는 Aquaguard처럼 여러 세션이 병렬로 작업하는 구조가 **아니다** — 사용자 1인 + Claude Code 세션이 순차적으로 §12 로드맵을 따라간다. 그래서 `contracts/` 폴더에 별도 JSON Schema 파일을 만들지 않았다 — 이 문서 §5의 예시 JSON이 유일한 소스 오브 트루스다. 새 모듈을 만들 때는 이 문서 §5를 먼저 갱신하고 코드를 짜라.

**지금 무엇을 먼저 해야 하는지 헷갈리면**: §12 로드맵 표에서 오늘 날짜가 속한 구간을 찾아라. Data MVP부터 8개 모듈(OBS/CHG/AGG/RISK/O/FIELD/VERIFY/AGENT) + API 서버 + UI까지 2026-08-29에 전부 조기 완료·실증됐다(Gemini·GEE 둘 다 실제 키로 검증 완료). 남은 건 **§11.3 Red-Team 리허설과 제출 준비**뿐이다 — 새 기능이 아니라 6,275건 전체로 배치 확장(§12 B급), 공식 붙임1 심사표 재확인(§12 8/29~8/31 항목), 제안서 작성 쪽으로 넘어갈 것.

**막히면**: `data/raw/`의 CSV·`.env`의 `VWORLD_API_KEY`/`GEE_PROJECT_ID`는 이미 배치·검증돼 있다(2026-08-29). 전체 파이프라인을 재검증하려면 저장소 루트에서 `python -m pytest -v`(`conftest.py`가 `.env`를 자동 로드하므로 라이브 GEE 테스트까지 함께 돈다). end-to-end 데모를 다시 돌리려면 `PYTHONPATH=. python scripts/run_priority_queue_demo.py --limit N`. 서버·UI를 띄우려면 `python -m uvicorn api_server:app --port 8001`(백엔드) 후 `cd ui && npm run dev`(프론트) — `ui/lib/api.ts`의 `NEXT_PUBLIC_API_BASE` 기본값이 `http://localhost:8001`.

**알려진 한계(2026-08-29, 2026-08-30·2026-08-31 일부 해소)**: `scripts/run_priority_queue_demo.py`/`run_priority_queue_batch.py`가 만드는 `site_attributes` 중 `recent_rainfall_mm`(`common/weather.py`, Open-Meteo)과 `adjacent_to_water`(`module_obs/water.py`, JRC Global Surface Water — 아래 참조)는 이제 채워진다. `restoration_elapsed_days`·`last_inspection_days_ago`·`past_anomaly_count`만 여전히 빈 값이다 — KECI 내부 자산 DB(복원경과일·최근점검일·과거이상이력)에 접근할 방법이 없기 때문(§ Module AGG 구현 상태). 그래서 지금 나오는 risk_score는 `anomaly_score_mean`+`changed_area_ratio`+`sar_anomaly_mean`+`recent_rainfall_mm`+`adjacent_to_water` 다섯 요인(가중치 합 0.75)으로 계산된다.

**요인 실측화(2026-08-31, "기술 스택을 더 끌어올릴 방법" 질문에서 진행)**:
- **`adjacent_to_water` 실측**: 지금까지 항상 `None`이었던 요인을 `module_obs/water.py`(JRC Global Surface Water `occurrence` 밴드, 버퍼 150m 내 최댓값이 25% 이상이면 인접으로 판정)로 실제 계산한다. "수변"을 이름에 단 시스템이 정작 이 값을 못 채우고 있던 어색한 공백을 메꿨다. 단일/배치 조회 둘 다 구현(`is_adjacent_to_water`/`is_adjacent_to_water_batch`) — 배치는 SAR 배치와 같은 이유로 `reduceRegions` 출력 컬럼명이 밴드명이 아니라 reducer 출력명("max")이 되는 함정을 그대로 재사용해 처리한다. 60개 site 재생성 결과 20개가 인접 판정(true).
- **`changed_area_ratio` 실측**: `module_obs/pixel_diff.py`가 기준·현재 기간 NDVI 합성(median composite)을 픽셀 단위로 빼서 |변화|가 `ANOMALY_THRESHOLD_FOR_CHANGE`를 넘는 픽셀의 이진 마스크를 만들고, 그 마스크를 `reduceRegion(mean)`하면 그 자체가 "변화 픽셀 비율"이 된다는 트릭을 쓴다(§12 로드맵에 있던 B급 확장 항목을 완료). `module_chg.compute_change_from_scenes()`에 `real_changed_area_ratio` 파라미터를 추가해, 주어지면 그 값을 쓰고 GEE 호출이 실패하면 기존 이상도 근사치로 자동 폴백한다 — 어느 쪽인지 `changed_area_ratio_source`("pixel_diff" | "approximated") 필드로 항상 구분해 표시해 과장하지 않는다. 60개 site 전부 실측 성공(폴백 0건).
- 두 함수 모두 배치 버전은 site 수와 무관하게 이미지 1~2장 + `reduceRegions` 1회로 끝나는 기존 배치 패턴을 그대로 따른다(§ Module OBS 배치 조회 구현 상태 참조).
