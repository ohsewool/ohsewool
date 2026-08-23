"""문서를 고친 뒤 밀기 전에 돌린다 — 문서를 읽는 검사만, 몇 초 안에.

**같은 실수를 두 번 했다.** 스위트를 돌리고, 그다음 README를 고치고, 다시 안 돌린 채
밀었다. 두 번 다 CI가 잡았다.

    2026-08-23  document-intelligence  README를 224로 고치고 AGENTS.md는 안 고쳤다
    2026-08-24  modelmate              README에 `/api/columns`를 적었더니 그 라우트가
                                       "누가 부르는 라우트"가 됐다(울타리 밖)

첫 번째 뒤에 **"문서를 읽는 검사가 있는 저장소에서는 문서 수정도 코드 수정이다"**라고
적어뒀다. 그리고 두 번째를 했다. **적어둔 교훈과 지키는 것은 다른 일이다.**

기억을 고치는 대신 값을 낮춘다. 전체 스위트는 modelmate만 9분이지만 **문서를 읽는
검사는 27개 파일뿐이고 전부 합쳐 1분이 안 걸린다.** 문서를 만졌으면 이것만 돌리면 된다.

목록은 **여기서 새로 만들지 않는다.** `check_doc_tests_bite.py`가 이미 "저장소의
실재하는 문서를 이름으로 읽는 검사"를 세고 있고, 그것을 그대로 쓴다 — 두 곳에 적으면
한 곳만 낡는다.

    python3 tools/check_docs_still_agree.py               # 다섯 저장소 전부
    python3 tools/check_docs_still_agree.py modelmate     # 하나만

**전체 스위트를 대신하지 않는다.** 문서를 읽는 검사만 본다. 코드를 고쳤으면 스위트를
돌려야 한다.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_doc_tests_bite import doc_reading_tests  # noqa: E402


def by_repo() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for key in doc_reading_tests():
        repo, _, relative = key.partition("/")
        grouped[repo].append(relative)
    return grouped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", default=None, help="이 저장소만")
    arguments = parser.parse_args(argv)

    grouped = by_repo()
    if not grouped:
        # **빈손을 통과로 세지 않는다.** 목록이 깨지면 이 도구는 아무것도 안 돌리고
        # 초록불을 낸다 — 이 포트폴리오가 여러 번 잡은 모양이다.
        print("FAILED — 문서를 읽는 검사를 하나도 못 찾았다. 목록이 깨졌는지 확인하라.")
        return 1
    if arguments.repo:
        if arguments.repo not in grouped:
            print(f"FAILED — {arguments.repo}에는 문서를 읽는 검사가 없다. "
                  f"있는 것: {sorted(grouped)}")
            return 1
        grouped = {arguments.repo: grouped[arguments.repo]}

    failures, started = 0, time.perf_counter()
    for repo, files in sorted(grouped.items()):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *sorted(files), "-q", "--no-header",
             "-p", "no:cacheprovider"],
            cwd=ROOT / repo, capture_output=True, text=True)
        # pytest의 색 코드를 걷어낸다. 안 걷으면 요약 줄이 잘려 나가 **초록불인지
        # 빨간불인지가 화면에서 안 보인다** — 읽을 수 없는 보고는 보고가 아니다.
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        summary = next((line for line in reversed(plain.splitlines())
                        if "passed" in line or "failed" in line or "error" in line), "")
        mark = "✓" if result.returncode == 0 else "✗"
        print(f"  {mark} {repo:24} 파일 {len(files):2}개  {summary.strip()[:52]}")
        if result.returncode != 0:
            failures += 1
            for line in plain.splitlines():
                if "FAILED" in line or "Error" in line:
                    print(f"        {line.strip()[:110]}")

    elapsed = time.perf_counter() - started
    total = sum(len(files) for files in grouped.values())
    print(f"\n{len(grouped)}개 저장소 · 파일 {total}개 · {elapsed:.1f}초")
    if failures:
        print(f"FAILED — {failures}개 저장소에서 문서와 검사가 어긋난다.")
        return 1
    print("문서와 검사가 서로를 부정하지 않는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
