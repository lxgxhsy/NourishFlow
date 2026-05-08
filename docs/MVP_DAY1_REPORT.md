# NourishFlow MVP Day 1 总报告

## 1. 完成度

### P1 骨架 + 健康检查
完成 FastAPI 后端骨架、PostgreSQL/Meilisearch 依赖配置、SQLModel 建表启动流程，以及 `/api/health` 健康检查端点。后续将启动事件改为 lifespan，避免 deprecated startup event。

关键 commit：`67be88a feat(p1): scaffold backend with PG/Meili and /api/health`、`01345ac refactor(p1): replace deprecated startup event and utcnow`

### P2 PDF 入库 + Meili 索引
完成 `parse_pdf(path) -> list[Section]` 接缝、pdfplumber 解析、800 字 + 100 overlap 固定窗口分块、PG 写入 articles/article_chunks，以及同步索引到 Meilisearch。MinerU 替换点保留在 `parse_pdf`。

关键 commit：`504bf56 feat(p2): add PDF ingestion CLI with pdfplumber and chunking`

### P3 SSE 对话 + 引用机制
完成 `/api/chat` SSE 流式端点、Meilisearch top-5 检索、prompt 组装、LiteLLM/DeepSeek 流式调用、消息入库、引用提取与 `messages.cited_chunk_ids` 写入。修复了 UUID 正则、用户消息写入时机、全角括号解析、few-shot UUID 记忆、引用去重等问题。

关键 commit：`9b2942f feat(p3): add /api/chat SSE endpoint with retrieval and LLM`、`8a5163b fix(p3): tighten UUID regex to require 36-char match`、`57945de fix(p3): write user message before LLM call and remove redundant os.environ`、`e81c5e0 fix(p3): fix citation extraction and strengthen prompt`、`23cabf1 fix(p3): use placeholder IDs in few-shot examples to prevent LLM memorization`、`c1f211f fix(p3): deduplicate cited_chunk_ids while preserving order`

### P4 引用查询端点
完成 `GET /api/citations/{chunk_id}`，可按 chunk_id 返回原文 chunk、页码、章节标题和文章元数据。验证了有效 UUID 200、不存在 chunk 404、非法 UUID 422。

关键 commit：`57257d6 feat(p4): add /api/citations endpoint for chunk lookup`

### P5 React 前端
完成 Vite + React + TypeScript + Tailwind 4 + shadcn/ui 单页聊天前端。实现 fetch + ReadableStream SSE 流式渲染、Markdown 渲染、chunk_id 徽章、点击徽章后 Dialog 拉取引用原文，以及暖米色 + 鼠尾草绿视觉主题。

关键 commit：`e5ab263 feat(p5): add React frontend with chat, citations and SSE streaming`、`d551407 fix(p5): add shadcn CSS variables and theme for Tailwind 4`、`b14db04 style(p5): switch to sage green and warm beige theme`、`e396fc0 style(p5): redesign citation dialog and fix badge rendering`、`edbf956 feat(p5): render assistant messages with markdown support`

## 2. 闭环验证

Day 1 核心闭环已真实跑通：用户在前端提问后，后端通过 Meilisearch 召回相关 chunks，DeepSeek/MiMo 按 prompt 生成带 `[chunk_id:xxx]` 的回答，FastAPI 通过 SSE 流式推送到前端。前端用 ReactMarkdown 渲染正文，把引用标记渲染成可点击徽章；点击徽章后 Dialog 调 `/api/citations/{chunk_id}`，展示真实原文和来源。

验证链路：用户提问 → Meili 检索 → MiMo 推理 + 引用 → SSE 流式 → 前端 Markdown 渲染 + 徽章 → 点击 → Dialog 显示原文。

浏览器验收截图已核对：
- 初始空页：NourishFlow 单页聊天布局、输入框和发送按钮可见。
- 流式中：用户消息气泡与 AI 流式回复正常显示。
- 回复完成：Markdown 加粗、列表、段落间距正常，引用徽章可见。
- 点击徽章：Dialog 弹层显示文献标题、Tier、页码、来源和原文 chunk。

## 3. Git 历史

```text
edbf956 feat(p5): render assistant messages with markdown support
e396fc0 style(p5): redesign citation dialog and fix badge rendering
b14db04 style(p5): switch to sage green and warm beige theme
d551407 fix(p5): add shadcn CSS variables and theme for Tailwind 4
e5ab263 feat(p5): add React frontend with chat, citations and SSE streaming
57257d6 feat(p4): add /api/citations endpoint for chunk lookup
c1f211f fix(p3): deduplicate cited_chunk_ids while preserving order
23cabf1 fix(p3): use placeholder IDs in few-shot examples to prevent LLM memorization
e81c5e0 fix(p3): fix citation extraction and strengthen prompt
57945de fix(p3): write user message before LLM call and remove redundant os.environ
8a5163b fix(p3): tighten UUID regex to require 36-char match
504bf56 feat(p2): add PDF ingestion CLI with pdfplumber and chunking
9b2942f feat(p3): add /api/chat SSE endpoint with retrieval and LLM
01345ac refactor(p1): replace deprecated startup event and utcnow
67be88a feat(p1): scaffold backend with PG/Meili and /api/health
fb486f7 init
edcd931 Initial commit
```

## 4. 已知问题

- Meilisearch 当前是全文 top-5，存在弱相关召回；测试中出现过相关性不足但引用范围校验仍通过的情况。
- 当前 PDF 解析使用 pdfplumber，扫描件 PDF、复杂表格和图片需要后续接 MinerU。
- 提示词 few-shot 曾导致 LLM 记忆示例 UUID；已改成占位符，并用 top-5 范围校验过滤幻觉引用。
- Dialog 原文里的换行不够优雅，根因在 P2 解析层文本质量，后续应在解析/清洗层优化。
- 无用户系统、无画像、无饮食记录、无三数字卡，这是 Day 1 MVP 明确砍掉的范围。

## 5. V1 路线图

- 接入 MinerU：复用 `parse_pdf(path) -> list[Section]` 接缝，提升扫描件、图表和复杂版式解析能力。
- 用户画像系统：从写死 mock profile 迁移到静态/动态画像。
- 三数字卡：添加糖、GL、NOVA 的日内累积和解释。
- 安全护栏：红区/橙区风险识别和就医建议流程。
- Langfuse 监控：记录检索、prompt、模型输出和引用质量。
- 检索质量优化：rerank、向量检索、混合检索和 rankingScoreThreshold。
- 引用真实性校验：对 LLM 输出引用做二次校验，降低错引风险。
- 部署生产化：严格 CORS、Meili master key 强制、环境变量校验、前后端部署配置。

## 6. 关键工程决策记录

- Day 1 没做向量检索：MVP 目标是跑通 PDF 入库到真实引用闭环，全文检索 top-5 足够验证链路；向量检索留到 V1 检索质量优化。
- Day 1 使用 pdfplumber 而不是 MinerU：本地接入快、依赖轻，能验证闭环；`parse_pdf` 函数签名保留，后续可只替换解析实现。
- prompt 全角括号 bug：LLM 输出过 `【chunk_id:xxx】`，后端最初只识别 ASCII `[]`，导致 cited_chunk_ids 为空；最终正则同时支持全角和 ASCII。
- few-shot UUID 防记忆：示例里不能放真实 UUID，否则模型会复用示例 ID；改成 `实际ID` 占位，后端再用 top-5 范围校验过滤。
- Phase 工作流和 CLAUDE.md 有效降低了偏航：每个 Phase 先对齐目标/文件/歧义，再编码、自审、验收、报告，避免了顺手优化和 PRD 外功能扩散。
