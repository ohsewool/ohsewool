"""도달하는데 아무도 확인하지 않는 거부를 형제 저장소에서 찾는다.

거부에는 세 가지 상태가 있고 초록불은 셋을 구별하지 않는다.

    한 번도 도달하지 않는다      커버리지가 말해준다
    도달하고 확인된다            바꾸면 검사가 빨간불이 된다
    **도달하는데 확인되지 않는다**  ← 커버리지는 "돌았다"고 하고 검사는 통과한다

형제 넷은 **분기 커버리지 100% 관문**을 갖고 있다. 그래서 `raise` 자리는 전부
도달한다 — 관문이 답할 수 없는 것이 정확히 마지막 줄이다.

`modelmate`에는 같은 질문을 HTTP 거부로 물은 도구가 있다
(`modelmate/scripts/find_unasserted_refusals.py`). 여기는 라이브러리라 도메인 예외를
던지므로 `HTTPException.__init__`을 가로챌 수 없다. 대신 **coverage의 동적 컨텍스트**를
쓴다 — `dynamic_context = test_function`이면 줄마다 "어느 검사가 이 줄을 실행했나"가
남는다.

**변이는 `raise X(...)` → `raise Exception(...)`이다.** 기본 클래스로 바꾼다.

    pytest.raises(구체적예외)  →  안 잡힌다 → 빨간불 → **확인됨**
    pytest.raises(Exception)   →  잡힌다   → 초록불 → **확인 안 됨**

`pass`로 바꾸지 않는 이유가 있다. 그러면 함수가 계속 흘러 엉뚱한 데서 죽고, 그
실패를 "확인됨"으로 읽게 된다. 형제 저장소의 앞선 감사는 `pass`를 썼고 그건
**"발동한 적이 있는가"**를 묻는 도구다. 이 도구는 **"무엇이 왔는지 묻는가"**를 묻는다.

원래가 이미 `Exception`인 자리는 구별할 수 없다. **그런 자리는 0으로 세지 않고
"재지 못한 지점"으로 따로 찍는다** — 조용히 빼면 이 도구도 초록불이 된다.

`raise NotImplementedError`(괄호 없음)도 그 목록에 뜬다. **그건 거부가 아니라
추상 메서드 표시**이고, 재지 못하는 것이 맞다. 2026-08-23 기준 그런 자리가
`mcp-gateway`와 `rag-profile-selector`에 하나씩 있다.

2026-08-23 결과:

    저장소                    raise  도달  확인 안 됨
    agent-safety-core          86    85      1   ← core/payload.py:242
    document-intelligence      79    77      0
    mcp-gateway                56    51      0
    rag-profile-selector       54    51      0

**분기 커버리지 100% 관문이 사는 것이 여기서 보인다.** 형제 넷은 거부가 거의 전부
도달하고 거의 전부 확인된다. 같은 도구를 `modelmate`(관문 없음)에 돌렸을 때는
108개 중 49개만 도달했고 그중 여섯이 확인되지 않았다.

**관문이 아니다.** 저장소 하나에 수십 분 걸린다.

    python3 tools/find_unasserted_refusals.py agent-safety-core
    python3 tools/find_unasserted_refusals.py mcp-gateway --trace-only
"""

from __future__ import annotations

import argparse
import ast
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "agent-safety-core": "core,adapters,profiles",
    "mcp-gateway": "mcp_gateway",
    "rag-profile-selector": "rag_profile_selector",
    "document-intelligence": "document_intelligence",
}


def source_dirs(repo: str) -> list[Path]:
    base = ROOT / repo
    found = []
    for name in SOURCES[repo].split(","):
        for candidate in (base / name, base / "src" / name):
            if candidate.exists():
                found.append(candidate)
                break
    return found


def raise_sites(repo: str) -> dict[tuple[str, int], tuple[str, str]]:
    """(파일, 줄) -> (던지는 클래스, 감싸는 함수)."""
    sites = {}
    for directory in source_dirs(repo):
        for path in sorted(directory.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            holder = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for inner in ast.walk(node):
                        holder[id(inner)] = node.name
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Raise) and node.exc is not None):
                    continue
                raised = node.exc
                name = ast.unparse(raised.func) if isinstance(raised, ast.Call) \
                    else ast.unparse(raised)
                sites[(str(path.relative_to(ROOT / repo)), node.lineno)] = (
                    name, holder.get(id(node), "<module>"))
    return sites


