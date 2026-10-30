import json
import re
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
norm = lambda s: re.sub(r"\s+", "", s)

chunks = main._chunks()
alltext = norm("".join(c[2] for c in chunks))

n = 0
for c in cases:
    if not c["must"]:
        continue
    got = main.search_docs(c["q"], top_k=3)
    missing = [m for m in c["must"] if norm(m) not in norm(got)]
    if not missing:
        continue
    n += 1
    print("MISS:", c["q"][:45])
    for m in missing:
        print("    缺:", m, "| 全库里有这个词:", norm(m) in alltext)
    print()

print("合计", n, "条")
