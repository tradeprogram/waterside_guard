# 수변가드 AI (Waterside Guard) — 아키텍처 확정안 v1.0

> 이 문서는 이 프로젝트의 정본(Source of Truth)이다. 배경지식이 없는 Claude Code 세션이 이 문서 하나만 읽고 바로 작업을 이어갈 수 있도록 쓰였다. **§0을 반드시 먼저 읽어라** — "무엇을 왜 만드는지"를 이해하지 못한 채 §5의 모듈 계약만 구현하면 숫자는 맞아도 프로젝트의 목적을 놓친 코드가 나온다.
>
> 참고 벤치마크: [tradeprogram/Aquaguard](https://github.com/tradeprogram/Aquaguard) — envelope 규약·폴백계층·상태머신·모듈 계약 패턴 출처. [tradeprogram/policymaps](https://github.com/tradeprogram/policymaps) — 검증배지·데이터 출처 공시·MCP tool화 패턴 출처.
>
> 원본 리서치: [`docs/2026_KECI_공모전_수상전략_리서치.pdf`](docs/2026_KECI_공모전_수상전략_리서치.pdf), 핸드오프 브리프: [`docs/개발_핸드오프_브리프.md`](docs/개발_핸드오프_브리프.md).

**프로젝트명**: 수변가드 AI (Waterside Guard) — 한국환경보전원(KECI)이 관리하는 전국 수변녹지·매수토지의 현장점검 우선순위를 위성 변화탐지 + GIS 위험도 점수로 자동 산출하는 의사결정지원 시스템.

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

수변가드가 끼워 넣는 고부가가치 단계: `복원·식재 → 지속 관측 → 이상변화 자동 선별 → 우선점검 → 현장 확인 → 전후 효과 자동 검증 → 다음 관리 우선순위`

### 0.3 한 문장 포지셔닝

> 수변가드 AI는 새로운 위성 모니터링 플랫폼이 아니다. 한국환경보전원이 이미 구축한 GIS·드론·위성 기반 위에서, "오늘 어디를 먼저 가야 하는가"를 자동으로 계산하고, 현장 결과로 그 판단을 검증·환류하는 마지막 운영 layer다.

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

1. 담당자가 월요일 오전 수변가드에 접속한다. 화면에는 전체 대상지 대신 **"이번 주 확인 필요 N개소"**가 먼저 나타난다.
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

`관측(OBS) → 변화탐지(CHG) → 공간집계(AGG) → 위험도산정(RISK) → 우선순위생성(O) → 현장점검(FIELD) → 검증환류(VERIFY)`

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
| 확률/점수 | `risk_score`는 0~100 정수, 그 외 확률형 값은 float 0.0~1.0 |
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

**구현 상태(2026-08-29, 실증 완료)**: `module_obs/run.py` — 원래 Sentinel Hub Statistical API로 구현했으나, 사용자가 이미 보유한 **Google Earth Engine**(`COPERNICUS/S2_SR_HARMONIZED`)으로 전환했다(CDSE도 검토했으나 GEE로 확정). `ee.ImageCollection.map()`으로 장면마다 SCL 기반 구름마스크·NDVI·NDMI를 서버 사이드에서 계산하고 `reduceRegion`으로 AOI 평균만 받는다 — 픽셀 래스터 전체를 로컬로 내려받지 않는다. `aggregate_array()`로 시계열 전체를 4번의 `getInfo()` 호출로 가져오므로 장면 수만큼 왕복하지 않는다. `GEE_PROJECT_ID`가 `.env`에 없거나 초기화가 실패하면 예외 대신 `status:"degraded", fallback_tier:3, data.scenes:[]`를 반환 — §0.5 "AI가 실패해도 서비스가 작동하는 설계"를 코드로 강제한 지점. 현재 구현은 Sentinel-2만 지원한다(입력에 `sources` 필드는 없음 — 애초에 다중소스 스위칭을 만들지 않았다, Sentinel-1은 §3.4에 적어둔 것처럼 향후 확장). `composite_ref`는 지도에 실제 위성영상 타일을 얹을 때(Before/After Evidence Card, §8) 쓸 예약 필드로 코드에 남겨뒀지만 아직 채우지 않는다.

**유방동 AOI로 실제 검증됨** — `GEE_PROJECT_ID` 등록 후(Earth Engine API가 해당 Cloud 프로젝트에서 비활성 상태였던 걸 콘솔에서 활성화) 2026-06-01~08-25 구간에서 NDVI 0.51~0.58 수준의 실제 관측치를 받았다. **실증 중 발견·수정한 버그**: `CLOUDY_PIXEL_PERCENTAGE`는 Sentinel-2 타일(최대 110×110km) 전체 기준이라, 우리 AOI처럼 작은 영역은 타일 다른 곳의 구름 때문에 실제로는 맑은 장면도 걸러지는 문제가 실측으로 확인됐다. 그래서 타일 메타데이터 필터는 후보를 줄이는 넓은 예비필터(80%)로만 쓰고, 실제 채택 기준은 `reduceRegion`으로 계산한 **AOI 자체의 유효(비구름) 픽셀 비율**(`MIN_AOI_VALID_RATIO=0.5`)로 바꿨다. `pytest module_obs/tests/ -v`의 라이브 테스트(`test_live_fetch_returns_scenes_when_credentials_present`)가 실제 API 호출로 통과함을 확인 — `conftest.py`가 `.env`를 자동 로드해 pytest에서도 자격증명을 인식한다.

### Module CHG — 변화탐지 (`module_chg`)

```jsonc
// input — Module OBS의 output(composite 시계열)을 받음
{ "aoi_id": "YONGIN_YUBANG", "site_geometry_5179": { "type": "Polygon", "coordinates": [] },
  "baseline_period": ["2024-06-01", "2024-08-31"], "current_period": ["2026-06-01", "2026-08-31"] }

// output (data)
{ "anomaly_score": 0.72, "changed_area_ratio": 0.18,
  "change_type_hint": "vegetation_decline", // "vegetation_decline" | "moisture_increase" | "bare_ground_increase" | "no_significant_change"
  "source": "observed", "confidence_interval": [0.61, 0.83] }
```

`change_type_hint`는 원인 진단이 아니라 **"무엇이 달라졌는지"에 대한 힌트**일 뿐이다 — §3.4의 범위 제한 원칙(종 판독 금지)을 지킨다. 폴백: Sentinel-2+1 융합 → Sentinel-2 단독(§4.3).

**구현 상태(2026-08-29)**: `module_chg/run.py` — Module OBS를 baseline/current 두 번 호출해 NDVI/NDMI **scene 평균의 편차**로 `anomaly_score`를 계산한다. **중요한 근사**: 현재 `changed_area_ratio`는 진짜 픽셀 단위 변화면적이 아니라 이상도 크기로부터 근사한 값이다(§12 로드맵 B급 확장에서 Earth Engine `reduceRegion` histogram 기반 pixel-wise diff로 교체 예정) — Backtest A(§10)에서 이 근사가 실제와 얼마나 다른지 반드시 검증할 것. `python -m pytest module_chg/tests/ -v`로 mock 기반 단위 테스트(자격증명 불필요) 통과 확인됨.

### Module AGG — GIS 공간 집계 (`module_agg`)

```jsonc
// input — Module CHG 출력을 관리대상지 단위로 묶음
{ "site_id": "A1037", "pnu": "4146110500100780003",
  "chg_results": [ { "anomaly_score": 0.72, "changed_area_ratio": 0.18 } ],
  "site_attributes": { "restoration_elapsed_days": 420, "last_inspection_days_ago": 63,
    "adjacent_to_water": true, "past_anomaly_count": 1 } }

// output (data)
{ "site_id": "A1037", "features": {
    "anomaly_score_mean": 0.72, "changed_area_ratio": 0.18,
    "adjacent_to_water": true, "restoration_elapsed_days": 420,
    "last_inspection_days_ago": 63, "past_anomaly_count": 1 } }
```

**구현 상태(2026-08-29)**: `module_agg/run.py` — Module CHG 결과(들)를 평균해 `anomaly_score_mean`/`changed_area_ratio`를 만들고, `site_attributes`는 그대로 통과시킨다. **중요한 제약**: `site_attributes`(복원경과일·최근점검일·인접수계여부·과거이상이력)는 KECI 내부 자산 DB에서 와야 하는데 이 프로토타입은 접근권한이 없다(개발_핸드오프_브리프 §2). 현재는 호출부가 채울 수 있는 값만 채우고 나머지는 `null`로 둔다 — Module RISK가 `null`을 "0 기여"로 안전하게 처리한다(아래 참조). `pytest module_agg/tests/ -v` 통과.

### Module RISK — 위험도 산정 (`module_risk`)

> **방법론 확정**: 처음부터 DNN을 쓰지 않는다. 1단계는 **규칙+통계 이상탐지**(explainable, label 불필요), label이 충분히 쌓이면 2단계로 **LightGBM/XGBoost ranking**을 얹는다(§6). 공모전에서 DNN을 억지로 넣는 것은 오히려 감점 요소가 될 수 있다.

```jsonc
// input — Module AGG의 features를 받음
{ "site_id": "A1037", "features": {
    "anomaly_score_mean": 0.72, "changed_area_ratio": 0.18,
    "adjacent_to_water": true, "restoration_elapsed_days": 420,
    "last_inspection_days_ago": 63, "past_anomaly_count": 1 } }

// output (data) — risk_score가 최종 output. 아래 값은 module_risk/run.py 실제 실행 결과(2026-08-29 검증)
{ "site_id": "A1037", "risk_score": 54, "risk_tier": "2순위",
  // risk_tier ∈ {"1순위"(>=70),"2순위"(>=50),"3순위"(>=30),"정상"}. "rank"(대기열 순번, §Module O)와는 별개 개념
  "contributing_factors": [
    { "factor": "anomaly_score_mean", "value": 0.72, "weight": 0.35 },
    { "factor": "changed_area_ratio", "value": 0.18, "weight": 0.20 },
    { "factor": "last_inspection_days_ago", "value": 63, "weight": 0.15 },
    { "factor": "adjacent_to_water", "value": true, "weight": 0.15 },
    { "factor": "past_anomaly_count", "value": 1, "weight": 0.15 }
  ],
  "model_version": "rule_v1", "source": "rule_based" } // "rule_based" | "ml_ranking"
```

`risk_score` 산출식(1단계, rule baseline):

```
risk_score = 100 × clip(
  0.35 × anomaly_score_mean
  + 0.20 × changed_area_ratio
  + 0.15 × min(last_inspection_days_ago / 180, 1.0)
  + 0.15 × adjacent_to_water(0|1)
  + 0.15 × min(past_anomaly_count / 3, 1.0)
, 0, 1)
```

가중치는 초기 가정값 — Backtest B(§10)에서 실제 이상사례 기준으로 보정한다. `contributing_factors`는 Module AGENT가 "왜 1순위인가"를 설명할 때 그대로 인용하는 근거 데이터다(숫자를 만들지 않고 tool output을 읽는 원칙, §0.4).

**구현 상태(2026-08-29)**: `module_risk/run.py` — 위 산출식을 그대로 구현. `features`의 특정 항목이 `null`이면(§ Module AGG의 KECI 내부 데이터 접근 제약 참조) 해당 가중항을 0으로 처리하고 `contributing_factors`에서 빼며, `status:"degraded"`로 표시해 "이 점수는 일부 요인 없이 계산됐다"는 사실을 숨기지 않는다. `risk_tier` 경계값은 70/50/30(§ 위 주석)으로 확정. `pytest module_risk/tests/ -v`에 위 A1037 예시(risk_score=54)를 정확히 재현하는 회귀 테스트가 있다 — 가중치를 바꾸면 이 테스트도 함께 갱신할 것.

### Module O — 오케스트레이션 (`module_o`)

**역할**: 전체 AOI의 Module RISK 결과를 모아 Top-N 우선순위 큐를 생성하고, 담당자 의사결정을 위한 상태를 관리한다.

```jsonc
// output (data)
{ "week_of": "2026-09-01", "priority_queue": [
    { "rank": 1, "site_id": "A1037", "risk_score": 54, "status": "미점검" }
  ],
  "queue_size": 12, "generated_at": "2026-09-01T09:00:00+09:00" }
```

**상태머신**(대상지 단위): `관측 → 변화탐지 → 집계 → 위험도산정 → 우선순위큐등록 → 현장점검등록 → 결과입력 → 검증완료`. 담당자 승인 게이트는 없다(재난 대응형 시스템이 아니므로 human-in-the-loop이 이미 "현장점검을 실제로 갈지 말지" 판단 자체에 있음 — Aquaguard의 관공서 모드 승인 게이트 같은 별도 장치 불필요).

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
  "predictions": [ { "site_id": "A1037", "risk_score": 54, "predicted_at": "2026-09-01" } ],
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

1. **1단계 — 규칙+통계 이상탐지**(§5 Module RISK의 `risk_score` 산출식). 설명 가능하고 label 없이도 작동한다. **공모전 프로토타입의 기본값.**
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
POST /inspections
GET  /verify/backtest?period=...&k=10
POST /reports/weekly
POST /sites/{site_id}/ask            -- §7 원안에 없던 추가: Module AGENT Q&A(§5)를 실제로 쓰려면 필요했음
```

**구현 상태(2026-08-29)**: `api_server.py` — 위 목록 전부 구현·테스트 완료(`tests/test_api_server.py`, FastAPI `TestClient` 사용, GEE/Gemini 자격증명 불필요 — 둘 다 없으면 각 모듈이 자체 폴백으로 응답). 서버 시작 시 `data/processed/yongin_yubang_priority_queue.geojson`(Module RISK 조기 실증 결과, §5 Module RISK)을 읽어 Module O의 인메모리 store를 채운다 — 매 요청마다 Earth Engine을 다시 부르지 않는다(§2.2 배치 모드 원칙). `/verify/backtest`는 store의 현재 risk_score + 등록된 현장점검 이력을 Module VERIFY로 채점한다 — 진짜 leakage-free backtest는 아직 아니다(§5 Module VERIFY 구현 상태 참조). `/sites/{site_id}/ask`·`/reports/weekly`는 Module AGENT를 감싼다 — `GEMINI_API_KEY`가 없으면 템플릿 폴백 응답을 그대로 반환한다(200 OK, `status:"degraded"`).

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

**구현 상태(2026-08-29)**: `ui/`(Next.js + MapLibre GL JS)가 6개 중 4개를 구현했다 — Map, Priority Queue, Evidence Card, Inspection. **Before/After**(실제 위성영상 타일)는 아직 없다 — Module OBS의 `composite_ref`가 예약 필드로만 존재(§5 Module OBS 구현 상태). **Time Series**는 SAR 없이 NDVI만 순수 SVG 스파크라인으로 표시 중(외부 차트 라이브러리 없음, `components/TimeSeriesChart.tsx`). 메인 KPI 중 `Precision@K`는 Module VERIFY 미구현이라 아직 없다. 실제 브라우저에서 지도 클릭 → Evidence Card → 현장점검 등록 → Priority Queue 상태 갱신까지 end-to-end로 확인됨.

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
수변가드: 위험 상위 20개만 확인
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
| 9/6–9/10 | **Module OBS + CHG 완료** (2026-08-29 조기 착수, GEE 실증까지 완료) | Sentinel-2 시계열 파이프라인, vegetation/moisture anomaly, before-after |
| 9/11–9/14 | **Module AGG + RISK(rule) 완료** (2026-08-29 조기 착수) — 유방동 실제 필지 10건으로 end-to-end 파이프라인(OBS→CHG→AGG→RISK) 실증까지 완료 | 대상지 단위 feature, rule baseline, `data/processed/yongin_yubang_priority_queue.geojson` |
| 9/15–9/18 | Module RISK(ML, 선택) | LightGBM은 label 충분할 때만 추가 |
| 9/19–9/22 | **Module O + FIELD + API 서버 + UI 전부 완료**(2026-08-29 조기 착수) | `api_server.py`(FastAPI, 6개 엔드포인트), `ui/`(Next.js+MapLibre) — 지도 클릭→Evidence Card→현장점검 등록→큐 갱신까지 브라우저에서 end-to-end 확인 |
| 9/23–9/25 | **Module VERIFY 완료**(2026-08-29 조기 착수) — Precision@K·Recall@Top20%·baseline 비교·leakage 가드, `GET /verify/backtest` 연결 | baseline 비교, Precision@K, Recall@K |
| 9/26–9/27 | **Module AGENT 완료 + 실제 Gemini 검증까지 끝남**(2026-08-29 조기 착수) | `/sites/{id}/ask`, `POST /reports/weekly`, `gemini-3.6-flash`로 실제 응답 확인 |
| 9/28 | Red-Team | §11.3 공격 방어 리허설 |
| 9/29 | 제출본 Lock | 문장·도표·수치·인용 최종 검증 |
| 9/30 이전 | 제출 | 마감 당일이 아니라 전날 제출 권장 |

**B급 확장(MVP 이후 시간 남으면)**: Sentinel-1 이벤트 트리거 모드(§2.2), ML ranking, 강우·수문 API 연동, 여러 수계 확대.

**코딩과 별개로 진행되는 작업**(이 리포 담당 아님): 참가신청서·개인정보동의서 작성, 제안서 초안→공식 붙임2 HWP 양식 이관(익명성 유지 필수), Backtest 수치 확보 후 기대효과 섹션 반영, ZIP 패키징(`공모분야번호_신청자명`).

---

## 13. 세션 브리핑 — 다음에 이 리포를 여는 Claude Code 세션에게

이 프로젝트는 Aquaguard처럼 여러 세션이 병렬로 작업하는 구조가 **아니다** — 사용자 1인 + Claude Code 세션이 순차적으로 §12 로드맵을 따라간다. 그래서 `contracts/` 폴더에 별도 JSON Schema 파일을 만들지 않았다 — 이 문서 §5의 예시 JSON이 유일한 소스 오브 트루스다. 새 모듈을 만들 때는 이 문서 §5를 먼저 갱신하고 코드를 짜라.

**지금 무엇을 먼저 해야 하는지 헷갈리면**: §12 로드맵 표에서 오늘 날짜가 속한 구간을 찾아라. Data MVP부터 8개 모듈(OBS/CHG/AGG/RISK/O/FIELD/VERIFY/AGENT) + API 서버 + UI까지 2026-08-29에 전부 조기 완료·실증됐다(Gemini·GEE 둘 다 실제 키로 검증 완료). 남은 건 **§11.3 Red-Team 리허설과 제출 준비**뿐이다 — 새 기능이 아니라 6,275건 전체로 배치 확장(§12 B급), 공식 붙임1 심사표 재확인(§12 8/29~8/31 항목), 제안서 작성 쪽으로 넘어갈 것.

**막히면**: `data/raw/`의 CSV·`.env`의 `VWORLD_API_KEY`/`GEE_PROJECT_ID`는 이미 배치·검증돼 있다(2026-08-29). 전체 파이프라인을 재검증하려면 저장소 루트에서 `python -m pytest -v`(`conftest.py`가 `.env`를 자동 로드하므로 라이브 GEE 테스트까지 함께 돈다). end-to-end 데모를 다시 돌리려면 `PYTHONPATH=. python scripts/run_priority_queue_demo.py --limit N`. 서버·UI를 띄우려면 `python -m uvicorn api_server:app --port 8001`(백엔드) 후 `cd ui && npm run dev`(프론트) — `ui/lib/api.ts`의 `NEXT_PUBLIC_API_BASE` 기본값이 `http://localhost:8001`.

**알려진 한계(2026-08-29, 아직 안 고친 것)**: `scripts/run_priority_queue_demo.py`가 만드는 `site_attributes`는 전부 빈 값이다 — KECI 내부 자산 DB(복원경과일·최근점검일·인접수계여부·과거이상이력)에 접근할 방법이 없기 때문(§ Module AGG 구현 상태). 그래서 지금 나오는 risk_score는 `anomaly_score_mean`+`changed_area_ratio` 두 요인(가중치 합 0.55)만으로 계산돼 최대치가 구조적으로 낮다 — 유방동 10필지 실증에서 전부 "정상"(risk_score 2~16)로 나온 것은 실제로 이상이 없어서일 수도 있지만, 요인 결측 때문에 점수 자체가 눌려 있을 가능성도 크다. `adjacent_to_water`는 실제로는 GEE의 수체 레이어(JRC Global Surface Water 등)로 계산 가능한 값이니 §12 B급 확장 우선순위로 다음에 붙일 것.
