"""Break a safety check on purpose and see whether the suite notices.

1,211 tests passing says the tests pass. It does not say they hold anything.
The only way to find out is to break the code and check that something goes
red - so this applies one deliberate breakage at a time, runs the suite, and
restores the original whether the run succeeded, failed, or crashed.

    python3 tools/mutate.py            # run the recorded probe set
    python3 tools/mutate.py --control  # run the negative controls only

**The negative control is not optional.** A probe that reports "caught" for
every mutation proves nothing on its own: a suite that fails for an unrelated
reason - wrong working directory, a collection error, a missing dependency -
produces exactly the same output. So harmless whitespace edits are applied to
the same files first, and they must come back *not* caught. If a control ever
reports caught, every result in the same run is void.

This is the same trap the secret scanner fell into earlier in this project: a
malformed regex made `git grep` error on every call, the empty output read as
"no secrets found", and five repositories came back clean including one that
held four live keys. A checker that cannot fail is not a checker.

Two findings came out of the recorded set, both in code that was already
correct and simply unheld:

  * agent-safety-core - the clock rollback check disarmed itself the first time
    it fired. The high-water mark could be made to follow the clock downward
    and all 331 tests still passed.
  * mcp-gateway - the cross-repository log format claim was fixed on both sides
    and tested on one. Deleting this side's fallback passed all 192.

Not everything worth breaking can be expressed as a string replacement. That
`core` is a regular package rather than a namespace one is a property of a file
*existing*, and a probe that emptied `core/__init__.py` would only be testing
that a syntax error fails the suite. That one is verified by deleting the file
by hand; `agent-safety-core/tests/test_package_resolution.py` goes red on five
tests when it is gone.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTEST = (sys.executable, "-m", "pytest", "tests/", "-q",
          "-p", "no:cacheprovider", "-x", "--no-header")


@dataclass(frozen=True)
class Probe:
    repo: str
    path: str
    old: str
    new: str
    label: str
    expect_caught: bool = True


PROBES = (
    Probe("agent-safety-core", "core/ledger.py",
          'if row["actor_id"] == approver_id:', "if False:",
          "self-approval refused"),
    Probe("agent-safety-core", "core/ledger.py",
          'if row["actor_id"] == reconciler_id:', "if False:",
          "self-reconciliation refused"),
    Probe("agent-safety-core", "core/ledger.py",
          "if previous is None or now > previous:", "if True:",
          "clock high-water mark is monotonic"),
    Probe("agent-safety-core", "core/checkpoint.py",
          "if self.presented_sequence < self.witness_sequence:", "if False:",
          "rollback verdict"),
    Probe("agent-safety-core", "core/witness.py",
          "for repeated in (base + 1, base):", "for repeated in ():",
          "witness conformance rejects a rewound counter"),

    Probe("mcp-gateway", "src/mcp_gateway/policy.py",
          "return PurePosixPath(requested.path).parts[:len(granted)] == granted",
          "return str(requested.path).startswith(str(self.path))",
          "path containment is by component, not string prefix"),
    Probe("mcp-gateway", "src/mcp_gateway/policy.py",
          'if ".." in PurePosixPath(requested.path).parts:', "if False:",
          "traversal refused rather than resolved"),
    Probe("mcp-gateway", "src/mcp_gateway/policy.py",
          "return requested.maximum <= self.maximum", "return True",
          "quantity ceiling enforced"),
    Probe("mcp-gateway", "src/mcp_gateway/transport.py",
          'if isinstance(result, Mapping) and result.get("isError") is True:', "if False:",
          "tool error is not recorded as success"),
    Probe("mcp-gateway", "src/mcp_gateway/audit.py",
          'return integrity.get("record_hash", integrity.get("event_hash"))',
          'return integrity.get("record_hash")',
          "reads agent-safety-core's log format"),

    Probe("modelmate", "backend/agents/review_queue.py",
          "return action not in PROCEEDING_ACTIONS", "return False",
          "actions outside the allow-list need review"),
    Probe("modelmate", "backend/tools/leakage_check.py",
          "if separation is not None and separation >= 0.90:", "if False:",
          "measured leakage detection"),
    Probe("modelmate", "backend/scoped_state.py",
          "scope = _current_scope.get()", "scope = DEFAULT_SCOPE",
          "per-request state isolation"),
    Probe("modelmate", "backend/tools/evaluation.py",
          'if leakage_risk == "high" and status == "pass":', "if False:",
          "a pass on leaking features is downgraded"),
    Probe("modelmate", "backend/tools/deployment_check.py",
          "def _risk_from_warnings(warnings: list[Any], evidence: dict[str, Any] | None = None) -> str:",
          "def _risk_from_warnings(warnings: list[Any], evidence: dict[str, Any] | None = None) -> str:\n    return \"low\"",
          "deployment gate reads real severity"),
    Probe("modelmate", "backend/agents/persistence.py",
          'conn.execute("PRAGMA foreign_keys = ON")', "pass",
          "foreign keys enforced"),
    Probe("modelmate", "backend/agents/review_queue.py",
          ").hexdigest()[:8]", ").hexdigest()[:0]",
          "distinct issues get distinct review ids"),

    Probe("rag-profile-selector", "src/rag_profile_selector/corpus.py",
          'if split == "test" and not self._protocol_frozen:', "if False:",
          "test split sealed until the protocol is frozen"),
    Probe("rag-profile-selector", "src/rag_profile_selector/corpus.py",
          "if actual != expected:", "if False:",
          "corpus checksums verified"),
    Probe("rag-profile-selector", "src/rag_profile_selector/corpus.py",
          "missing = [item for item in gold if item not in available]", "missing = []",
          "gold evidence exists in the corpus"),
    Probe("rag-profile-selector", "src/rag_profile_selector/selector.py",
          "best_fixed = min(fixed_means, key=lambda profile: (fixed_means[profile], profile))",
          "best_fixed = max(fixed_means, key=lambda profile: (fixed_means[profile], profile))",
          "headroom measures against the best fixed profile"),
    Probe("rag-profile-selector", "src/rag_profile_selector/fusion.py",
          "RRF_RANK_CONSTANT = 60", "RRF_RANK_CONSTANT = 6000",
          "fusion rank constant"),

    Probe("document-intelligence", "src/document_intelligence/model.py",
          'if self.provenance == "transcribed" and self.confidence is None:', "if False:",
          "a transcription must carry a confidence"),
    Probe("document-intelligence", "src/document_intelligence/model.py",
          'raise ValueError("bounding-box coordinates must be ordered")', "pass",
          "coordinate ordering"),
    Probe("document-intelligence", "src/document_intelligence/model.py",
          "0 <= self.left and self.right <= width and 0 <= self.top and self.bottom <= height",
          "True",
          "page bounds"),
    Probe("document-intelligence", "src/document_intelligence/model.py",
          "return min(scores) if scores else None",
          "return sum(scores)/len(scores) if scores else None",
          "weakest link, not the average"),
    Probe("document-intelligence", "src/document_intelligence/adapters/pdfplumber.py",
          'return "unclassified"', 'return "degenerate_box"',
          "an unrecognised rejection is not disguised"),
)

# Harmless edits that must NOT be caught. If one is, the run is void.
CONTROLS = (
    Probe("agent-safety-core", "core/ledger.py", '"""', '""" ',
          "whitespace in a docstring", expect_caught=False),
    Probe("mcp-gateway", "src/mcp_gateway/policy.py", "return False", "return False ",
          "trailing whitespace", expect_caught=False),
    Probe("modelmate", "backend/tools/leakage_check.py",
          "if by_presence >= 0.90:", "if by_presence >= 0.90 :",
          "whitespace before a colon", expect_caught=False),
    Probe("rag-profile-selector", "src/rag_profile_selector/corpus.py",
          "return report", "return  report",
          "double space", expect_caught=False),
    Probe("document-intelligence", "src/document_intelligence/model.py",
          "@dataclass(frozen=True, slots=True)", "@dataclass(frozen=True, slots=True) ",
          "trailing whitespace on a decorator", expect_caught=False),
)


def run(probe: Probe) -> bool | None:
    """Apply, run, restore. Returns whether the suite went red, or None if the
    pattern is gone - which is itself worth reporting, since a probe pointing at
    code that no longer exists silently tests nothing."""
    path = ROOT / probe.repo / probe.path
    original = path.read_text(encoding="utf-8")
    if probe.old not in original:
        return None
    try:
        path.write_text(original.replace(probe.old, probe.new, 1), encoding="utf-8")
        result = subprocess.run(PYTEST, cwd=ROOT / probe.repo,
                                capture_output=True, text=True, timeout=1800)
        return result.returncode != 0
    finally:
        path.write_text(original, encoding="utf-8")


def report(probes: tuple[Probe, ...]) -> int:
    failures = 0
    repo = None
    for probe in probes:
        if probe.repo != repo:
            repo = probe.repo
            print(f"\n{repo}")
        caught = run(probe)
        if caught is None:
            mark, bad = "?  pattern not found", True
        elif caught == probe.expect_caught:
            mark, bad = ("caught" if caught else "not caught (as intended)"), False
        else:
            mark = "NOT CAUGHT" if probe.expect_caught else "CAUGHT — control failed, run is void"
            bad = True
        failures += bad
        print(f"  {'✗' if bad else '✓'} {probe.label:<52} {mark}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--control", action="store_true",
                        help="run only the negative controls")
    arguments = parser.parse_args(argv)

    print("negative controls — these must NOT be caught")
    void = report(CONTROLS)
    if void:
        print("\na control was caught: the suite is failing for an unrelated "
              "reason and no result below would mean anything.")
        return 1
    if arguments.control:
        return 0

    print("\n\nmutations — these must be caught")
    missed = report(PROBES)
    print(f"\n{len(PROBES) - missed}/{len(PROBES)} caught")
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main())
