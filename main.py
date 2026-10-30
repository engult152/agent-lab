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
TOP_K = 5
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

def _normalize(text: str) -> str:
    """中文之间的换行直接去掉，其余空白压成单空格"""
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s*\n\s*(?=[\u4e00-\u9fff])", "", text)
    return re.sub(r"\s+", " ", text).strip()

def _pdf_pieces(path: Path):
    reader = PdfReader(str(path))
    text = " ".join(
        " ".join((p.extract_text() or "").split()) for p in reader.pages
    )
    text = _normalize(text)
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

        body = _normalize(re.sub(r"<!--.*?-->", "", body))
        if len(body) < 40:
            continue

        prefix = (heading + "｜") if heading else ""

        if len(body) <= 400:
            pieces.append(prefix + body)
        else:
            for i in range(0, len(body), 320):
                seg = body[i : i + 400].strip()
                if len(seg) > 40:
                    pieces.append(prefix + seg)

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

_STOP = [
    "我想知道", "请问", "帮我", "一下", "怎么样", "怎么办", "为什么",
    "是什么", "怎么", "什么", "之后", "然后", "还有", "那个", "这个",
    "哪个", "是不是", "该干嘛", "干嘛", "在哪", "哪里", "能不能",
    "可不可以", "比较好", "呢", "吗", "啊", "吧", "我在", "那边",
]


def _rewrite(q: str) -> str:
    """长问题压成关键词；短问题原样返回"""
    if len(q) <= 25:
        return q
    s = q
    for w in _STOP:
        s = s.replace(w, " ")
    s = re.sub(r"[，。！？、；：（）《》“”‘’]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) >= 4 else q

def search_docs(query: str, top_k: int = TOP_K) -> str:
    """在 docs 目录里按语义检索相关段落"""
    _load_vectors()
    if not _vectors:
        return "docs 目录里没有可检索的内容"

    qv = emb_client.embeddings.create(model=EMB_MODEL, input=[_rewrite(query)]).data[0].embedding
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
                       "description": (
                "在用户文档库(docs)中语义检索。回答任何技术问题前必须先调用。"
                "query 里请一次写全多个同义词（空格分隔），例如 "
                "「解决 修复 报错 无效 失败」，避免用不同措辞反复检索。"
            ),
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

def reindex():
    """清空内存索引，下次检索时重建（新增/修改文档后调用）"""
    global _vectors
    _vectors = []
    _bm["n"] = 0


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
    "你是一个助手。回答任何技术问题（装环境、报错、配置、命令用法、游戏攻略等）时，"
    "都必须先调用 search_docs 检索用户资料。"
    "资料里确实没有时，才可以用通用知识回答，但要明确说明「这部分不来自你的资料」。"
    "检索不到就直说不知道，不要编造。回答时先给结论，只有确实存在多个不同可能时才列候选。"
    "回答控制在 200 字以内，只给要点，不要复述资料原文。"
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



# ========== 混合检索：BM25 + 向量，RRF 融合 ==========
import collections

_bm = {"df": {}, "docs": [], "len": [], "avgdl": 0.0, "n": 0}


def _tokenize(text: str) -> list:
    toks = re.findall(r"[a-z0-9_]+", text.lower())
    for h in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(h) == 1:
            toks.append(h)
        else:
            toks.extend(h[i : i + 2] for i in range(len(h) - 1))
    return toks


def _build_bm25():
    if _bm["n"]:
        return
    docs = [_tokenize(v[2]) for v in _vectors]
    df = collections.Counter()
    for d in docs:
        df.update(set(d))
    _bm["df"] = df
    _bm["docs"] = docs
    _bm["len"] = [len(d) for d in docs]
    _bm["avgdl"] = sum(_bm["len"]) / max(1, len(docs))
    _bm["n"] = len(docs)


def _bm25_scores(query: str) -> list:
    _build_bm25()
    k1, b = 1.5, 0.75
    qt = _tokenize(query)
    n = _bm["n"]
    scores = []
    for i, d in enumerate(_bm["docs"]):
        tf = collections.Counter(d)
        s = 0.0
        for t in qt:
            f = tf.get(t)
            if not f:
                continue
            dfi = _bm["df"].get(t, 0)
            idf = math.log(1 + (n - dfi + 0.5) / (dfi + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * _bm["len"][i] / _bm["avgdl"]))
        scores.append(s)
    return scores

BM_WEIGHT = 0.7
COS_FLOOR = 0.35
FINAL_FLOOR = 0.60

def search_docs_hybrid(query: str, top_k: int = TOP_K, pool: int = 20) -> str:
    _load_vectors()
    if not _vectors:
        return "docs 目录里没有可检索的内容"

    q = _rewrite(query)
    qv = emb_client.embeddings.create(model=EMB_MODEL, input=[q]).data[0].embedding

    cos = [_cos(qv, v[3]) for v in _vectors]
    vec_rank = sorted(range(len(cos)), key=lambda i: -cos[i])[:pool]

    bm = _bm25_scores(q)
    if max(bm or [0]) <= 0:
        bm_rank = []
    else:
        bm_rank = sorted(range(len(bm)), key=lambda i: -bm[i])[:pool]

        rrf = collections.Counter()
    for r, i in enumerate(vec_rank):
        rrf[i] += 1.0 / (60 + r + 1)
    for r, i in enumerate(bm_rank):
        if cos[i] >= COS_FLOOR:
            rrf[i] += BM_WEIGHT / (60 + r + 1)

    if not rrf:
        return "没有找到语义足够相关的内容"

    picked = [i for i, _ in rrf.most_common(top_k)]
    picked = [i for i in picked if cos[i] >= FINAL_FLOOR]
    if not picked:
        return "没有找到语义足够相关的内容"
    return "\n\n".join(
        f"【{_vectors[i][0]} 第{_vectors[i][1] + 1}段】{_vectors[i][2][:800]}" for i in picked
    )

search_docs = search_docs_hybrid



REGISTRY["search_docs"] = search_docs_hybrid

def reindex():
    """清空内存索引，下次检索时重建（新增/修改文档后调用）"""
    global _vectors
    _vectors = []
    _bm["n"] = 0
# ========== 章节浏览工具 ==========
def outline() -> str:
    """列出 docs 下每个文件的标题结构"""
    lines = []
    for f in sorted(DOCS.rglob("*")):
        if f.suffix.lower() not in {".md", ".txt"}:
            continue
        heads = [
            l.strip()
            for l in f.read_text(encoding="utf-8", errors="replace").splitlines()
            if l.strip().startswith("#")
        ]
        if heads:
            lines.append("[" + f.name + "] " + " / ".join(h.lstrip("#").strip() for h in heads[:40]))
    return "\n".join(lines) or "没有找到标题"


def read_section(file: str, heading: str) -> str:
    """按标题读取某个文档里的一整节"""
    target = (DOCS / file).resolve()
    if DOCS not in target.parents:
        return "错误：只能访问 docs 目录"
    if not target.is_file():
        return "错误：文件不存在 " + file

    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    start = None
    for i, l in enumerate(lines):
        if l.strip().startswith("#") and heading in l:
            start = i
            break
    if start is None:
        return "没找到标题包含「" + heading + "」的章节"

    out = []
    for l in lines[start:]:
        if out and l.strip().startswith("#"):
            break
        out.append(l)
    return "\n".join(out).strip()[:3500]


TOOLS.append(
    {
        "type": "function",
        "function": {
            "name": "outline",
            "description": "列出 docs 下所有文档的章节标题。查流程类问题时（接下来该干嘛、第几章怎么走）先用它看目录",
            "parameters": {"type": "object", "properties": {}},
        },
    }
)

TOOLS.append(
    {
        "type": "function",
        "function": {
            "name": "read_section",
            "description": "按标题读取某个文档里的一整节内容。先用 outline 拿到文件名和标题，再调用本工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "文件名，例如 神之天平攻略.md"},
                    "heading": {"type": "string", "description": "章节标题关键词，例如 第六章"},
                },
                "required": ["file", "heading"],
            },
        },
    }
)

