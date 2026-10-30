import json
import re
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
norm = lambda s: re.sub(r"\s+", "", s)

main.BM_WEIGHT = 0.7
main.COS_FLOOR = 0.35

print(f"{'最终门槛':>8} {'正例':>8} {'负例':>8}")
print("-" * 28)

for ff in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
    main.FINAL_FLOOR = ff
    pos_ok = neg_ok = 0
    for c in cases:
        got = main.search_docs(c["q"], top_k=3)
        if c["must"]:
            pos_ok += all(norm(m) in norm(got) for m in c["must"])
        else:
            neg_ok += ("没有找到" in got or "没有可检索" in got)
    print(f"{ff:>8} {pos_ok:>5}/30 {neg_ok:>5}/8")
