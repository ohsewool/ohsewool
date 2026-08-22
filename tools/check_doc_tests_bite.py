"""문서를 읽는 검사가 실제로 그 문서에 물려 있는가.

다섯 저장소에서 52개 테스트 파일이 문서나 소스를 문자열로 읽는다. 그런 검사는 조용히
무의미해지기 쉽다 — 읽는 경로가 바뀌거나, 파서가 다른 것을 읽거나, 단언이 언제나
참인 형태가 되면 초록불은 그대로다.

**대조를 걸어 확인한다. 다만 방향이 둘이다.**

`presence`
    "이 숫자/문구가 문서에 있고 실행 결과와 같다"를 단언하는 검사. 문서를 **비우면**
    실패해야 한다. 통과하면 그 검사는 문서를 읽지 않는다.

`absence`
    "낡은 주장이 어디에도 없다"를 단언하는 검사. 비우면 **당연히 통과한다** — 주장도
    함께 사라지니까. 여기서는 반대로 **심어야** 한다. 심었는데 통과하면 못 잡는 것이다.

이 구분이 이 도구가 존재하는 이유다. 2026-08-22에 열두 건을 손으로 훑다가 두 건이
"비워도 통과"로 나왔다. 하나는 내가 경로를 잘못 짚은 것이었고(`benchmark/README.md`를
루트 `README.md`로 봤다), 다른 하나는 **부재를 단언하는 검사에 비우기 대조를 건 것**
이었다. 둘 다 결함처럼 보였고 둘 다 내 실수였다. 방향을 맞춰 다시 거니 열두 건 모두
물려 있었다.

**그 두 번을 기억에 맡기지 않으려고 목록으로 만든다.** 새 문서-검사 쌍이 생기면 여기
추가하는 것이 그 검사가 살아 있다는 증거다.

    python3 tools/check_doc_tests_bite.py
    python3 tools/check_doc_tests_bite.py --only rag-profile-selector
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Case:
    repo: str
    document: str
    tests: tuple[str, ...]
    mode: str              # "presence" | "absence"
    plant: str = ""        # absence일 때 심을 문구
    label: str = ""


CASES = (
    # presence — 문서에서 값을 읽어 실행 결과와 맞춰보는 검사들
    Case("agent-safety-core", "benchmark/README.md",
         ("tests/test_published_benchmark.py",), "presence",
         label="벤치마크 표가 실행 결과와 같다"),
    Case("mcp-gateway", "AGENTS.md",
         ("tests/test_instructions_current.py",), "presence",
         label="지시 파일이 지금을 서술한다"),
    Case("mcp-gateway", "docs/PROJECT_SPEC.md",
         ("tests/test_denial_disclosure.py",), "presence",
         label="정찰이 승인된 위협 집합에 없다"),
    Case("mcp-gateway", "docs/TASKS.md",
         ("tests/test_denial_disclosure.py",), "presence",
         label="정찰이 NEEDS_APPROVAL에 올라 있다"),
    Case("rag-profile-selector", "AGENTS.md",
         ("tests/test_instructions_current.py",), "presence",
         label="지시 파일이 지금을 서술한다"),
    Case("rag-profile-selector", "experiments/KR_LAW_RESULTS.md",
         ("tests/test_published_profiles.py",), "presence",
         label="실험이 돌린 프로파일 = 표에 실린 프로파일"),
    Case("document-intelligence", "AGENTS.md",
         ("tests/test_instructions_current.py",), "presence",
         label="지시 파일이 지금을 서술한다"),
    Case("document-intelligence", "README.md",
         ("tests/test_pdfplumber_adapter.py",), "presence",
         label="공개된 구역 수가 파싱 결과와 같다"),
    Case("modelmate", "README.md",
         ("tests/test_no_dead_deployment_links.py",), "presence",
         label="죽은 배포 링크가 없다"),
    Case("modelmate", "docs/security-notes.md",
         ("tests/test_login_does_not_leak_accounts.py",), "presence",
         label="가입 노출이 선택임을 적어뒀다"),
    Case("modelmate", "docs/usage-limits.md",
         ("tests/test_one_definition_of_today.py",), "presence",
         label="'오늘'이 서버의 하루임을 적어뒀다"),

    # absence — 낡은 주장이 없음을 단언하는 검사. 비우기가 아니라 심기로 확인한다.
    Case("rag-profile-selector", "README.md",
         ("tests/test_no_stale_status.py",), "absence",
         plant="\nThere are no empirical findings.\n",
         label="낡은 상태 문구를 잡는다"),
    Case("rag-profile-selector", "README.md",
         ("tests/test_no_stale_status.py",), "absence",
         plant="\n이 실험은 HotpotQA 코퍼스를 쓴다.\n",
         label="쓰지 않는 코퍼스 이름을 잡는다"),
)


def bites(case: Case) -> tuple[bool, str]:
    """이 검사가 문서에 물려 있는가. (물림, 설명)"""
    path = ROOT / case.repo / case.document
    if not path.exists():
        return False, "문서가 없다"
    original = path.read_text(encoding="utf-8")
    try:
        if case.mode == "presence":
            path.write_text("", encoding="utf-8")
        elif case.mode == "absence":
            if not case.plant:
                return False, "absence인데 심을 문구가 없다"
            path.write_text(original + case.plant, encoding="utf-8")
        else:
            return False, f"알 수 없는 mode: {case.mode}"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *case.tests, "-q",
             "-p", "no:cacheprovider", "--no-header"],
            cwd=ROOT / case.repo, capture_output=True, text=True, timeout=1800)
        return result.returncode != 0, ""
    finally:
        path.write_text(original, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default=None, help="이 저장소만")
    arguments = parser.parse_args(argv)

    cases = [case for case in CASES
             if arguments.only is None or case.repo == arguments.only]
    if not cases:
        print(f"FAILED — 돌릴 항목이 없다 (--only {arguments.only}). "
              f"아무것도 확인하지 않았다.")
        return 1

    failures, repo = 0, None
    for case in cases:
        if case.repo != repo:
            repo = case.repo
            print(f"\n{repo}")
        bit, note = bites(case)
        failures += not bit
        how = "비우면" if case.mode == "presence" else "심으면"
        mark = f"{how} 실패한다" if bit else f"{how}도 통과한다 — 물려 있지 않다"
        print(f"  {'✓' if bit else '✗'} {case.label:<44} {mark}{(' (' + note + ')') if note else ''}")

    print(f"\n{len(cases) - failures}/{len(cases)} 물려 있다")
    if len(cases) < 5 and arguments.only is None:
        # 목록이 줄어들면 "전부 물려 있다"가 점점 적은 것을 뜻하게 된다.
        # 아무것도 확인하지 않으면서 초록불인 상태를 막는다.
        print(f"FAILED — 항목이 {len(cases)}개뿐이다. 목록이 줄었는지 확인하라.")
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
