import base64
import os
import time

import pymupdf
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

c = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

MODEL = "Qwen/Qwen3-VL-8B-Instruct"
SRC = "docs/test1.pdf"
OUT = "docs/神之天平攻略.md"

PROMPT = (
    "这是一篇网页文章的截图。请只转录正文：文章标题、章节标题、正文段落、列表项。"
    "忽略网站的导航栏、搜索框、按钮、点赞收藏等数字、侧边栏、页脚、页码、网址和日期。"
    "按原文顺序输出纯文本，章节标题用 Markdown 的 ## 表示。"
    "不要总结、不要翻译、不要加任何说明文字。"
)

doc = pymupdf.open(SRC)
total = len(doc)
print("总页数:", total)

done = 0
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        done = f.read().count("<!-- page ")
    print("已有", done, "页，从第", done + 1, "页继续")

with open(OUT, "a" if done else "w", encoding="utf-8") as out:
    if done == 0:
        out.write("# 《神之天平》全流程图文攻略（上）\n\n")

    for i in range(done, total):
        pix = doc[i].get_pixmap(dpi=150)
        b64 = base64.b64encode(pix.tobytes("png")).decode()

        r = c.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64," + b64},
                        },
                    ],
                }
            ],
            max_tokens=4000,
        )

        text = r.choices[0].message.content.strip()
        out.write("\n<!-- page " + str(i + 1) + " -->\n\n" + text + "\n")
        out.flush()
        print("第", i + 1, "/", total, "页完成，", len(text), "字")
        time.sleep(0.5)

print("全部完成:", OUT)