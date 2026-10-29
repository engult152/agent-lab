import json
import re
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
norm = lambda s: re.sub(r"\s+", "", s)

for c in cases:
    if not c["must"]:
        continue
    top3 = main.search_docs(c["q"], top_k=3)
    missing3 = [m for m in c["must"] if norm(m) not in norm(top3)]
    if not missing3:
        continue

    top8 = main.search_docs(c["q"], top_k=8)
    missing8 = [m for m in c["must"] if norm(m) not in norm(top8)]

    print("Q:", c["q"])
    print("   top3 缺:", missing3)
    print("   top8 仍缺:", missing8)
    print("   结论:", "排序问题(扩大 top_k 能救)" if len(missing8) < len(missing3) else "检索根本找不到")
    print()
