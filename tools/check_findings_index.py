"""`FINDINGS.md`가 말하는 개수와 실제 항목 수가 같은가.

프로필 `README.md`가 **"42개 항목"**이라고 적고 있었다. 실제로는 58개였다 — 열여섯
회차 동안 항목은 늘고 그 문장은 그대로였다. **이 포트폴리오가 잡아온 종류의 결함이
자기 입구에 있었다.**

기존 검사들이 그것을 못 본 이유가 요점이다. `check_counts.py`는 저장소별 **테스트 수**를
대조하고, `check_anchors.py`는 **링크가 실재하는 제목을 가리키는지** 본다. 항목 수를
세는 것은 아무것도 없었다 — 두 검사 다 초록이었다.

여기서 세 가지를 본다.

    1. `README.md`가 말하는 항목 수 == `FINDINGS.md`의 목차 항목 수
    2. 목차 항목 수 == 실제 `## ` 절 수 (목차 절 자신은 뺀다)
    3. "결함의 모양" 색인이 가리키는 번호가 전부 목차 안에 있다

    python3 tools/check_findings_index.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "FINDINGS.md"
PROFILE = ROOT / "README.md"

# `58개 항목` 또는 `**58개 항목**`
CLAIM = re.compile(r"\*{0,2}(\d+)개 항목")
TOC_ENTRY = re.compile(r"^(\d+)\. \[(.+?)\]\(#(.+?)\)$", re.MULTILINE)
SECTION = re.compile(r"^## (.+)$", re.MULTILINE)
INDEX_REFERENCE = re.compile(r"^- (\d+)\. \[", re.MULTILINE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)

    findings = FINDINGS.read_text(encoding="utf-8")
    profile = PROFILE.read_text(encoding="utf-8")

    toc = TOC_ENTRY.findall(findings)
    sections = [title for title in SECTION.findall(findings)
                if title not in ("목차", "결함의 모양")]
    if not toc:
        print("FAILED — 목차 항목을 하나도 읽지 못했다. 형식이 바뀌었으면 이 검사는 "
              "아무것도 확인하지 않는다.")
        return 1

    problems = []
    numbers = [int(number) for number, _, _ in toc]
    if numbers != list(range(1, len(numbers) + 1)):
        gaps = [n for i, n in enumerate(numbers, start=1) if n != i]
        problems.append(f"목차 번호가 이어지지 않는다: {gaps[:5]}")

    if len(toc) != len(sections):
        problems.append(f"목차 {len(toc)}개인데 절은 {len(sections)}개다")

    claimed = CLAIM.search(profile)
    if not claimed:
        problems.append("README에서 '<N>개 항목'을 찾지 못했다 — 문장이 바뀌었으면 "
                        "이 검사는 빈손으로 통과한다")
    elif int(claimed.group(1)) != len(toc):
        problems.append(f"README는 {claimed.group(1)}개라 하는데 목차는 {len(toc)}개다")

    known = {int(number) for number, _, _ in toc}
    referenced = {int(number) for number in INDEX_REFERENCE.findall(findings)}
    if not referenced:
        problems.append("'결함의 모양' 색인이 아무 항목도 가리키지 않는다")
    unknown = sorted(referenced - known)
    if unknown:
        problems.append(f"색인이 없는 항목을 가리킨다: {unknown}")

    print(f"목차 {len(toc)}개 · 절 {len(sections)}개 · "
          f"README 주장 {claimed.group(1) if claimed else '없음'}개 · "
          f"색인이 가리키는 항목 {len(referenced)}개")
    for problem in problems:
        print(f"FAILED — {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
