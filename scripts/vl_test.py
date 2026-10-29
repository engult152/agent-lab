import base64
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

c = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

models = [m.id for m in c.models.list().data]
vis = [m for m in models if "VL" in m.upper() or "VISION" in m.upper()]

print("可用视觉模型:")
for m in vis:
    print("  -", m)

if not vis:
    raise SystemExit("没有找到视觉模型，请把上面的完整模型列表发我")

model = "Qwen/Qwen3-VL-8B-Instruct"
print("\n使用模型:", model)

b64 = base64.b64encode(open("page1.png", "rb").read()).decode()

r = c.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "把这张图片里的所有文字完整转录成纯文本，保持原有顺序和分段。不要总结、不要翻译、不要加任何说明。",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64," + b64},
                },
            ],
        }
    ],
    max_tokens=4000,
)

print("\n--- 转录结果 ---")
print(r.choices[0].message.content)