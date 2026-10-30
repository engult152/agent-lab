# agent-lab

![eval](https://github.com/engult152/agent-lab/actions/workflows/eval.yml/badge.svg)

一个基于 RAG 的本地知识库助手：把自己的文档（Markdown / 文本 / PDF）变成可以对话的资料库。

**回答带出处，查不到就说不知道。**

🔗 在线体验：https://agent-lab-fcqjtemgvcdmsehyskgwqm.streamlit.app/

## 功能

- **语义检索 + 关键词检索融合**：向量召回 + BM25，RRF 融合（「敲命令没反应」能找到「PATH 没配」，「普拉达」也能精确命中）
- **多轮对话**：记得上下文，可追问、可纠正；超过 6 轮自动裁剪，防止 token 无限增长
- **工具调用**：`search_docs` / `grep_docs` / `outline` / `read_section` / `read_file` / `list_files`，由模型自己决定调哪个
- **图片版 PDF**：用视觉模型逐页转录，把截图型 PDF 变成可检索文本
- **流式输出**：首字 1 秒内出现
- **拒答**：检索不到时明确说不知道，不编造
- **上传与管理**：侧边栏上传文档、查看知识库、删除文件，实时重建索引
- **会话持久化**：本地 SQLite / 云端 Turso，重启不丢，可切换历史会话

## 架构

```
用户提问
   │
   ├─ 查询改写（长问题压成关键词）
   │
   ├─ 混合检索 ──── docs/ ──→ 切块 ──→ embedding ──→ .cache/vectors.json
   │     ├─ 向量：余弦相似度（numpy 矩阵化）
   │     ├─ 关键词：BM25（预计算 TF）
   │     └─ RRF 融合 → 阈值过滤 → top-5
   │
   ├─ 模型决策 ──→ 调工具？──→ search / grep / outline / read_section / read_file
   │                   │
   │                   └─ 结果回填，再决策（最多 8 轮）
   │
   └─ 生成回答（流式）
```

两个入口：`main.py` 终端版，`app.py` Streamlit 网页版，共用同一套内核。

## 快速开始

```bash
uv sync

# 新建 .env
DEEPSEEK_API_KEY=sk-xxx          # 对话模型
SILICONFLOW_API_KEY=sk-xxx       # embedding 模型

# 把你的文档放进 docs/

uv run streamlit run app.py      # 网页版
uv run python main.py            # 终端版
```

## 评估

测试集 **69 条**（56 正例 + 13 负例），覆盖原词提问、口语改写、否定拒答三类。

| 指标 | 结果 | 说明 |
|---|---|---|
| 检索召回 | **55/56 = 98%** | 正确段落在 top-5 内的比例 |
| 负例拒答 | **13/13** | 文档里没有的问题，明确说不知道 |
| 端到端准确率 | **66/69 = 96%** | 真跑 Agent，用独立模型 `Qwen3-8B` 当裁判 |
| 单问响应 | 1.9 ~ 3.5 秒 | 含检索 + 两次模型调用 |
| 冷启动索引 | 0.001 秒 | 向量有本地缓存，只算新增段落 |
| 检索耗时（735 段） | 0.005 秒 | numpy 矩阵化后 |

复现：

```bash
uv run python eval.py           # 检索层（不调模型，CI 用）
uv run python eval_judge.py     # 端到端 + LLM 裁判
uv run python eval_stability.py # 同一问题跑 3 次，看稳定性
```

CI：每次 push 自动跑 `eval.py`，**召回低于 90% 直接失败**。

## 几个设计决策

**阈值 0.60 是扫出来的，不是拍的**

在测试集上从 0.45 扫到 0.70：0.55 时负例只剩 10/13，0.60 时负例满分、正例 89%，0.65 正例断崖。阈值没有通用值，必须按自己的数据分布扫。

**混合检索用 RRF，不是加权相加**

余弦相似度和 BM25 分数**量纲完全不同**，直接相加没有意义。RRF 只看「排第几」，天然可比。

**切块时把章节标题拼进每块**

否则问「第六章 BOSS 怎么打」时，那块内容里根本没有「第六章」三个字，向量自然对不上。

**用视觉模型而不是 OCR 处理扫描版 PDF**

传统 OCR 只认字、不懂版面，图注、表格、章节标题会全乱。视觉模型理解版面，能只转录正文、忽略导航和页脚。

**纯 Python + numpy，不上向量数据库**

735 段检索 0.005 秒，按此推算 2 万段约 0.14 秒。这一规模用 Chroma/Qdrant 属于过度设计。

## 已知局限

- 「接下来该干嘛」这类流程问题，答案散落在长段落里，召回率低于事实类问题（靠 grep + read_section 兜底）
- 只支持 md / txt / PDF，不支持 docx、网页
- 云端重启后**上传的文档**会丢失（Streamlit Cloud 用临时文件系统）；会话已通过 Turso 持久化
- 多用户**会话**已隔离（URL 中的 uid），但知识库文档仍共用一份
- GitHub README 的图片在国内加载不出来（`raw.githubusercontent.com` 不可达）

## 目录结构

```
main.py            内核：切块 / 检索 / 工具 / Agent 循环
app.py             Streamlit 网页界面
store.py           SQLite 会话持久化
pdf2md.py          图片版 PDF → 文本（视觉模型，断点续跑）
eval.py            检索层评估（CI 用）
eval_judge.py      端到端评估（LLM 裁判）
eval_stability.py  稳定性测试
eval/cases.json    69 条测试用例
docs/              知识库
.github/workflows/ CI
scripts/           调试与压测脚本
```

## 踩过的坑

见 [`docs/踩坑记录.md`](docs/踩坑记录.md)——16 条真实记录，包括：

- 图片版 PDF 放进 `docs/` 让切块慢了 6 秒（解析空转）
- 清理攻略页眉噪音，检索从 93% 到 98%
- 提示词里两条规则冲突，模型永远选「说不知道」那条
- 评估脚本自己出过 3 个 bug，每个都表现得像系统故障
