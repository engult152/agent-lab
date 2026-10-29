import os
import json
import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# 允许访问的目录：项目根目录
BASE = Path(__file__).resolve().parent


# ---------- 工具 ----------
def get_time() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def list_files(subdir: str = ".") -> str:
    """列出项目目录下的文件"""
    target = (BASE / subdir).resolve()
    if BASE != target and BASE not in target.parents:
        return "错误：只能访问项目目录内的文件"
    if not target.is_dir():
        return f"错误：{subdir} 不是目录"

    items = []
    for p in sorted(target.iterdir()):
        if p.name in {".venv", "__pycache__", ".git"}:
            continue
        items.append(f"{'[目录]' if p.is_dir() else '[文件]'} {p.name}")
    return "\n".join(items) or "（空目录）"


def read_file(path: str) -> str:
    """读取项目内的文本文件，最多返回 4000 字符"""
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
            "name": "get_time",
            "description": "获取当前本地时间",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出项目目录下的文件。用户问「有哪些文件」「项目结构」时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "subdir": {"type": "string", "description": "子目录，默认为当前目录 ."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取项目内某个文本文件的内容。需要看代码、配置、文档时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对项目根目录的文件路径，例如 main.py"}
                },
                "required": ["path"],
            },
        },
    },
]

REGISTRY = {
    "get_time": get_time,
    "list_files": list_files,
    "read_file": read_file,
}


# ---------- Agent 主循环 ----------
# ---------- 检索 docs 目录 ----------
DOCS = Path(__file__).resolve().parent / "docs"


def _terms(query: str) -> list:
    terms = set()
    for w in query.replace("，", " ").replace("？", " ").replace(",", " ").replace("?", " ").split():
        if w.isascii():
            if len(w) >= 2:
                terms.add(w.lower())
        elif len(w) <= 2:
            terms.add(w)
        else:
            terms.update(w[i : i + 2] for i in range(len(w) - 1))
    return list(terms)


def _chunks():
    chunks = []
    if not DOCS.is_dir():
        return chunks
    for f in sorted(DOCS.rglob("*")):
        if f.suffix.lower() not in {".md", ".txt"}:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for i, para in enumerate(text.split("\n\n")):
            para = para.strip()
            if len(para) > 20:
                chunks.append((f.name, i, para))
    return chunks


def search_docs(query: str, top_k: int = 3) -> str:
    terms = _terms(query)
    if not terms:
        return "查询词太短，请说具体一点"

    scored = []
    for name, idx, para in _chunks():
        score = sum(para.lower().count(t) for t in terms)
        if score:
            scored.append((score, name, idx, para))

    if not scored:
        return "docs 目录里没有找到相关内容"

    scored.sort(key=lambda x: -x[0])
    return "\n\n".join(
        f"【{name} 第{idx + 1}段】{para[:800]}" for _, name, idx, para in scored[:top_k]
    )


REGISTRY["search_docs"] = search_docs
TOOLS.append(
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "在用户自己的文档库（docs 目录）中检索相关段落。回答任何关于「我的笔记/资料里写了什么」的问题前必须先调用它",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词，用用户的原始问题即可"}
                },
                "required": ["query"],
            },
        },
    }
)


# ---------- 多轮对话 ----------
def run_turn(messages: list, max_steps: int = 8) -> str:
    for step in range(max_steps):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content

        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            print(f"  [工具] {name}({args})")
            try:
                result = REGISTRY[name](**args)
            except Exception as e:
                result = f"工具执行出错：{e}"
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": str(result)}
            )

    return "（达到最大步数，未得出最终答案）"


def chat():
    messages = [
        {
            "role": "system",
            "content": "你是一个助手。回答关于用户资料的问题时，必须先调用 search_docs 检索，再基于检索结果回答；检索不到就直说不知道，不要编造。回答时先给结论，只有确实存在多个不同可能时才列候选，不要把所有检索到的段落罗列一遍。",
        }
    ]
    print("输入问题开始对话，输入 exit 退出\n")

    while True:
        q = input("你: ").strip()
        if q.lower() in {"exit", "quit", "q"}:
            break
        if not q:
            continue

        messages.append({"role": "user", "content": q})
        reply = run_turn(messages)
        print(f"\nAgent: {reply}\n")


# ========== 向量检索版（覆盖上面的关键词版） ==========
import math

EMB_MODEL = "BAAI/bge-m3"
emb_client = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

_vectors = []


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)


def _load_vectors():
    global _vectors
    if _vectors:
        return
    chunks = _chunks()
    if not chunks:
        return
    resp = emb_client.embeddings.create(model=EMB_MODEL, input=[c[2] for c in chunks])
    _vectors = [
        (chunks[i][0], chunks[i][1], chunks[i][2], d.embedding)
        for i, d in enumerate(resp.data)
    ]


def search_docs_v2(query: str, top_k: int = 3) -> str:
    _load_vectors()
    if not _vectors:
        return "docs 目录里没有可检索的内容"

    qv = emb_client.embeddings.create(model=EMB_MODEL, input=[query]).data[0].embedding
    ranked = sorted(_vectors, key=lambda v: -_cos(qv, v[3]))

    top = [r for r in ranked[:top_k] if _cos(qv, r[3]) > 0.45]
    if not top:
        return "没有找到语义足够相关的内容"

    return "\n\n".join(f"【{n} 第{i + 1}段】{p[:800]}" for n, i, p, _ in top)


REGISTRY["search_docs"] = search_docs_v2

# ========== PDF 支持 ==========
from pypdf import PdfReader


def _chunks_pdf():
    out = []
    if not DOCS.is_dir():
        return out
    for f in sorted(DOCS.rglob("*")):
        suffix = f.suffix.lower()
        if suffix not in {".md", ".txt", ".pdf"}:
            continue
        try:
            if suffix == ".pdf":
                reader = PdfReader(str(f))
                text = " ".join(
                    " ".join((p.extract_text() or "").split()) for p in reader.pages
                )
                paras = [text[i : i + 400] for i in range(0, len(text), 320)]
            else:
                raw = f.read_text(encoding="utf-8", errors="replace")
                paras = raw.split("\n\n")
        except Exception as e:
            print("跳过", f.name, ":", e)
            continue
        for i, para in enumerate(paras):
            para = para.strip()
            if len(para) > 20:
                out.append((f.name, i, para))
    return out


_chunks = _chunks_pdf

# ========== 向量缓存 ==========
import hashlib

CACHE = Path(__file__).resolve().parent / ".cache" / "vectors.json"


def _load_vectors_cached():
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
        for (c, k), d in zip(todo, resp.data):
            store[k] = d.embedding
        CACHE.write_text(json.dumps(store), encoding="utf-8")
        print("新嵌入", len(todo), "段，缓存共", len(store), "段")
    else:
        print("全部命中缓存，", len(store), "段")

    _vectors = [(c[0], c[1], c[2], store[k]) for c, k in zip(chunks, keys)]


_load_vectors = _load_vectors_cached

if __name__ == "__main__":
    chat()




