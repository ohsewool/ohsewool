"""GitHub 저장소 **설명(description)**의 테스트 수가 README와 같은가.

2026-08-24에 외부 리뷰가 짚었고, 재보니 그대로였다.

    저장소                  README   설명
    modelmate               1186     239
    agent-safety-core        565     273
    mcp-gateway              379     124
    rag-profile-selector     348     150
    document-intelligence    234      52

**다섯 전부 틀렸다.** 어떤 것은 다섯 배 가까이 차이 난다.

### 왜 아무도 못 봤는가

이 저장소에는 개수를 지키는 도구가 여럿 있다.

    check_counts.py          프로필 표 ↔ 각 저장소 README
    check_findings_index.py  FINDINGS 항목 수 ↔ README 주장
    각 저장소 CI             자기 README ↔ `pytest --collect-only`

전부 **파일**을 본다. 그런데 저장소 설명은 파일이 아니다 — GitHub 메타데이터라
어느 체크아웃에도 들어 있지 않다. *검사가 닿지 않는 주장 표면이 하나 있었고,
그것이 하필 사람들이 가장 먼저 보는 자리였다.*

목록 화면에서 저장소 이름 옆에 붙는 한 줄이 그것이다. README를 열기 전에 보는 것.

### 왜 이 어긋남이 특히 나쁜가

이 포트폴리오가 내세우는 문장이 *"검증되지 않은 초록불을 믿지 않는다"*이다.
그 주장을 하는 첫 화면의 숫자가 다섯 배 틀려 있으면, 읽는 사람이 의심하는 것은
숫자가 아니라 **그 문장**이다.

    python3 tools/check_repo_descriptions.py            # GitHub API로 확인
    python3 tools/check_repo_descriptions.py --local ..  # 형제 체크아웃의 README와만 대조

`gh`가 없거나 인증이 없으면 **건너뛰지 않고 실패한다.** 확인하지 못한 것을 통과로
세면 이 검사도 없는 것과 같다.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPOS = ("agent-safety-core", "modelmate", "rag-profile-selector",
         "mcp-gateway", "document-intelligence")

COUNT_IN_README = re.compile(r"#\s*(\d+)\s*tests")
COUNT_IN_DESCRIPTION = re.compile(r"(\d+)\s*tests")


def readme_count(repo: str) -> int | None:
    path = ROOT / repo / "README.md"
    if not path.exists():
        return None
    found = COUNT_IN_README.search(path.read_text(encoding="utf-8"))
    return int(found.group(1)) if found else None


def description(repo: str) -> str:
    finished = subprocess.run(
        ["gh", "repo", "view", f"ohsewool/{repo}", "--json", "description"],
        capture_output=True, text=True)
    if finished.returncode != 0:
        raise SystemExit(
            f"FAILED — {repo}의 설명을 읽지 못했다: {finished.stderr.strip()[:120]}\n"
            "  `gh` 인증이 없으면 확인할 수 없다. **확인 못 한 것을 통과로 세지 않는다.**")
    return json.loads(finished.stdout).get("description") or ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", type=Path, default=None,
                        help="형제 체크아웃 위치(기본: 이 저장소의 상위)")
    parser.parse_args(argv)

    problems, checked = [], 0
    for repo in REPOS:
        claimed = readme_count(repo)
        if claimed is None:
            problems.append(f"{repo}: README에서 `# N tests`를 못 찾았다")
            continue
        text = description(repo)
        found = COUNT_IN_DESCRIPTION.search(text)
        if not found:
            problems.append(f"{repo}: 설명에 테스트 수가 없다 — {text[:50]!r}")
            continue
        checked += 1
        shown = int(found.group(1))
        mark = "✓" if shown == claimed else "✗"
        print(f"  {mark} {repo:24} README {claimed:<6} 설명 {shown}")
        if shown != claimed:
            problems.append(f"{repo}: 설명은 {shown}, README는 {claimed}")

    if not checked:
        # 빈손을 통과로 세지 않는다.
        print("FAILED — 설명을 하나도 확인하지 못했다.")
        return 1
    if problems:
        print(f"\nFAILED — 저장소 설명이 README와 어긋난다 ({len(problems)}건):")
        for problem in problems:
            print(f"    {problem}")
        print("  고치는 법: gh repo edit ohsewool/<repo> --description \"... N tests\"")
        return 1
    print(f"\n설명 {checked}개가 전부 README와 같은 수를 말한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
