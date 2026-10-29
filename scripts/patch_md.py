from pathlib import Path

p = Path("main.py")
src = p.read_text(encoding="utf-8")

start = src.index("def _markdown_pieces(")
end = src.index("\ndef ", start + 1)

new = '''def _markdown_pieces(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    heading = ""
    pieces = []

    for para in raw.split("\\n\\n"):
        p = para.strip()
        if not p:
            continue

        if p.startswith("#"):
            first, _, rest = p.partition("\\n")
            heading = first.lstrip("#").strip()
            body = rest.strip()
        else:
            body = p

        body = _normalize(re.sub(r"<!--.*?-->", "", body))
        if len(body) < 40:
            continue

        prefix = (heading + "\uff5c") if heading else ""

        if len(body) <= 400:
            pieces.append(prefix + body)
        else:
            for i in range(0, len(body), 320):
                seg = body[i : i + 400].strip()
                if len(seg) > 40:
                    pieces.append(prefix + seg)

    return pieces

'''

p.write_text(src[:start] + new + src[end:], encoding="utf-8")
print("替换完成")
