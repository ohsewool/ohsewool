"""한 파일만 돌려도 통과하는가 — 스위트가 초록불인 것과 검사가 참인 것은 다르다.

앞 회차에 **같은 커밋에서 색이 바뀌는 관문**을 하나 찾았다. 원인은 앞선 요청이
남긴 상태였고, 검사는 자기가 만들지 않은 것을 보고 있었다. 그때 물어야 할 다음
질문이 남았다: **이 포트폴리오의 검사들은 서로에게 얼마나 기대고 있는가.**

전부 함께 돌리면 초록불이다. 그건 각 검사가 참이라는 뜻이 아니라, *어떤 순서로
돌렸을 때* 참이라는 뜻이다. 앞선 파일이 DB에 행을 넣고, 전역을 채우고, 파일을
만들어두면 뒤에 오는 검사는 그것을 자기가 확인한 것으로 착각한다.

    함께 돌려서 통과 · 혼자 돌려서 실패   → 앞선 파일에 기대고 있다
    함께 돌려서 통과 · 혼자 돌려서 통과   → 그 파일은 스스로 선다

두 번째만이 "이 검사는 참이다"에 가깝다.

**파일 순서를 뒤집는 것으로는 모자란다.** 뒤집어도 상대 순서만 바뀌지 앞선 파일이
남긴 상태는 그대로 있다. 다섯 저장소를 역순으로 돌려봤고 전부 초록불이었다 —
그건 기대는 검사가 없다는 뜻이 아니라 **그 방법이 못 보는 것**이라는 뜻이다.

    python3 tools/check_tests_do_not_lean_on_each_other.py               # 다섯 저장소
    python3 tools/check_tests_do_not_lean_on_each_other.py modelmate     # 하나만
    python3 tools/check_tests_do_not_lean_on_each_other.py --json out.json

**느리다.** 파일마다 pytest를 새로 띄우므로 저장소 하나에 몇 분, 다섯이면 수십 분.
매 push에 돌릴 물건이 아니다 — 회차마다 한 번, 또는 주 1회다.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPOS = ("agent-safety-core", "mcp-gateway", "rag-profile-selector",
         "document-intelligence", "modelmate")

SUMMARY = re.compile(r"(\d+) (passed|failed|error)")


def test_files(repo: str) -> list[str]:
    directory = ROOT / repo / "tests"
    return sorted(f"tests/{path.name}" for path in directory.glob("test_*.py"))


def reversed_nodes(repo: str, relative: str, timeout: int = 600) -> list[str]:
    """그 파일의 테스트를 **정의 순서의 반대로** 나열한다.

    pytest는 명령줄에 준 노드 순서를 지킨다(확인했다: `c b a`로 주면 `c b a`로
    돈다). 그래서 순서를 뒤집으려고 플러그인을 넣을 필요가 없다.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", relative, "-q", "--no-header",
         "--collect-only", "-p", "no:cacheprovider"],
        cwd=ROOT / repo, capture_output=True, text=True, timeout=timeout)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    nodes = [line.strip() for line in plain.splitlines()
             if line.strip().startswith(relative) and "::" in line]
    return list(reversed(nodes))


def run_alone(repo: str, relative: str, timeout: int = 600,
              reverse: bool = False) -> dict:
    started = time.perf_counter()
    targets = [relative]
    if reverse:
        targets = reversed_nodes(repo, relative, timeout)
        if not targets:
            # 수집이 실패했는데 "테스트 0개"로 넘어가면 **아무것도 안 돈 파일이
            # 합격표를 받는다.** 앞 회차에 같은 모양을 두 번 잡았다.
            return {"file": relative, "returncode": 1, "seconds": 0.0,
                    "summary": "수집 실패 — 뒤집을 노드를 못 얻었다",
                    "failures": [], "collected_nothing": True}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *targets, "-q", "--no-header",
             "-p", "no:cacheprovider"],
            cwd=ROOT / repo, capture_output=True, text=True, timeout=timeout)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        code = result.returncode
    except subprocess.TimeoutExpired:
        plain, code = f"TIMEOUT after {timeout}s", -1

    summary = next((line for line in reversed(plain.splitlines())
                    if SUMMARY.search(line)), "")
    failures = [line.strip() for line in plain.splitlines()
                if line.startswith("FAILED") or line.startswith("ERROR")]
    return {
        "file": relative,
        "returncode": code,
        "seconds": round(time.perf_counter() - started, 1),
        "summary": summary.strip()[:90],
        "failures": failures[:6],
        # pytest는 수집된 테스트가 없어도 종료 코드 5를 낸다. 그걸 "통과"로 세면
        # **아무것도 안 돈 파일이 합격표를 받는다.**
        "collected_nothing": "no tests ran" in plain,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", default=None)
    parser.add_argument("--json", type=Path, default=None, help="결과를 여기에 적는다")
    parser.add_argument("--reverse-within-file", action="store_true",
                        help="파일 안의 테스트 순서를 뒤집어 돌린다 (같은 파일 안에서 기대는 것)")
    arguments = parser.parse_args(argv)

    repos = [arguments.repo] if arguments.repo else list(REPOS)
    for repo in repos:
        if not (ROOT / repo / "tests").is_dir():
            print(f"FAILED — {repo}/tests가 없다")
            return 1

    probe = ("같은 파일 안에서 순서를 뒤집었을 때"
             if arguments.reverse_within_file else "혼자 돌렸을 때")
    print(f"보는 것: {probe} 무엇이 무너지는가")
    report, leaning, empty = {}, [], []
    started = time.perf_counter()
    for repo in repos:
        files = test_files(repo)
        if not files:
            # 빈손을 통과로 세지 않는다.
            print(f"FAILED — {repo}에서 테스트 파일을 하나도 못 찾았다")
            return 1
        print(f"\n{repo} — 파일 {len(files)}개")
        rows = []
        for relative in files:
            row = run_alone(repo, relative, reverse=arguments.reverse_within_file)
            rows.append(row)
            if row["collected_nothing"]:
                empty.append(f"{repo}/{relative}")
                print(f"  ? {relative:58} 수집된 테스트 0개")
            elif row["returncode"] != 0:
                leaning.append(f"{repo}/{relative}")
                print(f"  ✗ {relative:58} {row['summary']}")
                for line in row["failures"]:
                    print(f"        {line[:110]}")
        report[repo] = rows
        stood = sum(1 for row in rows if row["returncode"] == 0
                    and not row["collected_nothing"])
        label = "순서를 뒤집어도 통과" if arguments.reverse_within_file else "혼자 서는 파일"
        print(f"  {label} {stood}/{len(files)}")

    elapsed = time.perf_counter() - started
    total = sum(len(rows) for rows in report.values())
    print(f"\n저장소 {len(report)}개 · 파일 {total}개 · {elapsed / 60:.1f}분")

    if arguments.json:
        arguments.json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if empty:
        print(f"FAILED — 혼자 돌리면 아무것도 수집 안 되는 파일 {len(empty)}개:")
        for name in empty:
            print(f"    {name}")
    if leaning:
        where = ("같은 파일 안 앞선 테스트" if arguments.reverse_within_file
                 else "앞선 파일")
        # 조사까지 맞춘다 — 읽을 수 없는 보고는 보고가 아니다.
        print(f"FAILED — {probe} 실패하는 파일 {len(leaning)}개 "
              f"({where}가 남긴 것에 기대고 있다):")
        for name in leaning:
            print(f"    {name}")
    if empty or leaning:
        return 1
    print("파일 하나하나가 혼자 선다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
