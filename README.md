## 에이전트가 부작용을 낼 때 무엇이 잘못되는가

다섯 저장소가 한 질문의 서로 다른 면을 다룬다. **주장이 검사 가능한가, 그리고 그 검사가 실제로 무언가를 본 결과인가.**

| | 무엇을 하는가 | 테스트 |
|---|---|---|
| [**agent-safety-core**](https://github.com/ohsewool/agent-safety-core) | 승인과 실행의 결속, 1회용 lease, `UNKNOWN_OUTCOME`의 명시적 처리 | 304 |
| [**modelmate**](https://github.com/ohsewool/modelmate) | 비전문가용 모델링 도우미 — 증거가 없으면 확신하지 않는 리포트 | 284 |
| [**rag-profile-selector**](https://github.com/ohsewool/rag-profile-selector) | 인용이 문서의 어디를 가리키는지 측정 · 한국어 법령 코퍼스 | 177 |
| [**mcp-gateway**](https://github.com/ohsewool/mcp-gateway) | MCP 서버 앞의 보안 프록시 — 정책 차단, JIT 승인, 해시 체인 감사 | 155 |
| [**document-intelligence**](https://github.com/ohsewool/document-intelligence) | 파서에 의존하지 않는 문서 증거 모델 | 67 |

전부 Apache-2.0, CI 초록불, `pip install -e .`.

---

## 각 저장소가 실제로 발견한 것

만든 것보다 **걸려 넘어진 것**이 더 말해준다. 아래는 전부 자기 코드가 자기 데모에 걸려 드러난 것들이다.

**누출 검사기가 이름만 보고 있었다** ([modelmate](https://github.com/ohsewool/modelmate/blob/main/docs/DEMO_DATA.md)) — 누출을 심은 데모를 만들었더니 검사기가 셋 다 놓쳤다. `exit_survey_score`는 잡혔지만 이유가 "score"라는 단어였고, `wellbeing_index`로 **이름만** 바꾸자 같은 값·같은 분리력(8.43 대 2.08)으로 통과했다. 지금은 컬럼이 *무엇을 하는지* 잰다. 누출 방치 AUC **1.0** 대 권고 적용 **0.778**.

**통제가 정의만 되고 배선되지 않았다** ([agent-safety-core](https://github.com/ohsewool/agent-safety-core/blob/main/docs/REDTEAM-002-findings.md)) — 2차 레드팀에서 공격 4건이 전부 관통했다. `access.py`에 권한·역할·승인분리 헬퍼가 다 있었고 `ledger.py`가 그중 아무것도 import하지 않았다. `reconcile()`의 docstring은 "에이전트는 이 전이를 할 수 없다"고 적혀 있었고, 검증 없는 자유 문자열이었다.

**headroom은 있지만 닿지 않는다** ([rag-profile-selector](https://github.com/ohsewool/rag-profile-selector/blob/main/experiments/KR_LAW_RESULTS.md)) — 질의별 프로파일 선택의 상한을 먼저 쟀다. 규칙 넷 중 하나가 기준선을 이겼지만, 그 규칙이 다르게 고른 질의는 3건(개선 2·악화 1)으로 **순이득 1건**이다. 28건 표본에서 우연과 구분되지 않는다. 부정적 결과를 결론 자리에 둔다.

**게이트웨이가 감시 대상에게 자기 환경변수를 넘기고 있었다** ([mcp-gateway](https://github.com/ohsewool/mcp-gateway)) — 두 번째 서버를 붙이다 발견했다. `Popen`에 `env`를 안 줘서, 게이트웨이가 쥔 모든 크리덴셜이 게이트웨이가 의심하려고 존재하는 프로세스에 넘어갔다.

**구역 하나가 페이지 전체를 무효로 만들었다** ([document-intelligence](https://github.com/ohsewool/document-intelligence)) — 실제 PDF를 넣으니 거부 0건이었다. 의심스러워 깨진 좌표를 주입했더니 검증은 돌았고, 대신 잘못된 구역 하나가 멀쩡한 구역 98개를 함께 날렸다.

---

## 반복되는 것

여섯 번 같은 종류의 문제를 만났다. **초록불이 실제로 확인한 결과가 아니었던 것.**

- 시크릿 스캐너가 정규식 에러로 아무것도 못 보고 "5개 저장소 깨끗"이라 보고했다 — 방금 키 4개를 꺼낸 저장소를 포함해서
- 같은 스캐너가 175개 파일을 OpenAI 키로 지목했다. 전부 Tailwind CSS 변수명이었다
- `dropna()`가 누출의 증거를 버리고 "측정 불가"라 결론냈다
- CI가 테스트 5~35개를 조용히 빠뜨린 채 초록 배지를 달 뻔했다
- README의 첫 명령이 새 클론에서 `ModuleNotFoundError`를 냈다. 테스트가 `sys.path.insert`로 가리고 있었다
- 제 측정치 하나가 CPU 경합 중에 잰 값이었다(182초 → 실제 7.5초). CI가 그걸 잡아냈다

그래서 도구마다 **자기가 실제로 찾아봤는지 증명하게** 만들었다. 시크릿 스캐너는 양성 대조 없이는 결과를 내지 않고, CI는 수집된 테스트 수를 세고, witness 적합성 시험은 부적합 구현 5종을 거부하는지 먼저 확인한다.

*"못 찾았다"와 "찾아보지 못했다"를 구분하지 못하는 검사는 없는 것보다 나쁘다. 확신을 만들어내기 때문이다.*
