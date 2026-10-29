import json
from pathlib import Path

old = json.loads(Path("eval/cases.json").read_text(encoding="utf-8-sig"))
gen = json.loads(Path("eval/cases_gen.json").read_text(encoding="utf-8-sig"))

DROP_KEYS = ["提示找不到命令，这是咋回事"]
WEAK = ["否", "多准备一些", "图14", "图15"]

NEG = [
    {"q": "这个项目用了 React 吗？", "must": []},
    {"q": "神之天平支持联机吗？", "must": []},
    {"q": "Python 的 GIL 是什么？", "must": []},
    {"q": "怎么用 Nginx 反向代理这个服务？", "must": []},
    {"q": "Streamlit 怎么加登录鉴权？", "must": []},
]

merged = []
for c in old + gen:
    if any(k in c["q"] for k in DROP_KEYS):
        continue
    must = [m for m in c["must"] if m not in WEAK]
    merged.append({"q": c["q"], "must": must})

merged += NEG

seen, out = set(), []
for c in merged:
    if c["q"] in seen:
        continue
    seen.add(c["q"])
    out.append(c)

Path("eval/cases.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("总条数:", len(out), "| 正例:", sum(1 for c in out if c["must"]), "| 负例:", sum(1 for c in out if not c["must"]))
