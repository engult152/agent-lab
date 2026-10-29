import json
import time
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))

JUDGE = """你是严格的评审。根据【资料要点】判断【回答】是否正确回答了【问题】。

verdict 只能取这四个值之一：
- correct：核心事实正确，且确实回答了问题
- partial：部分正确，或遗漏了关键信息
- wrong：与资料矛盾、答非所问、或编造了资料里没有的内容
- refuse：资料要点为空，且回答明确表示不知道（这是正确行为）

只输出 JSON，不要任何其他文字：{"verdict":"correct","reason":"一句话理由"}"""


def parse(txt):
    s, e = txt.find("{"), txt.rfind("}")
    if s >= 0 and e > s:
        try:
            return json.loads(txt[s : e + 1])
        except Exception:
            pass
    return {"verdict": "unknown", "reason": txt[:100]}


def judge(q, must, ans):
    ref = "、".join(must) if must else "（资料库中没有这个问题的答案）"
    prompt = f"问题：{q}\n资料要点：{ref}\n回答：{ans}"

    r = main.client.chat.completions.create(
        model=main.CHAT_MODEL,
        messages=[
            {"role": "system", "content": JUDGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return parse(r.choices[0].message.content.strip())


passed = 0
rows = []

for c in cases:
    msgs = [
        {"role": "system", "content": main.SYSTEM},
        {"role": "user", "content": c["q"]},
    ]

    t0 = time.time()
    ans = main.run_turn(msgs)
    dt = time.time() - t0

    v = judge(c["q"], c["must"], ans)
    verdict = v.get("verdict", "unknown")

    if c["must"]:
        ok = verdict == "correct"
    else:
        ok = verdict == "refuse"

    passed += ok
    rows.append((ok, verdict, c["q"], v.get("reason", ""), round(dt, 1)))

    print(("PASS" if ok else "FAIL"), f"[{verdict}] {round(dt, 1)}s  {c['q']}")
    if not ok:
        print("     理由:", v.get("reason", ""))
        print("     回答:", (ans or "")[:150].replace("\n", " "))

print("-" * 60)
print(f"裁判通过: {passed}/{len(cases)} = {passed / len(cases):.0%}")
