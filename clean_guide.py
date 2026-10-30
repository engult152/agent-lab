import re
from pathlib import Path

p = Path("docs/神之天平攻略.md")
lines = p.read_text(encoding="utf-8").splitlines()

out = []
dropped = 0
for l in lines:
    s = l.strip()
    if "全流程图文攻略" in s:
        dropped += 1
        continue
    if re.fullmatch(r"图\s*\d+", s):
        dropped += 1
        continue
    if re.fullmatch(r"\d+\s*/\s*\d+", s):
        dropped += 1
        continue
    out.append(l)

p.write_text("\n".join(out), encoding="utf-8")
print("原行数", len(lines), "→", len(out), "| 删掉", dropped, "行")
