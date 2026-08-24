"""현황판이 현황판의 모양을 하고 있는가 — **아무도 이 파일의 구조를 안 봤다.**

`work/ROADMAP.md`는 이 포트폴리오의 현황판이고, 회차마다 맨 위에 새 절이 붙는다.
그러다 2026-08-24에 발견했다: **제목 위에 문단 하나가 떠 있었다.**

    - [x] **의존성 고정** (2026-08-22). …        ← 파일 1행
    # 전체 로드맵 (2026-08-19 갱신 …)            ← 제목은 6행

어느 회차에 항목을 끼워 넣다가 앵커를 못 찾아 파일 맨 앞에 붙은 것이다. 며칠 동안
아무도 못 봤다 — **이 저장소는 문서의 *내용*을 여러 방법으로 지키지만 문서의 *모양*은
한 번도 안 봤기 때문이다.** 링크가 실재하는지(`check_anchors`), 개수가 맞는지
(`check_counts`), 검사가 문서에 물려 있는지(`check_doc_tests_bite`)는 다 보면서
"제목으로 시작하는가"는 아무도 묻지 않았다.

읽는 사람에게는 이게 첫인상이다. 현황판이 잘린 문장으로 시작하면 나머지를 안 믿는다.

여기서 보는 것은 셋뿐이다. 많이 볼수록 좋은 검사가 아니라, **틀리면 반드시 눈에
띄는 것**만 본다.

    1. 제목(`# `)으로 시작한다
    2. 회차 절(`### `)이 제목보다 뒤에 온다
    3. 열린 항목(`- [ ]`)이 하나라도 있다 — 다 닫혔다고 표시된 현황판은
       대개 갱신을 멈춘 현황판이다

    python3 tools/check_roadmap_shape.py

### CI에 넣지 않았다 — 넣을 수가 없다

이 검사를 `counts.yml`에 넣으려다 확인해보니 **`work/ROADMAP.md`는 어떤 저장소에도
들어 있지 않다.** `work/`는 git 저장소가 아니고, `ohsewool`도 `modelmate`도 그
파일을 추적하지 않는다. CI 체크아웃에는 그 파일이 아예 없으므로 단계를 넣었으면
**첫 실행부터 "파일이 없다"로 빨간불**이었을 것이다.

그래서 이것은 손으로 돌리는 검사다. 그리고 이 저장소는 *"손으로 돌리는 검사는
돌리지 않으면 없는 검사다"*를 이미 두 번 적어뒀다 — **그 한계를 여기 적어두는
것으로 대신한다. 고칠 방법은 파일을 어딘가에 넣는 것이고, 그건 사람이 정할
일이다**(공개 저장소에 올리면 2,980줄짜리 내부 작업 기록이 공개된다).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROADMAP = Path(__file__).resolve().parents[2] / "ROADMAP.md"


def main(argv: list[str] | None = None) -> int:
    if not ROADMAP.exists():
        print(f"FAILED — {ROADMAP}가 없다")
        return 1
    lines = ROADMAP.read_text(encoding="utf-8").splitlines()
    if not lines:
        # 빈손을 통과로 세지 않는다.
        print("FAILED — ROADMAP.md가 비어 있다")
        return 1

    problems = []

    first = next((n for n, line in enumerate(lines) if line.strip()), None)
    if first is None or not lines[first].startswith("# "):
        shown = lines[first][:60] if first is not None else "(빈 파일)"
        problems.append(
            f"제목으로 시작하지 않는다. 첫 줄: {shown!r}\n"
            "    회차 항목을 끼워 넣다 앵커를 못 찾으면 파일 맨 앞에 붙는다.")

    title_at = first if first is not None and lines[first].startswith("# ") else None
    rounds = [n for n, line in enumerate(lines) if line.startswith("### ")]
    if title_at is not None and rounds and min(rounds) < title_at:
        problems.append(f"회차 절이 제목보다 앞에 있다(줄 {min(rounds) + 1})")

    open_items = sum(1 for line in lines if line.startswith("- [ ] "))
    if open_items == 0:
        problems.append(
            "열린 항목이 하나도 없다. 정말 다 끝났다면 이 검사를 고쳐라 — "
            "대개는 현황판이 갱신을 멈춘 것이다.")

    if problems:
        print("FAILED — 현황판의 모양이 어긋난다:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"현황판이 제목으로 시작하고, 회차 절 {len(rounds)}개와 "
          f"열린 항목 {open_items}개를 들고 있다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
