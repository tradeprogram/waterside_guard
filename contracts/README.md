# 모듈 계약 (contracts/)

각 `module_*.example.json`은 [`../ARCHITECTURE.md` §5](../ARCHITECTURE.md#5-모듈-계약--입출력-예시)에 있는 모듈 출력 예시를 그대로 옮긴 것이다. 이 프로젝트는 단일 세션 순차 개발이라 별도 JSON Schema 파일은 두지 않는다 — 이 파일들과 ARCHITECTURE.md §5가 유일한 소스 오브 트루스다.

모듈 인터페이스를 바꿀 때는:
1. `ARCHITECTURE.md` §5의 해당 모듈 섹션을 먼저 갱신한다.
2. 이 폴더의 `module_*.example.json`을 동일하게 갱신한다.
3. 그다음 코드를 수정한다.

모든 출력은 공통 봉투(envelope) 형식(`status`/`fallback_tier`/`data`/`warnings`)을 따른다 — [ARCHITECTURE.md §4.2](../ARCHITECTURE.md#42-모듈-호출-규약) 참조.
