import json
import re
import time
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
norm = lambda s: re.sub(r"\s+", "", s)

main.BM_WEIGHT = 0.7
main.COS_FLOOR = 0.35

print(f"{'门槛':>6} {'正例':>8} {'负例':>8}")
print("-" * 26)

for ff in [0.50, 0.55, 0.60, 0.65, 0.70]:
    main.FINAL_FLOOR = ff
    pos_ok = neg_all = neg_ok = 0
    for c in cases:
        got = main.search_docs(c["q"], top_k=3)
        time.sleep(0.25)
        if c["must"]:
            pos_ok += all(norm(m) in norm(got) for m in c["must"])
            neg_all += 0
        else:
            neg_all += 1
            neg_ok += ("没有找到" in got or "没有可检索" in got)
    print(f"{ff:>6} {pos_ok:>5}/47 {neg_ok:>5}/13")
