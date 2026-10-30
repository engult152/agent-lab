import json
import re
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
norm = lambda s: re.sub(r"\s+", "", s)

print(f"{'权重':>6} {'下限':>6} {'正例':>8} {'负例':>8}")
print("-" * 34)

for w, fl in [(1.0, 0.0), (0.8, 0.30), (0.7, 0.35), (0.5, 0.40), (0.3, 0.45)]:
    main.BM_WEIGHT = w
    main.COS_FLOOR = fl
    pos_ok = neg_ok = 0
    for c in cases:
        got = main.search_docs(c["q"], top_k=3)
        if c["must"]:
            pos_ok += all(norm(m) in norm(got) for m in c["must"])
        else:
            neg_ok += ("没有找到" in got or "没有可检索" in got)
    print(f"{w:>6} {fl:>6} {pos_ok:>5}/30 {neg_ok:>5}/8")
