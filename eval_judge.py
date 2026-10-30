import json
import time
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))

JUDGE_MODEL = "Qwen/Qwen3-32B"
judge_client = main.emb_client

JUDGE = """你是严格的评审，判断【回答】是否被【资料原文】支持。

规则：
- correct：回答的核心内容能在资料原文中找到依据，且确实回答了问题
- partial：部分有据，但遗漏关键点，或夹带了资料中没有的额外断言
- wrong：与资料矛盾，或关键结论在资料中找不到依据（编造）
- refuse：资料里没有答案，回答明确表示不知道（这是正确行为）

注意：
1. 资料原文是检索片段，可能不完整，不要因为「资料里没提到某个细节」就判 wrong
2. 回答可以做合理归纳和措辞转换，只要核心事实有据即可
3. 只有当回答给出的事实与资料矛盾，或明显杜撰时，才判 wrong

只输出 JSON，不要其他文字：{"verdict":"correct","reason":"一句话理由"}"""


def parse(txt):
    s, e = txt.find("{"), txt.rfind("}")
    if s >= 0 and e > s:
        try:
            return json.loads(txt[s : e + 1])
        except Exception:
            pass
    return {"verdict": "unknown", "reason": txt[:100]}


def judge(q, ref, ans):
    prompt = f"问题：{q}\n\n【资料原文】\n{ref}\n\n【回答】\n{ans}"
    for attempt in range(3):
        try:
            r = judge_client.chat.completions.create(
                model=JUDGE_MODEL,
                timeout=90,
                messages=[
                    {"role": "system", "content": JUDGE},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            return parse(r.choices[0].message.content.strip())
        except Exception as e:
            print("   裁判失败，重试", attempt + 1, str(e)[:50])
    return {"verdict": "unknown", "reason": "裁判请求连续失败"}


passed = 0

for c in cases:
  

    msgs = [
        {"role": "system", "content": main.SYSTEM},
        {"role": "user", "content": c["q"]},
    ]
    t0 = time.time()
    ans = main.run_turn(msgs)
    ref = "\n\n".join(m["content"] for m in msgs if m.get("role") == "tool")
    ref = ref or "（本轮没有调用检索工具）"
    dt = time.time() - t0

    v = judge(c["q"], ref, ans)
    verdict = v.get("verdict", "unknown")

    if c["must"]:
        ok = verdict == "correct"
    else:
        ok = verdict in {"refuse", "correct"}

    passed += ok
    print(("PASS" if ok else "FAIL"), f"[{verdict}] {round(dt, 1)}s  {c['q']}")
    if not ok:
        print("     理由:", v.get("reason", ""))
        print("     回答:", (ans or "")[:150].replace("\n", " "))

print("-" * 60)
print(f"裁判通过: {passed}/{len(cases)} = {passed / len(cases):.0%}")