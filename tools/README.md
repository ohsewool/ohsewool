# 계기 목록 — 무엇이 무엇을 지키고, 언제 도는가

이 디렉터리의 도구는 전부 **주장이 현실에서 떠나는 것**을 잡는 계기다. 열다섯이
되도록 목록이 없었다 — 인계받는 사람은 뭘 언제 돌려야 하는지 docstring 열다섯을
뒤져야 알았다. *유지 모드는 계약이 있어야 유지된다.*

각 도구의 **왜**는 그 파일의 docstring에 있다. 여기는 무엇을·언제만 적는다.

## 매 push — counts CI가 돌린다

| 도구 | 지키는 것 |
|---|---|
| `check_counts.py` | 프로필 표의 테스트 수 ↔ 각 저장소 README |
| `check_findings_index.py` | FINDINGS 목차·절·README 주장·색인 개수 일치 |
| `check_anchors.py` | 내부 링크가 실재하는 제목을 가리키는가 |
| `check_tools_inventory.py` | **이 목록 자체** — tools/의 모든 도구가 여기 있는가 |
| `find_vacuous_tests.py` | 부르지도 단언하지도 않는 테스트 |
| `check_env.py` | import가 올바른 체크아웃에 닿는가 (`--require-importable`) |
| `check_mutation_freshness.py` | 변이 감사가 낡지 않았는가 (mutate.py는 1.5h라 못 돈다) |
| `check_repo_descriptions.py` | GitHub 저장소 설명의 테스트 수 ↔ README |
| `check_scheduled_workflows.py` | 주간 워크플로 셋의 마지막 실행이 살아 있는가 |

## 주간 — counts CI의 doc-tests-bite 잡 (schedule/dispatch 전용)

| 도구 | 지키는 것 |
|---|---|
| `check_doc_tests_bite.py` | 문서를 읽는 검사가 그 문서에 **물려** 있는가 (비우기/심기 대조) |
| `check_docs_still_agree.py` | 문서를 읽는 검사 28개가 지금도 통과하는가 |

`check_docs_still_agree.py`는 **문서를 고친 회차에는 밀기 전에 손으로도 돌린다**
(다섯 저장소 ~90초). 같은 실수를 두 번 하고 만든 규칙이다.

## 회차마다 손 — 관문이 아니라 지도

| 도구 | 지키는 것 | 비용 |
|---|---|---|
| `check_tests_do_not_lean_on_each_other.py` | 파일 하나만 돌려도 통과하는가 (`--reverse-within-file` 모드 포함) | ~50분 |
| `find_unasserted_refusals.py` | 형제 넷의 거부가 도달하고 확인되는가 | 저장소당 수 분 |
| `check_roadmap_shape.py` | 현황판이 현황판 모양인가 — **CI 불가**: ROADMAP.md가 버전 관리 밖 | 1초 |

modelmate에는 같은 성격의 자기 계기가 따로 있다(`scripts/find_unasserted_refusals.py`,
`scripts/measure_part_coverage.py` + `scripts/combine_coverage.py`, `scripts/check_demo_still_demonstrates.py`).

## 필요할 때만

| 도구 | 하는 일 | 비용 |
|---|---|---|
| `mutate.py` | 형제 넷 전체 변이 감사 — 낡으면 `check_mutation_freshness`가 말한다 | ~1.5시간 |
| `sync_repo_descriptions.py` | 설명 숫자를 README에서 읽어 **반영**(쓰기 쪽) — `--apply` | 수 초 |

## 규칙

- **빈손을 통과로 세지 않는다.** 모든 계기는 훑을 것을 못 찾으면 실패한다.
- **대조 없이 믿지 않는다.** 새 계기는 진짜 결함을 심어 무는 것을 확인한 뒤에만 목록에 올린다.
- 새 도구를 만들면 **이 표에 한 줄 추가한다** — 안 하면 `check_tools_inventory.py`가 빨간불을 낸다.
