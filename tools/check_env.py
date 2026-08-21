"""Check that `import x` reaches the checkout you think you are testing.

Four of these repositories are installed editable. An editable install records
a path, and that path is wherever `pip install -e` was last pointed - which is
not necessarily the working tree. This environment had all four pointing at
`/tmp/fresh/...` and `/tmp/asc`, copies made days earlier during a fresh-clone
verification and never cleaned up.

Each repository's own tests happened to survive it, because they
`sys.path.insert` their own `src/` before importing. Cross-repository tests
have no such protection: mcp-gateway's suite loads `core` from
agent-safety-core, found it at `/tmp/asc`, and had been validating against a
four-day-old ledger. It passed. It would also have passed if the current
ledger were broken.

CI is not exposed to this - it checks out a sibling fresh and installs that -
so the failure mode is specific to a long-lived development machine, and
invisible exactly there.

    python3 tools/check_env.py

Nothing here tests the repositories. It tests the room they are being tested
in, which is the thing no repository can check about itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# import name -> the checkout it must resolve inside
MODULES = {
    "core": "agent-safety-core",
    "mcp_gateway": "mcp-gateway",
    "rag_profile_selector": "rag-profile-selector",
    "document_intelligence": "document-intelligence",
}


def resolve(module: str) -> Path | None:
    """Ask a clean interpreter, from a neutral directory.

    Run in a subprocess started outside any repository: asking from inside one
    would let the current directory supply the answer and hide the very
    misconfiguration this is looking for.

    A namespace package has `__file__ is None` and only a `__path__`. Reading
    `__file__` alone turned that into the string "None" and reported it as a
    path outside the checkout - this checker's own first result was a false
    alarm on `core`, which is a namespace package.
    """
    result = subprocess.run(
        [sys.executable, "-c",
         f"import {module}\n"
         f"print({module}.__file__ or next("
         f"(p for p in getattr({module}, '__path__', []) if '/' in p), ''))"],
        capture_output=True, text=True, cwd="/",
    )
    found = result.stdout.strip()
    return Path(found) if result.returncode == 0 and found else None


def main() -> int:
    failures = 0
    unresolved = 0
    for module, repo in MODULES.items():
        expected = ROOT / repo
        found = resolve(module)
        if found is None:
            # Not installed is a legitimate state - the repositories are usable
            # from a checkout - and must not be reported as pointing somewhere
            # wrong.
            #
            # **But it is also the state in which this script checks nothing.**
            # Run in a fresh CI job with nothing installed, every module lands
            # here and the exit code is zero: a green tick that establishes
            # nothing. Found 2026-08-22 while wiring this into CI - the editable
            # installs had failed and the check passed anyway.
            #
            # `--require-importable` is for that setting. Locally the default
            # stays as it was.
            unresolved += 1
            print(f"  · {module:<24} not importable outside a checkout (fine if uninstalled)")
            continue
        try:
            found.relative_to(expected)
        except ValueError:
            print(f"  ✗ {module:<24} resolves to {found}")
            print(f"    {'':<24} expected somewhere under {expected}")
            failures += 1
        else:
            print(f"  ✓ {module:<24} {found.relative_to(ROOT)}")

    if failures:
        print(f"\n{failures} module(s) resolve outside their checkout. Any test run "
              f"here is testing something else.\n"
              f"fix:  pip install -e <repo> --no-deps --no-build-isolation")
        return 1
    if arguments.require_importable and unresolved:
        print(f"\nFAILED — {unresolved}개 모듈이 import되지 않는다. 설치되지 않은 상태에서는 "
              f"이 검사가 아무것도 확인하지 않는다.")
        return 1
    print("\nevery module resolves inside its own checkout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