REGISTRY["outline"] = outline
REGISTRY["read_section"] = read_section

SYSTEM = SYSTEM + (
    " 如果检索到的内容不足以回答流程类问题（例如「接下来该干嘛」「第几章怎么走」），"
    "必须先调用 outline 列出章节，再用 read_section 读取对应的整节，然后作答。"
)

def grep_docs(keyword: str, max_hits: int = 8) -> str:
    """在 docs 里按关键词逐行搜索，返回文件 + 章节 + 命中行"""
    hits = []
    for f in sorted(DOCS.rglob("*")):
        if f.suffix.lower() not in {".md", ".txt"}:
            continue
        heading = ""
        text = f.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("#"):
                heading = s.lstrip("#").strip()
                continue
            if keyword in s:
                hits.append(f.name + " [" + heading + "] " + s[:80])
                if len(hits) >= max_hits:
                    return "\n".join(hits)
    return "\n".join(hits) or "没有找到包含「" + keyword + "」的行"


TOOLS.append(
    {
        "type": "function",
        "function": {
            "name": "grep_docs",
            "description": "按关键词在文档里逐行搜索，返回命中的文件、所在章节和那一行。适合查「某个名词在哪一节」。比 outline 更精确，建议优先用它",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "关键词，例如 墓地、耳环、独角兽"}
                },
                "required": ["keyword"],
            },
        },
    }
)

REGISTRY["grep_docs"] = grep_docs

SYSTEM = SYSTEM + (
    " 查不到时，先调用 grep_docs 用关键词定位它在哪一节，再用 read_section 读那一节，"
    "不要凭章节名猜。"
)
if __name__ == "__main__":
    chat()
    








