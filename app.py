import json
import time

import streamlit as st
import main

st.set_page_config(page_title="笔记助手", page_icon="📚", layout="centered")
st.title("📚 我的笔记助手")
st.caption("基于 docs 目录的语义检索，回答会标明出处")


def run(messages, placeholder, max_steps=8):
    """流式版的 Agent 循环，返回 (回答, 工具调用记录)"""
    trace = []

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
            messages.append(
                {"role": "tool", "tool_call_id": c["id"], "content": str(result)}
            )

        placeholder.markdown("正在检索……")

    return "（达到最大步数，未得出最终答案）", trace


SYSTEM = (
    "你是一个助手。回答关于用户资料的问题时，必须先调用 search_docs 检索，"
    "再基于检索结果回答；检索不到就直说不知道，不要编造。"
    "回答时先给结论，只有确实存在多个不同可能时才列候选。"
)

if "chat" not in st.session_state:
    st.session_state.chat = []
    st.session_state.history = [{"role": "system", "content": SYSTEM}]

with st.sidebar:
    st.subheader("状态")
    st.metric("文档段落", len(main._chunks()))
    st.caption("修改 docs 里的文件后，重启页面即可生效")
    if st.button("清空对话", use_container_width=True):
        st.session_state.chat = []
        st.session_state.history = [{"role": "system", "content": SYSTEM}]
        st.rerun()

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

q = st.chat_input("问点什么，比如：401 错误怎么排查？")

if q:
    st.session_state.chat.append({"role": "user", "content": q})
    st.session_state.history.append({"role": "user", "content": q})

    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        ph = st.empty()
        ph.markdown("正在检索……")
        reply, trace = run(st.session_state.history, ph)

        if trace:
            with st.expander("查看工具调用"):
                for name, args in trace:
                    st.code(name + "(" + json.dumps(args, ensure_ascii=False) + ")")

        ph.markdown(reply)

    st.session_state.chat.append({"role": "assistant", "content": reply})