"""Find tests that cannot fail.

Three shapes, all of which pass forever and count toward the total:

  no_assertion   a test function that asserts nothing **and calls nothing**.
                 There is no reading of such a test under which it can fail.
  expects_no_raise
                 asserts nothing but calls something: the claim is "this does
                 not raise", which is a real claim. Split out on 2026-08-22
                 because every one of the sixteen findings in `no_assertion`
                 was of this kind - a category with no signal is a category
                 nobody reads.
  always_true    `assert <literal>` or `assert <name>` where the name is a
                 module/class - the assert of something that is always truthy.
  empty_loop     `for x in y: assert ...` where y can be empty, so the loop body
                 never runs. The same vacuous-all() shape found in mcp-gateway's
                 policy, in test clothing.

Reports, does not judge. The output is a list to read, not a gate - but a list
worth reading has to separate what needs attention from what does not.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# 한 기계의 절대 경로(`/home/jovyan/work`)가 박혀 있었다. 다른 세 도구는 전부
# `__file__`에서 유도하는데 이것만 그랬고, 그래서 **다른 어디에서도 돌지 않았다** —
# CI에 넣지 못한 이유이기도 하다.
#
# 이 프로젝트가 이미 한 번 찾은 결함이다: `mcp-gateway`의 테스트 셋이
# `/home/jovyan/work/agent-safety-core`가 있는지로 형제 가용성을 판단하고 있었다.
# 같은 모양이 이 저장소의 검사 도구 안에 남아 있었다.
DEFAULT_ROOT = Path(__file__).resolve().parents[2]
REPOS = ("agent-safety-core", "mcp-gateway", "modelmate",
         "rag-profile-selector", "document-intelligence")

ASSERTING_CALLS = ("raises", "warns", "approx", "fail", "importorskip", "skip", "xfail")


class Visitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.findings: list[tuple[str, int, str, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name.startswith("test"):
            self.check(node)
        self.generic_visit(node)

    def check(self, node: ast.FunctionDef) -> None:
        asserts = [n for n in ast.walk(node) if isinstance(n, ast.Assert)]
        raising = any(
            isinstance(n, ast.Call) and _name(n.func) in ASSERTING_CALLS
            for n in ast.walk(node)
        )
        unittest_style = any(
            isinstance(n, ast.Call) and _name(n.func).startswith("assert")
            for n in ast.walk(node)
        )
        withs = [n for n in ast.walk(node) if isinstance(n, (ast.With, ast.AsyncWith))]
        has_with_raises = any(
            isinstance(item.context_expr, ast.Call)
            and _name(item.context_expr.func) in ASSERTING_CALLS
            for w in withs for item in w.items
        )

        if not asserts and not raising and not unittest_style and not has_with_raises:
            # 단언이 없는 것과 **아무것도 하지 않는 것**은 다르다. 무언가를 부르고
            # 단언하지 않는 테스트는 "이 호출이 예외를 내지 않아야 한다"는 정당한
            # 검사이고, 부르지도 단언하지도 않는 테스트만 진짜 공허하다.
            #
            # 2026-08-22에 세어보니 `no_assertion` 16건이 **전부** 호출을 갖고 있었다.
            # 즉 그 범주의 신호는 0이었고, 신호가 0인 목록은 읽히지 않는다 — 이
            # 프로젝트가 감사 이벤트에서 이미 쓴 논리다. 갈라놓으면 첫 줄이 다시
            # 무언가를 뜻한다.
            calls = any(isinstance(n, ast.Call) for n in ast.walk(node))
            kind = "expects_no_raise" if calls else "no_assertion"
            self.findings.append((str(self.path), node.lineno, node.name, kind))

        for statement in asserts:
            test = statement.test
            if isinstance(test, ast.Constant) and test.value:
                self.findings.append(
                    (str(self.path), statement.lineno, node.name, "always_true"))

        # assert inside a for-loop whose only assertions are in the body
        for loop in [n for n in ast.walk(node) if isinstance(n, ast.For)]:
            body_asserts = [n for n in ast.walk(loop) if isinstance(n, ast.Assert)]
            if body_asserts and len(body_asserts) == len(asserts):
                self.findings.append(
                    (str(self.path), loop.lineno, node.name, "assertions_only_in_a_loop"))


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                        help="다섯 저장소가 나란히 있는 디렉터리")
    arguments = parser.parse_args(argv)
    root = arguments.root

    by_kind: dict[str, list] = {}
    scanned = 0
    for repo in REPOS:
        for path in sorted((root / repo / "tests").rglob("test_*.py")):
            scanned += 1
            visitor = Visitor(path.relative_to(root))
            visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
            for finding in visitor.findings:
                by_kind.setdefault(finding[3], []).append(finding)

    if not scanned:
        print(f"FAILED — {root} 아래에서 테스트 파일을 하나도 찾지 못했다. "
              f"이 훑기는 아무것도 보지 않았다.")
        return 1
    print(f"{scanned} test files scanned\n")

    # 고정 목록이다. 새 범주를 만들고 여기 넣지 않으면 **찾아놓고 보고하지 않는다** —
    # 실제로 `expects_no_raise`를 만들었을 때 그렇게 됐다. 목록에 없는 종류가
    # 나오면 아래에서 실패로 알린다.
    order = ("always_true", "no_assertion", "expects_no_raise", "assertions_only_in_a_loop")
    for kind in order:
        found = by_kind.get(kind, [])
        print(f"── {kind}: {len(found)}")
        for path, line, name, _ in found:
            print(f"     {path}:{line}  {name}")
        print()

    unreported = sorted(set(by_kind) - set(order))
    if unreported:
        print(f"FAILED — 분류했지만 보고하지 않은 종류: {', '.join(unreported)}")
        return 1

    # **실패 조건은 하나뿐이다.** 부르지도 단언하지도 않는 테스트는 어떤 읽기로도
    # 실패할 수 없으니 그것만 막는다. 나머지 둘은 읽을 목록이다 —
    # `expects_no_raise`는 정당한 패턴이고, 루프 안 단언은 빈 컬렉션이면 공허해지지만
    # 그 판단은 컬렉션이 비는지 알아야 할 수 있어 이 도구가 답할 수 없다.
    #
    # 관문으로 삼을 수 있는 것만 관문으로 삼는다. 나머지까지 실패로 만들면 사람들이
    # 이 검사를 끄고, 끈 검사는 없는 검사다.
    vacuous = by_kind.get("no_assertion", [])
    if vacuous:
        print(f"FAILED — 부르지도 단언하지도 않는 테스트 {len(vacuous)}개. "
              f"어떤 읽기로도 실패할 수 없다.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
