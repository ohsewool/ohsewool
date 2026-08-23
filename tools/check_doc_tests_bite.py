"""문서를 읽는 검사가 실제로 그 문서에 물려 있는가 — **그리고 몇 개나 그런가.**

다섯 저장소에서 **25개** 테스트 파일이 저장소의 실재하는 문서를 이름으로 읽는다.
(예전 이 자리에는 "52개"라고 적혀 있었다. 손으로 센 값이었고 무엇을 셌는지 다시
알아낼 수 없다 — 지금 수는 아래 `doc_reading_tests()`가 매번 다시 센다.)
그런 검사는 조용히 무의미해지기 쉽다 — 읽는 경로가 바뀌거나, 파서가 다른 것을 읽거나, 단언이 언제나
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

**항목이 물려 있는 것과 항목이 충분한 것은 다르다.** 2026-08-23에 세어보니 열셋 전부
물려 있었고, 그 열셋이 덮는 것은 스물다섯 중 **여섯**이었다. 나머지 열아홉에는
아무 대조도 없었고 **새 검사가 생겨도 아무것도 그것을 묻지 않았다.**

예전 안전장치는 `len(CASES) < 5`였다. 하한선은 목록이 줄어드는 것만 본다 —
**모집단이 목록에서 멀어지는 것은 못 본다.** 이 저장소가 `DECLARED_RECORDS`에서
이미 겪은 모양이다. 이제 모집단을 매번 세고, 대조가 없는 것은 `UNCONTROLLED`에
**이유와 함께 이름으로** 둔다. 새 문서-검사 쌍이 생기면 여기서 걸린다.

    python3 tools/check_doc_tests_bite.py
    python3 tools/check_doc_tests_bite.py --only rag-profile-selector
    python3 tools/check_doc_tests_bite.py --scope-only   # 빠른 범위 확인만
"""

from __future__ import annotations

import argparse
import ast
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPOS = ("agent-safety-core", "mcp-gateway", "rag-profile-selector",
         "document-intelligence", "modelmate")


