
from pathlib import Path
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

st.set_page_config(page_title="笔记助手", page_icon="📚", layout="centered")

_pwd = os.environ.get("APP_PASSWORD", "")
if _pwd and not st.session_state.get("ok"):
    st.title("🔒 需要密码")
    if st.text_input("访问密码", type="password") == _pwd:
        st.session_state["ok"] = True
        st.rerun()
    st.stop()

st.title("📚 我的笔记助手")
st.caption("基于 docs 目录的语义检索，回答会标明出处")


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

if "chat" not in st.session_state:
    st.session_state.sid = store.last_session_id(
        owner=st.session_state.uid
    ) or store.new_session(owner=st.session_state.uid)
    saved = store.load_messages(st.session_state.sid)
    st.session_state.chat = [{"role": r, "content": c} for r, c in saved]
    st.session_state.history = [{"role": "system", "content": SYSTEM}] + [
        {"role": r, "content": c} for r, c in saved
    ]

with st.sidebar:
    st.subheader("状态")
    st.metric("文档段落", len(main._chunks()))
    st.caption("今日已用 " + str(store.usage_today()) + " / 80")
    st.caption("修改 docs 里的文件后，重启页面即可生效")

    st.divider()
    up = st.file_uploader("添加文档", type=["md", "txt", "pdf"])
    if up is not None:
        try:
            target = Path("docs") / up.name
            target.write_bytes(up.getbuffer())
            main.reindex()
            st.success("已添加：" + up.name)
        except Exception as e:
            st.error("添加失败：" + str(e))

    st.divider()
    with st.expander("知识库（点击展开）"):
        counts = {}
        for c in main._chunks():
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
    DAILY_LIMIT = 80
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