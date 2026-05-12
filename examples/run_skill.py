from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from boss_recruit_skill import BossRecruitSkill  # noqa: E402


def main() -> None:
    skill = BossRecruitSkill(output_dir=str(REPO_ROOT / "artifacts"))

    health = skill.prepare_execution()
    print("=== health ===")
    print(json.dumps(health, ensure_ascii=False, indent=2))

    if not health["ready"]:
        return

    result = skill.search_and_generate_from_text(
        "帮我找上海 Python 后端开发，要求 3 年经验，本科，生成 PDF 和 Excel"
    )
    print("=== result ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
