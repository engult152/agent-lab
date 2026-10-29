import json
import random

import main

N = 20
chunks = [c for c in main._chunks() if len(c[2]) > 80]
random.seed(42)
picked = random.sample(chunks, min(N, len(chunks)))

GEN = """根据下面的资料，生成一个用户可能问的问题，以及回答必须出现的关键词。

要求：
- 问题要像真人提问，可以口语化，不要照抄原文标题
- 问题必须只用这段资料就能回答
- 关键词 1~3 个，是回答里必须出现的关键事实（数字、命令、专有名词、结论）
- 只输出 JSON，不要其他文字：{{"q":"问题","must":["关键词"]}}

资料（来自 {name}）：
{text}"""

out = []
for c in picked:
    prompt = GEN.format(name=c[0], text=c[2][:1200])
    r = main.client.chat.completions.create(
        model=main.CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    txt = r.choices[0].message.content.strip()
    s, e = txt.find("{"), txt.rfind("}")
    try:
        item = json.loads(txt[s : e + 1])
        item["src"] = c[0]
        out.append(item)
        print("OK  ", item["q"])
    except Exception:
        print("SKIP", txt[:60])

from pathlib import Path

Path("eval/cases_gen.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("生成", len(out), "条 → eval/cases_gen.json")
