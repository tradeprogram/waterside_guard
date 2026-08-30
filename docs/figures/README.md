# 제안서용 그림

전부 `scripts/generate_figures.py`가 **실행 중인 API의 실제 응답**에서 생성한다.
추정치·예시값으로 만든 그림은 여기에 없다 — 제안서의 모든 숫자는 재현 가능해야 한다.

```bash
python api_server.py              # 먼저 API를 띄운다(:8001)
python scripts/generate_figures.py            # 전부
python scripts/generate_figures.py --only ablation route
```

UI 화면 캡처는 여기서 만들지 않는다(화면 디자인이 계속 바뀐다). 도식·차트·지도만 둔다.

| 파일 | 내용 | 근거 |
|---|---|---|
| `F1_ablation_seasonal_falsepositive.png` | 계절 기준선이 걸러낸 오탐 6건 → 0건. **라벨 없이 낼 수 있는 유일한 정량 근거** | `GET /verify/ablation?k=10` |
| `F3_workflow.png` | 위성이 후보를 좁히고 사람·드론이 확인하는 흐름 — "드론을 대체하지 않는다" | 아키텍처 |
| `F5_seasonal_baseline_principle.png` | 과거 3년 같은 계절 정상범위 대비 올해 값의 위치 | `GET /sites/{id}/timeseries` |
| `F9_architecture.png` | 8모듈 구조와 폴백 계층 | `ARCHITECTURE.md` |
| `F10_site_distribution.png` | 한강유역 6개 시/군/구 60필지 분포와 등급 구성 | `data/processed/*_priority_queue.geojson` |
| `F11_score_breakdown.png` | 점수의 요인별 분해 + **결측 요인까지 빗금으로 표기** | `GET /sites/{id}/evidence` |
| `F_route_savings.png` | 군집·동선 최적화로 줄어드는 이동거리(직선거리 기준) | `GET /priority-queue/route` |

아직 만들 수 없는 그림(현장 라벨 확보 후): 커버리지 곡선, Precision@K.
라벨 없이 이 수치를 채워 넣지 않는다.