def trace(repo: str) -> dict[tuple[str, int], set[str]]:
    """줄마다 그 줄을 실행한 검사들. coverage의 동적 컨텍스트를 읽는다."""
    base = ROOT / repo
    config = base / ".coveragerc-unasserted"
    config.write_text(
        "[run]\ndynamic_context = test_function\nbranch = True\n"
        f"source = {SOURCES[repo]}\n", encoding="utf-8")
    try:
        subprocess.run([sys.executable, "-m", "coverage", "run",
                        "--rcfile", str(config), "-m", "pytest", "-q"],
                       cwd=base, capture_output=True, text=True)
    finally:
        # **`finally`가 아니면 중단될 때 형제 저장소에 남는다.** 2026-08-24에
        # 실행 중인 감사를 껐더니 `document-intelligence`에 `.coveragerc-unasserted`가
        # 그대로 남았다(`git status`에 `??`로 떴다). 이 저장소들은 같은 모양을 이미
        # 겪었다 — QA 스크립트가 업로드한 CSV를 안 지워 저장소가 매번 커졌고, 그
        # 파일들이 커밋돼 픽스처처럼 앉아 있었다.
        #
        # 스위트가 몇 분 걸리는 도구라 사람이 중간에 끊는 일은 예외가 아니라 기본에
        # 가깝다. 정상 경로에서만 지우는 것은 지우지 않는 것과 비슷하다.
        config.unlink(missing_ok=True)

    database = base / ".coverage"
    if not database.exists():
        raise SystemExit(f"{repo}: coverage 데이터가 없다 — 추적이 돌지 않았다")
    connection = sqlite3.connect(database)
    by_line: dict[tuple[str, int], set[str]] = defaultdict(set)

    # **`branch = True`면 줄은 `line_bits`가 아니라 `arc`에 남는다.**
    # 처음엔 `line_bits`만 읽었고 "줄 0개에 검사가 붙었다"가 나왔다 — 도구가
    # 빈손인데 조용히 0을 보고한 것이다. 두 표를 다 읽고, 그래도 0이면 죽는다.
    query = """
        SELECT file.path, arc.tono, context.context
        FROM arc
        JOIN file ON file.id = arc.file_id
        JOIN context ON context.id = arc.context_id
        WHERE arc.tono > 0
    """
    for path, line, context in connection.execute(query):
        if not context:
            continue
        try:
            relative = str(Path(path).relative_to(base))
        except ValueError:
            continue
        by_line[(relative, line)].add(context.split("|")[0])

    if not by_line:
        try:
            from coverage.numbits import numbits_to_nums
            for path, numbits, context in connection.execute(
                    "SELECT file.path, line_bits.numbits, context.context FROM line_bits "
                    "JOIN file ON file.id = line_bits.file_id "
                    "JOIN context ON context.id = line_bits.context_id"):
                if not context:
                    continue
                try:
                    relative = str(Path(path).relative_to(base))
                except ValueError:
                    continue
                for line in numbits_to_nums(numbits):
                    by_line[(relative, line)].add(context.split("|")[0])
        except Exception:
            pass
    connection.close()
    if not by_line:
        raise SystemExit(
            f"{repo}: 줄에 붙은 검사가 하나도 없다. 빈손을 0으로 보고하지 않는다 — "
            "coverage 스키마가 바뀌었는지 확인하라.")
    return by_line


def sweep(repo: str, by_line) -> int:
    base = ROOT / repo
    sites = raise_sites(repo)
    unasserted, unmeasured, checked = [], [], 0

    for (relative, line), (raised, function) in sorted(sites.items()):
        tests = by_line.get((relative, line), set())
        if not tests:
            continue                                   # 도달하지 않는다 — 다른 질문이다
        if raised in ("Exception", "BaseException"):
            unmeasured.append(f"{relative}:{line} (원래가 이미 {raised})")
            continue
        path = base / relative
        original = path.read_bytes()
        lines = original.decode("utf-8").splitlines(keepends=True)
        mutated = re.sub(r"raise\s+[\w.]+\(", "raise Exception(", lines[line - 1], count=1)
        if mutated == lines[line - 1]:
            unmeasured.append(f"{relative}:{line} (심을 수 없는 형태)")
            continue
        lines[line - 1] = mutated
        path.write_bytes("".join(lines).encode("utf-8"))
        selected = sorted(
            "tests/" + name.split(".")[0] + ".py::" + "::".join(name.split(".")[1:])
            for name in tests if name)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", *selected, "-q", "--no-header",
                 "-p", "no:cacheprovider"],
                cwd=base, capture_output=True, text=True)
        finally:
            path.write_bytes(original)
        checked += 1
        if result.returncode == 0:
            unasserted.append((f"{relative}:{line}", function, raised, len(tests)))
        print(f"  {'확인 안 됨' if result.returncode == 0 else '확인됨':12} "
              f"{relative + ':' + str(line):44} {function:28} {raised:22} "
              f"검사 {len(tests)}개", flush=True)

    print(f"\n{repo}: 도달하는 raise {checked}개 · **확인되지 않는 것 {len(unasserted)}개**")
    for where, function, raised, count in unasserted:
        print(f"    {where:44} {function}  raise {raised}  (검사 {count}개가 지나간다)")
    if unmeasured:
        print(f"\n재지 못한 지점 {len(unmeasured)}개:")
        for entry in unmeasured:
            print(f"    {entry}")
    return 1 if unasserted else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", choices=sorted(SOURCES))
    parser.add_argument("--trace-only", action="store_true")
    arguments = parser.parse_args(argv)

    print(f"1단계: {arguments.repo} 스위트를 컨텍스트와 함께 돌린다")
    by_line = trace(arguments.repo)
    print(f"  줄 {len(by_line)}개에 검사가 붙었다")
    if arguments.trace_only:
        return 0
    print("2단계: raise마다 기본 Exception으로 바꾸고 그 줄을 지나는 검사만 돌린다")
    return sweep(arguments.repo, by_line)


if __name__ == "__main__":
    raise SystemExit(main())
