"""agent-lab：一个能读你自己文档的本地 Agent"""

import os
import json
import math
import re
import hashlib
import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

# ---------------- 配置 ----------------
BASE = Path(__file__).resolve().parent
DOCS = BASE / "docs"
CACHE = BASE / ".cache" / "vectors.json"

CHAT_MODEL = "deepseek-chat"
EMB_MODEL = "BAAI/bge-m3"
TOP_K = 3
MIN_SCORE = 0.60

chat_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
emb_client = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

client = chat_client  # app.py 里用到


# ---------------- 文档与切块 ----------------
def _pdf_pieces(path: Path):
    reader = PdfReader(str(path))
    text = " ".join(
        " ".join((p.extract_text() or "").split()) for p in reader.pages
    )
    return [text[i : i + 400] for i in range(0, len(text), 320)]


def _markdown_pieces(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    heading = ""
    pieces = []
    for para in raw.split("\n\n"):
        p = para.strip()
        if not p:
            continue

        if p.startswith("#"):
            first, _, rest = p.partition("\n")
            heading = first.lstrip("#").strip()
            body = rest.strip()
        else:
            body = p

        body = re.sub(r"<!--.*?-->", "", body).strip()
        if len(body) < 40:
            continue

        pieces.append(heading + "｜" + body if heading else body)

    return pieces


def _chunks():
    """返回 [(文件名, 序号, 文本块)]"""
    chunks = []
    if not DOCS.is_dir():
        return chunks
    for f in sorted(DOCS.rglob("*")):
        suffix = f.suffix.lower()
        if suffix not in {".md", ".txt", ".pdf"}:
            continue
        try:
            pieces = _pdf_pieces(f) if suffix == ".pdf" else _markdown_pieces(f)
        except Exception as e:
            print("跳过", f.name, ":", e)
            continue
        for i, body in enumerate(pieces):
            if len(body) > 20:
                chunks.append((f.name, i, body))
    return chunks


# ---------------- 向量检索 ----------------
def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)


_vectors = []


def _load_vectors():
    """把段落转成向量，带本地缓存，只算新增的"""
    global _vectors
    if _vectors:
        return
    chunks = _chunks()
    if not chunks:
        return

    CACHE.parent.mkdir(exist_ok=True)
    try:
        store = json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        store = {}

    keys = [hashlib.md5(c[2].encode("utf-8")).hexdigest() for c in chunks]
    todo = [(c, k) for c, k in zip(chunks, keys) if k not in store]

    if todo:
        resp = emb_client.embeddings.create(
            model=EMB_MODEL, input=[c[2] for c, _ in todo]
        )
        for (_, k), d in zip(todo, resp.data):
            store[k] = d.embedding
        CACHE.write_text(json.dumps(store), encoding="utf-8")
        print("新嵌入", len(todo), "段，缓存共", len(store), "段")
    else:
        print("全部命中缓存，", len(store), "段")

    _vectors = [(c[0], c[1], c[2], store[k]) for c, k in zip(chunks, keys)]


def search_docs(query: str, top_k: int = TOP_K) -> str:
    """在 docs 目录里按语义检索相关段落"""
    _load_vectors()
    if not _vectors:
        return "docs 目录里没有可检索的内容"

    qv = emb_client.embeddings.create(model=EMB_MODEL, input=[query]).data[0].embedding
    ranked = sorted(_vectors, key=lambda v: -_cos(qv, v[3]))
    top = [r for r in ranked[:top_k] if _cos(qv, r[3]) > MIN_SCORE]

    if not top:
        return "没有找到语义足够相关的内容"
    return "\n\n".join(f"【{n} 第{i + 1}段】{p[:800]}" for n, i, p, _ in top)


# ---------------- 文件工具 ----------------
def get_time() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def list_files(subdir: str = ".") -> str:
    target = (BASE / subdir).resolve()
    if BASE != target and BASE not in target.parents:
        return "错误：只能访问项目目录内的文件"
    if not target.is_dir():
        return f"错误：{subdir} 不是目录"
    items = []
    for p in sorted(target.iterdir()):
        if p.name in {".venv", "__pycache__", ".git", ".cache"}:
            continue
        items.append(("[目录]" if p.is_dir() else "[文件]") + " " + p.name)
    return "\n".join(items) or "（空目录）"


def read_file(path: str) -> str:
    target = (BASE / path).resolve()
    if BASE != target and BASE not in target.parents:
        return "错误：只能访问项目目录内的文件"
    if not target.is_file():
        return f"错误：文件不存在 {path}"
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > 4000:
        return text[:4000] + f"\n\n...（已截断，原文共 {len(text)} 字符）"
    return text


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "在用户文档库(docs)中语义检索。回答任何关于用户资料的问题前必须先调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词，用用户的原始问题"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取当前本地时间",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出项目目录下的文件",
            "parameters": {
                "type": "object",
                "properties": {"subdir": {"type": "string", "description": "子目录，默认 ."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取项目内某个文本文件的内容",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "相对项目根目录的路径"}},
                "required": ["path"],
            },
        },
    },
]

REGISTRY = {
    "search_docs": search_docs,
    "get_time": get_time,
    "list_files": list_files,
    "read_file": read_file,
}


# ---------------- Agent 循环 ----------------
def run_turn(messages, max_steps=8):
    for _ in range(max_steps):
        resp = client.chat.completions.create(
            model=CHAT_MODEL, messages=messages, tools=TOOLS
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content

        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            print("  [工具]", name, args)
            try:
                result = REGISTRY[name](**args)
            except Exception as e:
                result = f"工具执行出错：{e}"
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": str(result)}
            )

    return "（达到最大步数，未得出最终答案）"


SYSTEM = (
    "你是一个助手。回答关于用户资料的问题时，必须先调用 search_docs 检索，"
    "再基于检索结果回答；检索不到就直说不知道，不要编造。"
    "回答时先给结论，只有确实存在多个不同可能时才列候选。"
)


def chat():
    messages = [{"role": "system", "content": SYSTEM}]
    print("输入问题开始对话，输入 exit 退出\n")
    while True:
        q = input("你: ").strip()
        if q.lower() in {"exit", "quit", "q"}:
            break
        if not q:
            continue
        messages.append({"role": "user", "content": q})
        print("\nAgent:", run_turn(messages), "\n")


if __name__ == "__main__":
    chat()

