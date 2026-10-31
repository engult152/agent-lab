
from pathlib import Path
import base64
import json
import time
import uuid

import streamlit as st
import os

import streamlit as st

try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:
    pass

import main  # noqa: E402
import store  # noqa: E402

st.set_page_config(page_title="引文 · 资料问答", page_icon="📖", layout="centered")

_CSS = """
<style>
:root{
  --bg:#eef5f0;          /* 浅薄荷底 */
  --surface:#ffffff;
  --ink:#12233a;         /* 深藏青文字 */
  --muted:#5b6b7c;
  --mint:#ddf0e6;        /* 浅薄荷块 */
  --mint-deep:#b9e2cd;
  --accent:#3f8f6b;      /* 少量强调 */
  --shadow-sm:0 2px 6px rgba(18,35,58,.05), 0 1px 2px rgba(18,35,58,.04);
  --shadow-md:0 12px 32px rgba(18,35,58,.08), 0 2px 8px rgba(18,35,58,.04);
}
.stApp{
  background:
    radial-gradient(900px 500px at 12% -8%, #e4f3ea 0%, rgba(228,243,234,0) 60%),
    radial-gradient(800px 520px at 92% 4%, #eaf1fb 0%, rgba(234,241,251,0) 62%),
    var(--bg);
}
html,body{font-family:"PingFang SC","HarmonyOS Sans SC","MiSans","Microsoft YaHei",system-ui,sans-serif;}
.block-container{padding-top:2.6rem;max-width:860px;}
h1,h2,h3{letter-spacing:-.015em;color:var(--ink);font-weight:700;}
p,li{line-height:1.8;color:var(--ink);}

/* 顶部标题：宋体 + 印章徽标 */
.hero{display:flex;gap:16px;align-items:center;margin:0 0 26px;}
.hero .mark{
  width:54px;height:54px;border-radius:12px;
  background:#a8402f;color:#fff;
  font-family:"Source Han Serif SC","Noto Serif SC","Songti SC","SimSun",serif;
  font-size:28px;font-weight:700;line-height:1;
  display:flex;align-items:center;justify-content:center;flex:0 0 auto;
  transform:rotate(-2deg);
  box-shadow:inset 0 0 0 2px rgba(255,255,255,.22), var(--shadow-md);
}
.hero h1{
  margin:0;font-size:32px;font-weight:700;letter-spacing:.04em;
  font-family:"Source Han Serif SC","Noto Serif SC","Songti SC","SimSun",serif;
}
.hero p{margin:6px 0 0;color:var(--muted);font-size:14px;letter-spacing:.01em;}

/* 侧边栏 */
section[data-testid="stSidebar"]{background:rgba(255,255,255,.72);border-right:none;
  box-shadow:1px 0 0 rgba(18,35,58,.05);backdrop-filter:blur(8px);}
section[data-testid="stSidebar"] .block-container{padding-top:1.6rem;}
[data-testid="stMetricValue"]{font-size:40px;font-weight:700;color:var(--ink);letter-spacing:-.02em;}
[data-testid="stMetricLabel"]{color:var(--muted);}

/* 消息：白色浮起卡片 */
[data-testid="stChatMessage"]{
  background:var(--surface);border-radius:22px;padding:1rem 1.15rem;margin:.55rem 0;
  box-shadow:var(--shadow-sm);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]){
  background:var(--mint);box-shadow:none;
}
[data-testid="stChatMessage"] p{margin:.25rem 0;}

/* 输入框：统一圆角，去掉内外两层不一致的角 */
[data-testid="stBottom"], [data-testid="stBottom"] > div{background:transparent!important;}
[data-testid="stChatInput"]{
  border:none;border-radius:16px;background:var(--surface);box-shadow:var(--shadow-md);
}
[data-testid="stChatInput"] > div{
  border-radius:16px!important;background:transparent!important;box-shadow:none!important;
}
[data-testid="stChatInput"] textarea{
  border-radius:16px!important;background:transparent!important;box-shadow:none!important;
}
[data-testid="stChatInput"] button{border-radius:12px!important;}
[data-testid="stChatInput"]:focus-within{box-shadow:0 0 0 3px var(--mint-deep), var(--shadow-md);}

/* 按钮：药丸 */
.stButton>button{
  border-radius:999px;border:none;background:var(--surface);color:var(--ink);
  box-shadow:var(--shadow-sm);padding:.5rem 1.05rem;font-weight:500;
  transition:transform .18s cubic-bezier(.2,.8,.2,1), box-shadow .18s;
}
.stButton>button:hover{transform:translateY(-1px);box-shadow:var(--shadow-md);color:var(--accent);}
.stButton>button:active{transform:translateY(0);}

/* 折叠面板 / 分割线 */
[data-testid="stExpander"]{border:none;border-radius:18px;background:var(--surface);box-shadow:var(--shadow-sm);}
[data-testid="stExpander"] summary{border-radius:18px;}
hr{border:none;height:1px;background:rgba(18,35,58,.06);}

/* 上传区 */
[data-testid="stFileUploaderDropzone"]{border:1.5px dashed var(--mint-deep);border-radius:18px;background:var(--surface);}

/* 代码块 */
code{background:var(--mint);color:#12402c;border-radius:6px;padding:.1rem .35rem;}
pre{border-radius:16px;box-shadow:var(--shadow-sm);}

@media (prefers-reduced-motion:reduce){*{transition:none!important;}}

/* 只隐藏 Deploy 按钮；保留侧边栏开关和右上角菜单 */
[data-testid="stAppDeployButton"]{display:none!important;}
#MainMenu{visibility:hidden;}
[data-testid="stHeader"]{background:transparent!important;}
/* 侧边栏收起后的「展开」按钮一定要看得见 */
[data-testid="stSidebarCollapsedControl"]{display:block!important;visibility:visible!important;z-index:999999;}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

_pwd = os.environ.get("APP_PASSWORD", "")
if _pwd and not st.session_state.get("ok"):
    st.title("🔒 需要密码")
    if st.text_input("访问密码", type="password") == _pwd:
        st.session_state["ok"] = True
        st.rerun()
    st.stop()

st.markdown(
    '<div class="hero"><div class="mark">引</div>'
    "<div><h1>引文</h1>"
    "<p>问你自己的资料，答案带原文出处 · 无出处不答</p></div></div>",
    unsafe_allow_html=True,
)


def run(messages, placeholder, max_steps=8):
    """流式版 Agent 循环"""
    trace = []

    # 只保留 system + 最近 12 条，防止上下文无限增长
    if len(messages) > 13:
        messages = [messages[0]] + messages[-12:]

    for _ in range(max_steps):
        stream = main.client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=main.TOOLS, stream=True
        )

        content = ""
        last = 0.0
        calls = {}

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                content += delta.content
                now = time.time()
                if now - last > 0.05:
                    placeholder.markdown(content + "▌")
                    last = now

            for tc in delta.tool_calls or []:
                slot = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function is not None:
                    if tc.function.name:
                        slot["name"] += tc.function.name
                    if tc.function.arguments:
                        slot["args"] += tc.function.arguments

        if not calls:
            placeholder.markdown(content)
            return content, trace

        messages.append(
            {
                "role": "assistant",
                "content": content or None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["args"]},
                    }
                    for c in calls.values()
                ],
            }
        )

        for c in calls.values():
            try:
                args = json.loads(c["args"] or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                result = main.REGISTRY[c["name"]](**args)
            except Exception as e:
                result = "工具执行出错：" + str(e)
            trace.append((c["name"], args))
            print("  [工具]", c["name"], args, flush=True)
            messages.append(
                {"role": "tool", "tool_call_id": c["id"], "content": str(result)}
            )

        placeholder.markdown("正在检索……")

    return "（达到最大步数，未得出最终答案）", trace



# app.py 开头，SYSTEM 之前
def check_password():
    pwd = os.environ.get("APP_PASSWORD", "")
    if not pwd:
        return True
    if st.session_state.get("ok"):
        return True
    st.title("🔒 需要密码")
    if st.text_input("密码", type="password") == pwd:
        st.session_state.ok = True
        st.rerun()
    return False

if not check_password():
    st.stop()

SYSTEM = main.SYSTEM


if "uid" not in st.session_state:
    st.session_state.uid = st.query_params.get("u") or uuid.uuid4().hex[:8]
    st.query_params["u"] = st.session_state.uid


if "restored" not in st.session_state:
    st.session_state.restored = True
    changed = False
    for _name, _content, _is_bin in store.list_files(st.session_state.uid):
        _dir = Path("docs") / "uploads" / st.session_state.uid
        _dir.mkdir(parents=True, exist_ok=True)
        _p = _dir / _name
        if not _p.exists():
            if _is_bin:
                _p.write_bytes(base64.b64decode(_content))
            else:
                _p.write_text(_content, encoding="utf-8")
            changed = True
    if changed:
        main.reindex()

if "chat" not in st.session_state:
    st.session_state.sid = store.last_session_id(
        owner=st.session_state.uid
    ) or store.new_session(owner=st.session_state.uid)
    saved = store.load_messages(st.session_state.sid)
    st.session_state.chat = [{"role": r, "content": c} for r, c in saved]
    st.session_state.history = [{"role": "system", "content": SYSTEM}] + [
        {"role": r, "content": c} for r, c in saved
    ]

DAILY_LIMIT = 10

with st.sidebar:
    st.subheader("状态")
    st.metric(
        "文档段落",
        sum(1 for c in main._chunks() if c[3] in ("", st.session_state.uid)),
    )
    st.caption("今日已用 " + str(store.usage_today()) + " / " + str(DAILY_LIMIT))
    st.caption("修改 docs 里的文件后，重启页面即可生效")

    st.divider()
    up = st.file_uploader("添加文档", type=["md", "txt", "pdf"])
    if up is not None:
        try:
            target = Path("docs") / "uploads" / st.session_state.uid / up.name
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = bytes(up.getbuffer())
            target.write_bytes(raw)
            if len(raw) > 3 * 1024 * 1024:
                st.warning("文件超过 3MB，本次不持久化（重启后需重新上传）")
            elif up.name.lower().endswith(".pdf"):
                store.save_file(
                    st.session_state.uid,
                    up.name,
                    base64.b64encode(raw).decode("ascii"),
                    True,
                )
            else:
                store.save_file(
                    st.session_state.uid,
                    up.name,
                    raw.decode("utf-8", errors="replace"),
                    False,
                )
            main.reindex()
            st.success("已添加：" + up.name)
        except Exception as e:
            st.error("添加失败：" + str(e))

    st.divider()
    with st.expander("知识库（点击展开）"):
        counts = {}
        for c in main._chunks():
            if c[3] not in ("", st.session_state.uid):
                continue
            counts[c[0]] = counts.get(c[0], 0) + 1
        for i, (name, n) in enumerate(counts.items()):
            col1, col2 = st.columns([6, 2])
            col1.caption(name + " · " + str(n) + " 段")
            if col2.button("删", key="del_" + str(i)):
                try:
                    (Path("docs") / name).unlink()
                    main.reindex()
                    st.rerun()
                except Exception as e:
                    st.error("删除失败：" + str(e))
    with st.expander("历史会话"):
        for sid, title, created in store.list_sessions(10):
            label = (title or "空对话")[:14] + "  " + (created or "")[5:16].replace("T", " ")
            if st.button(label, key="sess_" + str(sid), use_container_width=True):
                rows = store.load_messages(sid)
                st.session_state.sid = sid
                st.session_state.chat = [{"role": r, "content": c} for r, c in rows]
                st.session_state.history = [{"role": "system", "content": SYSTEM}] + [
                    {"role": r, "content": c} for r, c in rows
                ]
                st.rerun()
    if st.button("新对话", use_container_width=True):
        st.session_state.sid = store.new_session()
        st.session_state.chat = []
        st.session_state.history = [{"role": "system", "content": SYSTEM}]
        st.rerun()

    if st.button("清空对话", use_container_width=True):
        st.session_state.chat = []
        st.session_state.history = [{"role": "system", "content": SYSTEM}]
        st.rerun()

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

q = st.chat_input("问点什么，比如：401 错误怎么排查？")

if q:
    main._UID.set(st.session_state.uid)
    if store.usage_today() >= DAILY_LIMIT:
        st.error("今天的调用次数已用完（上限 " + str(DAILY_LIMIT) + " 次），明天再来。")
        st.stop()
    store.bump_usage()

    st.session_state.chat.append({"role": "user", "content": q})
    st.session_state.history.append({"role": "user", "content": q})

    with st.chat_message("user"):
        st.markdown(q)
        with st.chat_message("assistant"):
            ph = st.empty()
            ph.markdown("正在检索……")
            t0 = time.time()
            reply, trace = run(st.session_state.history, ph)
            elapsed = time.time() - t0

        if trace:
            with st.expander("查看工具调用"):
                for name, args in trace:
                    st.code(name + "(" + json.dumps(args, ensure_ascii=False) + ")")

        ph.markdown(reply)
        est = int(
            (sum(len(str(m.get("content") or "")) for m in st.session_state.history) + len(reply))
            / 1.5
        )
        st.caption("⏱ " + format(elapsed, ".1f") + "s · 约 " + str(est) + " tokens")

    st.session_state.chat.append({"role": "assistant", "content": reply})
    store.add_message(st.session_state.sid, "user", q)
    store.add_message(st.session_state.sid, "assistant", reply)