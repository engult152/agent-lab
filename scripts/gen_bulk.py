from pathlib import Path

src = Path("docs/神之天平攻略.md").read_text(encoding="utf-8")
for i in range(10):
    Path("docs/bulk_" + format(i, "02d") + ".md").write_text(src, encoding="utf-8")
print("已生成 10 份，预计总段数 ~850")
