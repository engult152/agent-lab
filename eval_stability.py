import json
from pathlib import Path

import main

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
PICK = [0, 2, 10, 11, 12, 14]
REPEAT = 3

JUDGE_MODEL = "Qwen/Qwen3-32B"
jc = main.emb_client

JUDGE = """你是严格的评审，判断【回答】是否被【资料原文】支持。
verdict 取值：
- correct：核心内容有据，且回答了问题
- partial：部分有据，但遗漏关键点
- wrong：与资料矛盾，或结论无据（编造）
- refuse：资料里没有答案，回答明确表示不知道（正确行为）
资料可能不完整，不要因细节缺失判 wrong。
只输出 JSON：{"verdict":"correct","reason":"一句话"}"""


def judge(q, ref, ans):
    prompt = f"问题：{q}\n\n【资料原文】\n{ref}\n\n【回答】\n{ans}"
    r = jc.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    txt = r.choices[0].message.content.strip()
    s, e = txt.find("{"), txt.rfind("}")
    try:
        return json.loads(txt[s : e + 1]).get("verdict", "unknown")
    except Exception:
        return "unknown"


stats = []
for idx in PICK:
    c = cases[idx]
    oks = []
    for _ in range(REPEAT):
        msgs = [
            {"role": "system", "content": main.SYSTEM},
            {"role": "user", "content": c["q"]},
        ]
        ans = main.run_turn(msgs)
        ref = "\n\n".join(m["content"] for m in msgs if m.get("role") == "tool")
        verdict = judge(c["q"], ref or "（无）", ans)

        if c["must"]:
            ok = verdict == "correct"
        else:
            ok = verdict in {"refuse", "correct"}
        oks.append(ok)

    passed = sum(oks)
    stats.append((c["q"], passed))

print("\n" + "=" * 70)
total = 0
for q, n in stats:
    mark = "稳定" if n == REPEAT else ("全挂" if n == 0 else "不稳定")
    total += n
    print(f"[{mark}] {n}/{REPEAT}  {q}")
print("=" * 70)
print(f"总通过: {total}/{len(PICK) * REPEAT}")
