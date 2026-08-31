# 수변생태벨트 점검 우선순위 지원시스템 — 대시보드 (`ui/`)

Next.js + MapLibre GL JS. ARCHITECTURE.md §8 UI·대시보드 설계 중 지도/Priority Queue/Evidence Card/Time Series/Inspection을 구현한 것. 계산은 전부 `../api_server.py`(FastAPI)가 하고, 이 앱은 fetch만 한다.

## 실행

1. 백엔드 먼저: 저장소 루트에서 `python -m uvicorn api_server:app --port 8001`
2. `npm install && npm run dev` (기본 `http://localhost:3000`, 포트가 사용 중이면 Next.js가 다른 포트를 고른다)
3. 백엔드 주소가 `http://localhost:8001`이 아니면 `.env.local`에 `NEXT_PUBLIC_API_BASE=...` 설정

## 구조

```
lib/api.ts                    # api_server.py를 감싼 fetch 클라이언트 — 계산 로직 없음
components/MapView.tsx         # MapLibre 지도, risk_tier별 색상 폴리곤
components/PriorityQueueList.tsx  # 좌측 Top-N 목록
components/EvidencePanel.tsx      # 우측 Evidence Card — 근거·시계열·점검 등록
components/TimeSeriesChart.tsx    # baseline/current NDVI 스파크라인(외부 차트 라이브러리 없음)
components/InspectionForm.tsx     # POST /inspections
```

## 알려진 제약(2026-08-29)

- Before/After 위성영상 타일(실제 이미지)은 아직 없다 — NDVI 스파크라인만 표시(§ Module OBS `composite_ref` 예약 필드 참조).
- 자동 새로고침 없음 — 점검 등록 후에만 데이터를 다시 불러온다.
- 인증 없음(프로토타입 범위).
