"""마지막 변이 감사가 언제였는지, 그리고 그게 너무 오래됐는지.

`tools/mutate.py`는 다섯 저장소의 안전장치 27개를 하나씩 무력화하고 스위트가
빨간불을 내는지 본다. 탐침마다 그 저장소의 스위트를 통째로 돌리므로 **한 시간 반**이
걸리고, 그래서 매 push에 돌릴 수 없다.

문제는 "그럼 가끔 손으로"가 실제로는 **여러 회차 동안 아무도 안 돌리는 상태**가
된다는 것이다. 그동안 그 도구 자체에 구멍이 있었다 — 치환이 문법을 깨뜨리면 스위트가
빨개지고 도구는 그것을 "잡힘"으로 읽었다. 안 돌렸으니 아무도 몰랐다.

그래서 **마지막으로 돌린 날짜를 문서에 적고 그 날짜를 검사한다.** 낡으면 CI가
말한다. 검사를 자동으로 돌리지는 못해도, 안 돌린 채 잊히는 것은 막을 수 있다.

날짜를 이 파일에 박지 않고 `FINDINGS.md`에서 읽어온다. 박아두면 문서와 코드가 갈릴
때 어느 편을 들지 알 수 없고, 읽어오면 둘 중 하나가 움직이는 순간 걸린다 —
`document-intelligence`에서 공개된 구역 수를 검사할 때 쓴 것과 같은 이유다.

    python3 tools/check_mutation_freshness.py
    python3 tools/check_mutation_freshness.py --max-age-days 60
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "FINDINGS.md"

# `**마지막 전체 변이 감사: 2026-08-22 — 27/27 잡힘, 대조 5/5 안 잡힘.**`
RECORD = re.compile(
    r"마지막 전체 변이 감사:\s*(\d{4}-\d{2}-\d{2})\s*—\s*(\d+)/(\d+)\s*잡힘"
    r"[^0-9]*(\d+)/(\d+)\s*안 잡힘"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-age-days", type=int, default=45,
                        help="이 일수를 넘으면 실패한다")
    parser.add_argument("--today", type=str, default=None,
                        help="기준 날짜 (테스트용)")
    arguments = parser.parse_args(argv)

    if not FINDINGS.exists():
        print(f"FAILED — {FINDINGS.name}이 없다. 읽을 기록이 없으면 이 검사는 "
              f"아무것도 확인하지 않는다.")
        return 1

    match = RECORD.search(FINDINGS.read_text(encoding="utf-8"))
    if not match:
        # 기록이 사라진 것과 오래된 것은 다르다. 둘 다 실패지만 이유가 다르고,
        # 같은 메시지로 묶으면 고칠 방법도 같아 보인다.
        print("FAILED — FINDINGS.md에서 마지막 변이 감사 기록을 찾지 못했다.\n"
              "         `**마지막 전체 변이 감사: YYYY-MM-DD — N/N 잡힘, 대조 M/M 안 잡힘.**`\n"
              "         형태의 줄이 있어야 한다.")
        return 1

    stamp, caught, probes, uncaught_controls, controls = match.groups()
    when = datetime.strptime(stamp, "%Y-%m-%d").date()
    today = datetime.strptime(arguments.today, "%Y-%m-%d").date() if arguments.today else date.today()
    age = (today - when).days

    print(f"마지막 전체 변이 감사: {stamp} ({age}일 전)")
    print(f"  변이 {caught}/{probes} 잡힘, 음성 대조 {uncaught_controls}/{controls} 안 잡힘")

    problems = []
    if age > arguments.max_age_days:
        problems.append(f"{age}일 전이다 (한도 {arguments.max_age_days}일). "
                        f"`python3 tools/mutate.py`를 돌리고 날짜를 갱신하라.")
    if age < -1:
        # 미래 날짜는 기록이 아니라 오타다. 통과시키면 영원히 신선해 보인다.
        #
        # 하루는 봐준다. 기록하는 기계와 검사하는 기계의 시간대가 다르면 -
        # 여기서는 KST에서 적고 CI(UTC)에서 읽는다 - 몇 시간 동안 "내일"로 보인다.
        # **검사하려는 것과 무관한 이유로 빨간불이 되는 검사**는 이 프로젝트가
        # 반복해서 경고한 실패다: 확인 못 한 것과 틀린 것이 같은 표시 뒤로 숨는다.
        problems.append(f"{stamp}은 하루 넘게 미래다. 기록이 아니라 오타일 것이다.")
    if caught != probes:
        problems.append(f"기록된 결과가 {caught}/{probes}이다 — 잡히지 않은 변이가 남아 있다.")
    if uncaught_controls != controls:
        problems.append(f"음성 대조 {uncaught_controls}/{controls} — 대조가 하나라도 "
                        f"잡히면 그 회차 결과는 전부 무효다.")

    for problem in problems:
        print(f"FAILED — {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
