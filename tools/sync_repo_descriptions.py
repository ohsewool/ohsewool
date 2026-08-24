"""저장소 설명의 테스트 수를 README에서 읽어 GitHub에 반영한다.

`check_repo_descriptions.py`가 지키는 그 값의 **쓰기 쪽**이다.

### 왜 필요한가

검사를 만든 당일에 두 번 낡았다.

    아침   다섯 전부 낡아 있었다 (1186↔239 등) — 외부 리뷰가 짚었다
    저녁   README를 1193으로 올리며 설명을 또 안 고쳤다 — CI가 잡았다

잡는 쪽은 이제 있다. 문제는 고치는 비용이다 — `gh repo edit`에 문장 전체를
손으로 다시 쓰는 일이라, 매번 미루게 되고 미루면 낡는다. **기억을 고치는 대신
값을 낮춘다**(80회차에 문서 게이트를 9분→87초로 낮춘 것과 같은 이유다).

    python3 tools/sync_repo_descriptions.py           # 무엇이 다른지 보여주기만
    python3 tools/sync_repo_descriptions.py --apply   # 실제 반영

숫자만 바꾼다. 설명 문장 자체는 사람이 쓴 것이고 사람 것으로 남는다 —
`N tests` 부분이 없는 설명은 건드리지 않고 말만 한다.
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
COUNT_IN_DESCRIPTION = re.compile(r"\d+\s*tests")


def readme_count(repo: str) -> int | None:
    path = ROOT / repo / "README.md"
    if not path.exists():
        return None
    found = COUNT_IN_README.search(path.read_text(encoding="utf-8"))
    return int(found.group(1)) if found else None


def gh(args: list[str]) -> str:
    finished = subprocess.run(["gh", *args], capture_output=True, text=True)
    if finished.returncode != 0:
        raise SystemExit(f"FAILED — gh {' '.join(args[:3])}…: "
                         f"{finished.stderr.strip()[:120]}")
    return finished.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="실제로 반영한다 (없으면 보여주기만)")
    options = parser.parse_args(argv)

    drifted, untouchable = [], []
    for repo in REPOS:
        claimed = readme_count(repo)
        if claimed is None:
            untouchable.append(f"{repo}: README에서 `# N tests`를 못 찾았다")
            continue
        description = json.loads(
            gh(["repo", "view", f"ohsewool/{repo}", "--json", "description"])
        ).get("description") or ""
        if not COUNT_IN_DESCRIPTION.search(description):
            untouchable.append(
                f"{repo}: 설명에 `N tests`가 없다 — 문장은 사람 몫이라 안 만든다")
            continue
        wanted = COUNT_IN_DESCRIPTION.sub(f"{claimed} tests", description)
        if wanted == description:
            print(f"  ✓ {repo:24} {claimed} — 이미 같다")
            continue
        drifted.append((repo, description, wanted))
        print(f"  ✗ {repo:24} 설명을 {claimed}(으)로 바꿔야 한다")

    for line in untouchable:
        print(f"  ? {line}")

    if not drifted:
        print("\n반영할 것이 없다.")
        return 1 if untouchable else 0

    if not options.apply:
        print(f"\n{len(drifted)}건이 다르다. 반영하려면 --apply.")
        return 1

    for repo, _old, wanted in drifted:
        gh(["repo", "edit", f"ohsewool/{repo}", "--description", wanted])
        print(f"  → {repo} 반영")
    print(f"\n{len(drifted)}건 반영. 확인: python3 tools/check_repo_descriptions.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
