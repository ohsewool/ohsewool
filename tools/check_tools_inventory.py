"""tools/의 모든 도구가 목록(README)에 있는가 — 목록은 모집단에서 멀어진다.

계기가 열다섯이 되도록 목록이 없었고, 목록을 만드는 순간 새 문제가 생긴다:
**열여섯 번째 도구는 목록에 안 올라간다.** 이 저장소가 가장 자주 잡은 모양이
"한 사실을 두 곳에 적고 한 곳만 지켰다"이고, 목록과 디렉터리가 정확히 그 두 곳이다.

    도구가 있는데 목록에 없다   인계받는 사람이 그 계기의 존재를 모른다
    목록에 있는데 도구가 없다   지웠거나 이름을 바꿨는데 목록이 낡았다

둘 다 잡는다. 도구 이름은 README의 백틱 코드(`` `이름.py` ``)로 센다 — 산문에
스치듯 언급된 것을 등재로 치지 않기 위해서다.

    python3 tools/check_tools_inventory.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
README = TOOLS / "README.md"


def main(argv: list[str] | None = None) -> int:
    if not README.exists():
        print("FAILED — tools/README.md가 없다. 목록 없는 계기창은 인계가 안 된다.")
        return 1
    on_disk = {p.name for p in TOOLS.glob("*.py")}
    if not on_disk:
        # 빈손을 통과로 세지 않는다.
        print("FAILED — tools/에서 도구를 하나도 못 찾았다.")
        return 1
    # 백틱 바로 안의 맨 파일명만 등재로 센다. modelmate 쪽 계기는
    # `scripts/이름.py`처럼 경로가 붙어 있어 이 정규식에 안 걸린다 — 그래서
    # 별도 필터가 필요 없다. **처음엔 필터를 뒀다가 대조가 뚫렸다**: 그 필터가
    # 유령 등재(실재하지 않는 이름)를 걸러내 버려 stale 검사가 영원히 빈손이었다.
    # 유령을 심어도 초록불이었고, 심어보지 않았으면 몰랐다.
    listed = set(re.findall(r"`([a-z_0-9]+\.py)`", README.read_text(encoding="utf-8")))

    missing = sorted(on_disk - listed)
    stale = sorted(listed - on_disk)

    print(f"디렉터리 {len(on_disk)}개 · 목록 {len(listed & on_disk)}개 등재")
    problems = []
    if missing:
        problems.append(f"목록에 없는 도구: {missing} — README 표에 한 줄 추가하라")
    if stale:
        problems.append(f"실재하지 않는 등재: {stale} — 지웠으면 목록도 지워라")
    if problems:
        print("FAILED — 목록이 모집단에서 멀어졌다:")
        for line in problems:
            print(f"    {line}")
        return 1
    print("도구 전부가 목록에 있고, 목록 전부가 실재한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
