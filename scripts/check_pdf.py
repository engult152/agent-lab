from pypdf import PdfReader

r = PdfReader(r"docs\test1.pdf")
print("总页数:", len(r.pages))

total = 0
for i, p in enumerate(r.pages[:5]):
    t = p.extract_text() or ""
    total += len(t)
    print("第", i + 1, "页字符数:", len(t))

print("前5页合计字符:", total)
