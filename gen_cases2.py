import json
import random
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
known = {c["q"] for c in cases}

chunks = [c for c in main._chunks() if 100 < len(c[2]) < 350]
random.seed(7)
picked = random.sample(chunks, min(30, len(chunks)))

GEN = """根据下面的资料，生成一个真实用户会问的问题，以及回答必须出现的关键词。

要求：
- 用口语问，像在论坛里发帖，不要照抄原文标题
- 必须只用这段资料就能回答
- 关键词 2 个，是回答里的关键事实（数字、专有名词、命令、结论）
- 只输出 JSON：{{"q":"问题","must":["词1","词2"]}}

资料（{name}）：
{text}"""

out = []
for c in picked:
    r = main.client.chat.completions.create(
        model=main.CHAT_MODEL,
        messages=[{"role": "user", "content": GEN.format(name=c[0], text=c[2][:900])}],
        temperature=0.8,
    )
    txt = r.choices[0].message.content.strip()
    s, e = txt.find("{"), txt.rfind("}")
    try:
        item = json.loads(txt[s : e + 1])
    except Exception:
        continue
    if item["q"] in known:
        continue
    item["src"] = c[0]
    out.append(item)
    print("OK  ", item["q"])

Path("eval/cases_gen.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\n生成", len(out), "条")
