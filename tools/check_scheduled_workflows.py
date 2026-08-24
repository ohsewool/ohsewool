"""주간 워크플로의 마지막 실행이 초록불인가 — **주간 빨간불은 아무도 안 본다.**

이 포트폴리오에는 스케줄로만 도는 워크플로가 있다. 값비싼 측정이라 매 push에 못
돌리는 것들이다.

    modelmate/coverage.yml       주간 재측정 — 기록이 현실에서 떠났는가
    modelmate/timezone.yml       세 시간대에서 스위트
    rag-profile-selector/corpus.yml  코퍼스 재수집 + 공개 수치 대조

97회차에 배운 것: **한 번도 돈 적 없는 워크플로는 주장이다** — dispatch로 돌려보니
셋 다 첫 실행에서 죽어 있었다. 이 검사가 지키는 것은 그 다음 문제다: 화요일 새벽에
coverage가 빨간불이 되면 **누가 아는가.** 여섯 저장소의 Actions 탭을 매주 열어볼
사람은 없다. 알림 없는 주간 실패는 몇 주를 조용히 간다 — 늘 빨간불인 것은 아무도
안 보고, **아무도 안 보는 빨간불은 없는 검사다.**

그래서 매 push에 도는 이 저장소의 CI가 **다른 저장소의 마지막 스케줄 실행 결론**을
읽는다. 잡는 것 셋:

    마지막 완료 실행이 실패      워크플로가 지난주에 죽었고 아무도 몰랐다
    실행 이력이 아예 없음        만들어놓고 한 번도 안 돌았다 (97회차의 그 상태)
    마지막 실행이 8일 이상 전    스케줄이 죽었다 — GitHub은 저장소가 60일
                                조용하면 스케줄을 끄고, 그것도 조용히 한다

`counts.yml` 자신은 목록에 없다 — 이전 실행이 빨간불이면 그것을 고치는 실행까지
빨간불이 되는 자기참조가 생긴다.

    python3 tools/check_scheduled_workflows.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

WATCHED = (
    ("ohsewool/modelmate", "coverage.yml"),
    ("ohsewool/modelmate", "timezone.yml"),
    ("ohsewool/rag-profile-selector", "corpus.yml"),
)
MAX_AGE_DAYS = 8


def latest_run(repo: str, workflow: str) -> dict | None:
    finished = subprocess.run(
        ["gh", "run", "list", "-R", repo, "--workflow", workflow, "--limit", "1",
         "--json", "conclusion,status,createdAt,event"],
        capture_output=True, text=True)
    if finished.returncode != 0:
        raise SystemExit(f"FAILED — {repo}/{workflow} 실행 목록을 읽지 못했다: "
                         f"{finished.stderr.strip()[:100]}\n"
                         "  확인 못 한 것을 통과로 세지 않는다.")
    rows = json.loads(finished.stdout)
    return rows[0] if rows else None


def main(argv: list[str] | None = None) -> int:
    problems, checked = [], 0
    now = datetime.now(timezone.utc)
    for repo, workflow in WATCHED:
        run = latest_run(repo, workflow)
        name = f"{repo.split('/')[1]}/{workflow}"
        if run is None:
            problems.append(f"{name}: 실행 이력이 없다 — 만들어놓고 돈 적이 없다")
            print(f"  ✗ {name:36} 실행 이력 없음")
            continue
        checked += 1
        created = datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00"))
        age = (now - created).days
        verdict = run.get("conclusion") or run.get("status")
        mark = "✓"
        if run.get("status") != "completed":
            pass                                   # 도는 중이면 판단 보류
        elif verdict != "success":
            mark = "✗"
            problems.append(f"{name}: 마지막 실행이 {verdict} ({age}일 전, "
                            f"{run.get('event')})")
        if age > MAX_AGE_DAYS:
            mark = "✗"
            problems.append(f"{name}: 마지막 실행이 {age}일 전 — 스케줄이 죽었다")
        print(f"  {mark} {name:36} {verdict:10} {age}일 전 · {run.get('event')}")

    if checked == 0 and not problems:
        print("FAILED — 아무것도 확인하지 못했다.")
        return 1
    if problems:
        print(f"\nFAILED — 주간 워크플로 {len(problems)}건이 조용히 죽어 있다:")
        for line in problems:
            print(f"    {line}")
        return 1
    print(f"\n주간 워크플로 {checked}개의 마지막 실행이 전부 초록불이고 살아 있다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
