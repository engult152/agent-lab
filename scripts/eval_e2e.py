import json
import time
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))

# 4 条正例 + 1 条负例
picked = cases[:4] + [cases[-1]]

ok = 0
for c in picked:
    msgs = [
        {"role": "system", "content": main.SYSTEM},
        {"role": "user", "content": c["q"]},
    ]

    t0 = time.time()
    ans = main.run_turn(msgs)
    dt = time.time() - t0

    if c["must"]:
        good = all(m in ans for m in c["must"])
        kind = "正例"
    else:
        good = any(k in ans for k in ["没有", "未", "不知道", "找不到"])
        kind = "负例"

    ok += good
    print(("PASS" if good else "FAIL"), f"[{kind}] {round(dt, 1)}s  {c['q']}")
    print("   ", (ans or "")[:180].replace("\n", " "))
    print()

print("-" * 60)
print(f"端到端通过: {ok}/{len(picked)}")
