import sys
from pathlib import Path
import json

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
target = sys.argv[1] if len(sys.argv) > 1 else "土城"

for c in cases:
    if target in c["q"]:
        print("问题:", c["q"])
        print("must:", c["must"])
        got = main.search_docs(c["q"], top_k=5)
        print("\n--- must 命中情况 ---")
        for m in c["must"]:
            print("  ", "有" if m in got else "无", m)
        print("\n--- 检索到的段落（前 120 字）---")
        print(got[:1200])
        break
