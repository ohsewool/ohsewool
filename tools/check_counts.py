"""Check this README's table against what each repository says about itself.

The table listed 304 / 284 / 177 / 155 / 67 while the repositories were at
334 / 410 / 180 / 202 / 98. Every one of those five is verified in its own CI
against `pytest --collect-only` — that check was added after the count drifted
twice, including once in a repository verified days earlier — and the summary
that aggregates them was covered by none of it.

A guard that stops at the repository boundary leaves the page most people read
unguarded, which is the same defect the guard was built for.

So the chain closes here: each repository's CI checks its README against its
real suite, and this checks the table against those READMEs. Nothing in the
middle is taken on trust, and no heavyweight dependency install is needed to
do it.

    python3 tools/check_counts.py           # fetch from GitHub
    python3 tools/check_counts.py --local ..  # read sibling checkouts instead
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPOS = ("agent-safety-core", "modelmate", "rag-profile-selector",
         "mcp-gateway", "document-intelligence")
RAW = "https://raw.githubusercontent.com/ohsewool/{repo}/main/README.md"

# `pytest tests/ -q   # 334 tests` in each sibling README.
COUNT_IN_SIBLING = re.compile(r"#\s*(\d+)\s*tests")
# `| [**agent-safety-core**](...) | ... | 334 |` in this one.
ROW_IN_TABLE = re.compile(r"\|\s*\[\*\*(?P<repo>[\w-]+)\*\*\][^|]*\|[^|]*\|\s*(?P<count>\d+)\s*\|")


def sibling_readme(repo: str, local: Path | None) -> str:
    """Read a sibling's README, from disk or from GitHub.

    `raw.githubusercontent.com` is a CDN and it caches. On 2026-08-22 it served
    the previous README for two repositories several minutes after the push had
    landed - `git log origin/main` showed the new commits and raw did not. This
    script then reported that two READMEs disagreed with this one, which was
    false: they agreed, and the copy being read was stale.

    That is the failure mode this whole project keeps finding in its own checks.
    An alarm nobody can trust costs the same attention as an all-clear nobody
    can trust, and here it would have pointed at the wrong file - I nearly went
    to fix READMEs that were already correct.

    So the request asks for a fresh copy. It is not a guarantee - a CDN may
    ignore it - but the alternative was not asking at all.
    """
    if local is not None:
        return (local / repo / "README.md").read_text(encoding="utf-8")
    request = urllib.request.Request(
        RAW.format(repo=repo),
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", type=Path, default=None,
                        help="directory holding sibling checkouts")
    arguments = parser.parse_args(argv)

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    claimed = {match["repo"]: int(match["count"]) for match in ROW_IN_TABLE.finditer(readme)}

    missing = [repo for repo in REPOS if repo not in claimed]
    if missing:
        # Not "everything matched": a row this script cannot parse would
        # otherwise be silently exempt from the check it exists to perform.
        print(f"FAILED — no table row found for: {', '.join(missing)}")
        return 1

    failures = 0
    for repo in REPOS:
        try:
            found = COUNT_IN_SIBLING.search(sibling_readme(repo, arguments.local))
        except (urllib.error.URLError, OSError) as error:
            # Unreachable is not the same as mismatched, and must not be
            # reported as either a pass or a discrepancy.
            print(f"  ?  {repo:<24} could not be read ({error})")
            failures += 1
            continue
        if found is None:
            print(f"  ?  {repo:<24} its README states no test count")
            failures += 1
            continue
        actual = int(found[1])
        agrees = actual == claimed[repo]
        failures += not agrees
        print(f"  {'✓' if agrees else '✗'} {repo:<24} table {claimed[repo]}"
              + ("" if agrees else f", its README says {actual}"))

    print("\nall rows agree" if not failures else f"\n{failures} row(s) to fix")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
