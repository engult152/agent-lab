import json
import streamlit as st
import main

st.set_page_config(page_title="笔记助手", page_icon="📚", layout="centered")
st.title("📚 我的笔记助手")
st.caption("基于 docs 目录的语义检索，回答会标明出处")


def run(messages, max_steps=8):
    """跑一轮对话，返回 (回答, 工具调用记录)"""
    trace = []
    for _ in range(max_steps):
        resp = main.client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=main.TOOLS
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content, trace

        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            try:
                result = main.REGISTRY[name](**args)
            except Exception as e:
                result = "工具执行出错：" + str(e)
            trace.append((name, args))
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": str(result)}
            )

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
    st.caption("修改 docs 里的文件后，重新运行本页即可生效")
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
        with st.spinner("检索中…"):
            reply, trace = run(st.session_state.history)

        if trace:
            with st.expander("查看工具调用"):
                for name, args in trace:
                    st.code(name + "(" + json.dumps(args, ensure_ascii=False) + ")")

        st.markdown(reply)

    st.session_state.chat.append({"role": "assistant", "content": reply})
