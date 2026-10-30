import json
from pathlib import Path

DROP = [
    "小百离队", "第六章乐园那个BOSS", "火把到底怎么做",
    "蓝色水晶球和红色水晶球", "游完泳打完BOSS", "cmd 里敲 python",
    "蓝鲸计划", "npm.ps1", "相似度分数全挤在",
    "输中文问题怎么老报", "我明明改了函数里的处理逻辑",
]

WEAK = {"否", "防御"}

NEG = [
    {"q": "神之天平有 DLC 吗？", "must": []},
    {"q": "这个项目支持导出 Excel 吗？", "must": []},
    {"q": "怎么用 Grafana 监控这个应用？", "must": []},
    {"q": "帮我写一首关于秋天的诗", "must": []},
    {"q": "Python 3.14 有什么新特性？", "must": []},
]

base = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
gen = json.loads(Path("eval/cases_gen.json").read_text(encoding="utf-8-sig"))

seen = {c["q"] for c in base}
merged = list(base)

for c in gen:
    if any(k in c["q"] for k in DROP):
        continue
    if c["q"] in seen:
        continue
    must = [m for m in c["must"] if m not in WEAK]
    if not must:
        continue
    seen.add(c["q"])
    merged.append({"q": c["q"], "must": must})

for n in NEG:
    if n["q"] not in seen:
        seen.add(n["q"])
        merged.append(n)

Path("eval/cases.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("总条数:", len(merged),
      "| 正例:", sum(1 for c in merged if c["must"]),
      "| 负例:", sum(1 for c in merged if not c["must"]))
