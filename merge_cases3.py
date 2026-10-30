import json
from pathlib import Path

DROP = [
    "第二章那个哥布林的石板到底怎么拿",
    "打完金色稻穗那段剧情之后该怎么走",
    "我在论坛里搜那种三四十个字",
    "第一章洞窟里火把有时间限制吗",
    "第一章那个蓝色水晶球和红色水晶球",
    "第五章魔王城刚进去遇到盖乌",
    "第二章在力斯帕达尔镇加入公会拿到钥匙",
    "金色稻穗那个任务，素材都集齐了",
    "第五章那个BOSS战怎么打啊？打完还有什么隐藏路线",
    "第五章那个火把弓到底怎么合成",
    "第三章那个地图我老是绕晕",
    "刚玩神之天平第一章，从左边出村走到湖边",
    "金色稻穗那关的桥怎么开",
    "金色稻穗那关用炸弹炸石块",
    "我在 PowerShell 里直接输入中文问题，结果报错",
    "我装完 Python 后，在命令行敲 python 提示找不到命令",
    "刚装完 Python，在命令行敲 python 没反应",
    "第三章跟弥露对完话回自己房子",
    "第六章一开始那点自由时间该先干啥？听说后面就没机会了",
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
    seen.add(c["q"])
    merged.append({"q": c["q"], "must": c["must"]})

Path("eval/cases.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("总条数:", len(merged),
      "| 正例:", sum(1 for c in merged if c["must"]),
      "| 负例:", sum(1 for c in merged if not c["must"]))
