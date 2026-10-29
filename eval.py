import json
import sys
from pathlib import Path
import re

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))

top_k = int(sys.argv[1]) if len(sys.argv) > 1 else main.TOP_K
min_score = float(sys.argv[2]) if len(sys.argv) > 2 else main.MIN_SCORE
main.MIN_SCORE = min_score

print(f"参数: top_k={top_k}  min_score={min_score}")
print("-" * 60)

hits = 0
pos_ok = pos_all = neg_ok = neg_all = 0

for c in cases:
    got = main.search_docs(c["q"], top_k=top_k)

    if c["must"]:
        pos_all += 1
        norm = lambda s: re.sub(r"\s+", "", s)
        ok = all(norm(m) in norm(got) for m in c["must"])
        pos_ok += ok
        kind = "正例"
    else:
        neg_all += 1
        ok = "没有找到" in got or "没有可检索" in got
        neg_ok += ok
        kind = "负例"

    print(f"{'OK  ' if ok else 'MISS'} [{kind}] {c['q']}")
    if not ok and c["must"]:
        print(f"     期望包含: {c['must']}")

print("-" * 60)
print(f"正例召回: {pos_ok}/{pos_all}")
print(f"负例正确拒答: {neg_ok}/{neg_all}")
print(f"总分: {pos_ok + neg_ok}/{pos_all + neg_all}")
