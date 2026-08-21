"""목차 링크가 실제로 어딘가에 걸리는가.

`FINDINGS.md`의 목차를 만들 때 앵커를 손으로 계산했고 **두 개가 깨져 있었다.**
GitHub은 제목을 소문자로 바꾼 뒤 앵커를 만드는데 내 생성기가 그러지 않아서,
`README의 첫 줄을...`이 `#README의-첫-줄을...`이 됐다. 눌러도 아무 데도 가지 않는다.

**조용히 깨지는 종류다.** 링크는 멀쩡해 보이고, 눌러본 사람만 안다. 그래서 손으로
확인할 것이 아니라 검사로 둔다.

    python3 tools/check_anchors.py

GitHub 규칙: 소문자화 → 영숫자·하이픈·언더스코어·유니코드 글자만 남김 → 공백을
하이픈으로. 한글은 그대로 남는다.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ("README.md", "FINDINGS.md")

HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
INTERNAL_LINK = re.compile(r"\]\(#([^)]+)\)")


def anchor_of(heading: str) -> str:
    lowered = heading.lower()
    stripped = re.sub(r"[^\w\- ]", "", lowered, flags=re.UNICODE)
    return stripped.replace(" ", "-")


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    available = {anchor_of(heading) for heading in HEADING.findall(text)}
    return [target for target in INTERNAL_LINK.findall(text) if target not in available]


def main() -> int:
    failures = 0
    checked = 0
    for name in DOCUMENTS:
        path = ROOT / name
        if not path.exists():
            print(f"  · {name:<14} 없음")
            continue
        text = path.read_text(encoding="utf-8")
        links = INTERNAL_LINK.findall(text)
        checked += len(links)
        broken = check(path)
        failures += len(broken)
        mark = "✓" if not broken else "✗"
        print(f"  {mark} {name:<14} 내부 링크 {len(links)}개, 깨진 것 {len(broken)}")
        for target in broken:
            print(f"      #{target}")

    if not checked:
        # 링크가 하나도 없으면 "전부 통과"는 아무 뜻이 없다.
        print("내부 링크를 하나도 찾지 못했다 — 이 결과는 아무것도 확인하지 않았다.")
        return 1
    if failures:
        print(f"\n{failures}개가 어디에도 걸리지 않는다.")
        return 1
    print(f"\n내부 링크 {checked}개가 전부 실재하는 제목을 가리킨다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
