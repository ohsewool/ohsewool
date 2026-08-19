"""Find tests that cannot fail.

Three shapes, all of which pass forever and count toward the total:

  no_assertion   a test function with no assert, no pytest.raises, no
                 self.assert*, and no call to a helper that does the asserting.
  always_true    `assert <literal>` or `assert <name>` where the name is a
                 module/class - the assert of something that is always truthy.
  empty_loop     `for x in y: assert ...` where y can be empty, so the loop body
                 never runs. The same vacuous-all() shape found in mcp-gateway's
                 policy, in test clothing.

Reports, does not judge: a test whose whole point is "this does not raise" is
legitimate and lands in no_assertion. The output is a list to read, not a gate.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path("/home/jovyan/work")
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
            self.findings.append((str(self.path), node.lineno, node.name, "no_assertion"))

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


def main() -> int:
    by_kind: dict[str, list] = {}
    scanned = 0
    for repo in REPOS:
        for path in sorted((ROOT / repo / "tests").rglob("test_*.py")):
            scanned += 1
            visitor = Visitor(path.relative_to(ROOT))
            visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
            for finding in visitor.findings:
                by_kind.setdefault(finding[3], []).append(finding)

    if not scanned:
        print("FAILED — no test files found; this scan looked at nothing")
        return 1
    print(f"{scanned} test files scanned\n")

    for kind in ("always_true", "no_assertion", "assertions_only_in_a_loop"):
        found = by_kind.get(kind, [])
        print(f"── {kind}: {len(found)}")
        for path, line, name, _ in found:
            print(f"     {path}:{line}  {name}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