def doc_reading_tests() -> dict[str, list[str]]:
    """저장소의 **실재하는 문서**를 이름으로 읽는 테스트 파일들.

    문자열 리터럴 중 그 저장소 안의 실재하는 `.md`/`requirements.txt`/`pyproject.toml`을
    가리키는 것만 센다. 이 좁힘에는 이유가 있다 — 처음에는 `README|AGENTS|\.md` 정규식으로
    쟀고 43개가 나왔는데, 그 안에 임시 픽스처(`f.txt`, `/tmp/...`)와 **독스트링에서 문서
    경로를 언급만 하는 산문**이 섞여 있었다. 이 저장소가 열한 번째로 만나는 모양이다:
    **인용과 사용의 혼동.**

    한계도 적어 둔다. 문서를 `docs_dir / name`처럼 조립해 여는 검사는 여기서 안 보인다 —
    `CASES`에 있는 다섯이 실제로 그렇다. 그래서 아래 비교는 `found - covered`만 막고
    `covered - found`는 막지 않는다. **못 보는 것을 못 본다고 적는 것이, 본 척하는 것보다 낫다.**
    """
    found: dict[str, list[str]] = {}
    for repo in REPOS:
        root = ROOT / repo
        for path in sorted((root / "tests").rglob("test_*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            documents = set()
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                    continue
                text = node.value.strip()
                if not text or len(text) > 80 or "\n" in text:
                    continue
                candidate = root / text
                if not (candidate.is_file() and (candidate.suffix == ".md"
                        or candidate.name in ("requirements.txt", "pyproject.toml"))):
                    continue
                documents.add(text)
            if documents:
                found[f"{repo}/{path.relative_to(root)}"] = sorted(documents)
    return found


# 문서를 읽지만 **대조가 없는** 검사들. 비어 있어야 하는 목록이 아니라, 다음에 무엇을
# 걸지 고르는 목록이다. 대조 하나에 pytest 한 번이 걸려 전부 거는 것은 비싸다 —
# 그래서 고르되, **고른 적 없는 것이 조용히 생기지 않게** 한다.
UNCONTROLLED = {
    # `*_doc_paths.py`는 문서가 가리키는 경로가 실재하는지 본다. 문서를 비우면
    # 가리키는 것이 없어져 **당연히 통과한다** — presence 대조가 맞지 않는 형태다.
    # absence로 걸려면 없는 경로를 심어야 하고, 그건 이 검사 자신이 하는 일이다.
    # `agent-safety-core`의 같은 파일은 여기 없다. 그 저장소는 `**/*.md` 글롭으로
    # 문서를 찾아서 **경로 리터럴이 없고**, 그래서 모집단에도 안 잡힌다. 이 목록에
    # 넣었다가 첫 실행에서 "낡았다"로 걸렸다 — 이 검사가 있는 이유 그대로다.
    "mcp-gateway/tests/test_doc_paths.py": "문서를 비우면 통과가 정답인 형태",
    "rag-profile-selector/tests/test_doc_paths.py": "문서를 비우면 통과가 정답인 형태",
    "document-intelligence/tests/test_doc_paths.py": "문서를 비우면 통과가 정답인 형태",
    # 아래는 걸 수 있고 걸어야 하지만 아직 안 걸었다. 대조 하나에 pytest 한 번.
    "agent-safety-core/tests/test_optional_jsonschema.py": "requirements.txt — 다음 회차",
    "agent-safety-core/tests/test_package_resolution.py": "pyproject.toml — 다음 회차",
    "document-intelligence/tests/test_rejections_that_were_never_fired.py": "README.md — 다음 회차",
    "document-intelligence/tests/test_transcribed_provenance.py": "requirements.txt — 다음 회차",
    "mcp-gateway/tests/test_code_that_never_ran.py": "README.md — 다음 회차",
    "modelmate/tests/test_connections_close_on_every_path.py": "README.md — 다음 회차",
    "modelmate/tests/test_declared_dependencies.py": "requirements.txt — 다음 회차",
    "agent-safety-core/tests/test_declared_dependencies.py": "pyproject.toml/requirements.txt — 다음 회차",
    "document-intelligence/tests/test_declared_dependencies.py": "pyproject.toml — 다음 회차",
    "modelmate/tests/test_every_route_has_a_caller.py": "README.md — 다음 회차",
    "modelmate/tests/test_the_explainer_does_not_claim_shap.py": "requirements.txt — 다음 회차",
    "rag-profile-selector/tests/test_rejections_that_were_never_fired.py": "README.md — 다음 회차",
}


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
    Case("modelmate", "docs/coverage-record.json",
         ("tests/test_the_coverage_numbers_are_current.py",), "presence",
         label="README의 커버리지가 마지막 측정과 같다"),

    # 2026-08-23에 더한 여섯. 전부 **문서가 자기 수를 말하는** 검사다 —
    # 이 포트폴리오가 "42개 항목"으로 이미 한 번 당한 자리라 여기부터 걸었다.
    Case("agent-safety-core", "README.md",
         ("tests/test_readme_counts_itself_correctly.py",), "presence",
         label="README가 자기 수를 맞게 센다"),
    Case("mcp-gateway", "requirements.txt",
         ("tests/test_declared_dependencies.py",), "presence",
         label="선언한 의존이 실제와 같다"),
    Case("rag-profile-selector", "README.md",
         ("tests/test_published_corpus_size.py",), "presence",
         label="공개된 코퍼스 크기가 실제와 같다"),
    Case("modelmate", "README.md",
         ("tests/test_readme_counts_itself_correctly.py",), "presence",
         label="README가 자기 수를 맞게 센다"),
    Case("modelmate", "README.md",
         ("tests/test_the_readme_leads_with_the_product.py",), "presence",
         label="README가 제품으로 시작한다"),
    Case("modelmate", "requirements.txt",
         ("tests/test_dependencies_are_pinned.py",), "presence",
         label="의존이 전부 못 박혀 있다"),

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


BACKUP_SUFFIX = ".bite-backup"


def recover_leftovers() -> list[str]:
    """지난번에 죽다 남긴 문서를 되돌린다.

    **이 도구가 나를 물었다.** 문서를 비워 놓고 pytest를 돌린 뒤 `finally`에서
    되돌리는데, 2026-08-23에 다른 작업 중 이 도구를 90초 타임아웃으로 죽였다.
    `SIGTERM`은 `finally`를 돌리지 않는다 — modelmate의 `docs/security-notes.md`와
    `docs/usage-limits.md`가 **0바이트로 남았고**, 몇 단계 뒤에 `git status`를 보고서야
    알았다. 하마터면 빈 문서 둘을 커밋할 뻔했다.

    **검사하려고 만지는 것을 망가뜨린 채 끝날 수 있는 검사기였다.** 이제 셋을 한다.

        1. 비우기 전에 원본을 `<문서>.bite-backup`으로 남긴다
        2. SIGTERM/SIGINT를 받으면 되돌리고 죽는다
        3. 시작할 때 남은 백업이 있으면 **되돌리고 그 사실을 말한다**

    3번이 요점이다. 1·2번이 또 새면 다음 실행이 알아서 고치고, 무엇보다 **조용히
    넘어가지 않는다.**
    """
    recovered = []
    for backup in sorted(ROOT.rglob("*" + BACKUP_SUFFIX)):
        if ".git" in backup.parts:
            continue
        document = backup.with_suffix("")
        if document.suffix == "":     # `README.md.bite-backup` → `README.md`
            document = backup.parent / backup.name[: -len(BACKUP_SUFFIX)]
        document.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        backup.unlink()
        recovered.append(str(document.relative_to(ROOT)))
    return recovered


def bites(case: Case) -> tuple[bool, str]:
    """이 검사가 문서에 물려 있는가. (물림, 설명)"""
    path = ROOT / case.repo / case.document
    if not path.exists():
        return False, "문서가 없다"
    original = path.read_text(encoding="utf-8")
    if not original.strip():
        # **이 대조는 이미 비어 있는 문서에서 자기 자신을 속인다.**
        #
        # presence 대조는 "비우면 실패하는가"를 묻는다. 문서가 **이미** 비어 있으면
        # 비우는 것은 아무 일도 아니고, 검사는 어차피 실패하므로 `✓ 비우면
        # 실패한다`가 나온다 — 확인한 것이 하나도 없이.
        #
        # 실제로 그렇게 됐다. 2026-08-23에 이 도구가 죽임을 당하며
        # `document-intelligence/README.md`를 0바이트로 남겼고, **그 뒤 두 번의 전체
        # 실행이 그 항목을 ✓로 보고했다.** 열아홉 개 초록불 중 하나는 문서가
        # 망가졌다는 뜻이었다.
        return False, "문서가 이미 비어 있다 — 되돌려라(git checkout)"
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    backup.write_text(original, encoding="utf-8")

    def restore_and_die(signum, frame):   # pragma: no cover - 신호 경로
        path.write_text(original, encoding="utf-8")
        backup.unlink(missing_ok=True)
        raise SystemExit(f"\n중단됨 — {case.repo}/{case.document}을 되돌렸다")

    previous = {number: signal.signal(number, restore_and_die)
                for number in (signal.SIGTERM, signal.SIGINT)}
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
        backup.unlink(missing_ok=True)
        for number, handler in previous.items():
            signal.signal(number, handler)


def scope_report() -> int:
    """**목록이 모집단을 다 알고 있는가.**

    항목이 물려 있다는 것과 항목이 충분하다는 것은 다르다. 하한선(`len(CASES) < 5`)은
    목록이 줄어드는 것만 봤고, **모집단이 목록에서 멀어지는 것은 못 봤다.**
    """
    found = doc_reading_tests()
    covered = {f"{case.repo}/{test}" for case in CASES for test in case.tests}
    unaccounted = sorted(set(found) - covered - set(UNCONTROLLED))
    stale = sorted(set(UNCONTROLLED) - set(found))

    print(f"\n문서를 읽는 검사 {len(found)}개 · 대조 있음 "
          f"{len(set(found) & covered)}개 · 이유와 함께 남겨둠 "
          f"{len(set(found) & set(UNCONTROLLED))}개")
    problems = 0
    if unaccounted:
        problems += 1
        print("FAILED — 문서를 읽는데 대조도 없고 목록에도 없는 검사:")
        for name in unaccounted:
            print(f"    {name}  ({', '.join(found[name])})")
        print("  CASES에 넣어 대조를 걸거나, UNCONTROLLED에 **이유와 함께** 넣어라.")
    if stale:
        problems += 1
        print("FAILED — UNCONTROLLED에 있는데 이제 문서를 안 읽는다(낡았다):")
        for name in stale:
            print(f"    {name}")
    if not found:
        problems += 1
        print("FAILED — 문서를 읽는 검사를 하나도 못 찾았다. 훑기가 깨졌으면 "
              "이 검사는 빈손으로 통과한다.")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default=None, help="이 저장소만")
    parser.add_argument("--scope-only", action="store_true",
                        help="대조는 돌리지 않고 범위만 확인한다(빠르다)")
    arguments = parser.parse_args(argv)

    leftovers = recover_leftovers()
    if leftovers:
        print("지난 실행이 되돌리지 못한 문서를 복구했다 — 그때 이 도구는 죽임을 당했다:")
        for name in leftovers:
            print(f"    {name}")
        print()

    if arguments.scope_only:
        return 1 if scope_report() else 0

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
    if arguments.only is None:
        failures += scope_report()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
