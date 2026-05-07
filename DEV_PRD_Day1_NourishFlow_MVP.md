# NourishFlow MVP · 开发 PRD(Day 1)

> 基于产品 PRD v1.1,**今天的目标是跑通核心闭环:PDF 入库 → 能聊 → 引用真实**。
> 其他模块(画像、饮食记录、三数字卡、安全护栏等)留到后续迭代。

---

## 一、今天的范围

### 1.1 做什么

| 能力 | 验收 |
|---|---|
| PDF 通过 CLI 入库 | `python -m app.ingest xx.pdf --title=... --tier=1` 跑通,PG + Meilisearch 都有数据 |
| 全文检索召回 chunks | 给定 query,Meilisearch 返回 top-5 |
| 主对话能引用 | 前端发消息,流式返回,带 `[chunk_id:xxx]` 徽章 |
| 引用可点查看 | 点徽章弹层,显示原文 chunk + 来源 |

### 1.2 不做什么(产品 PRD 有,今天砍)

- ❌ 用户画像(静态/动态)—— 写死一个 mock profile 注入 prompt
- ❌ 饮食被动记录 / meal_logs / 三数字卡
- ❌ 安全护栏(红区/橙区关键词扫描)—— prompt 里写一句兜底
- ❌ 代谢状态加权重排 —— top-5 直接给
- ❌ 异步后处理 —— 全部同步
- ❌ Langfuse 监控
- ❌ MinerU / 多模态图表解析 —— **接口预留**
- ❌ 画像设置页
- ❌ LLM 引用真实性校验
- ❌ 用户系统、登录态

---

## 二、技术栈(锁定)

| 层 | 选型 |
|---|---|
| 后端 | Python 3.11 + FastAPI |
| 包管理 | uv |
| ORM | SQLModel |
| 主存储 | PostgreSQL 16 |
| 搜索索引 | Meilisearch 1.10 |
| LLM SDK | LiteLLM |
| LLM 主力 | DeepSeek V4 Pro(`deepseek/deepseek-chat`) |
| PDF 解析 | pdfplumber(MinerU 留位) |
| 前端 | React 19 + Vite 6 + TypeScript |
| UI | shadcn/ui + Tailwind 4 |
| 部署 | Docker Compose 起 PG + Meilisearch,后端本地 uv run |

---

## 三、模块切分

### M1 · 数据层

**docker-compose** 只起两个服务:

- `postgres:16` —— 端口 5432,db 名 `nourishflow`
- `meilisearch:v1.10` —— 端口 7700

后端 FastAPI **不进 compose**,本地 `uv run uvicorn` 启,改了自动热加载,迭代快。

**建表**(启动时 `SQLModel.metadata.create_all`,不用 alembic):

| 表名 | 字段(只列今天用的) |
|---|---|
| `articles` | id, title, source_org, pub_year, tier, url, tags(JSONB), uploaded_at |
| `article_chunks` | id, article_id, chunk_index, content, section_title, page_number, **chunk_type**(留位:text/table/figure), created_at |
| `conversations` | id, created_at |
| `messages` | id, conversation_id, role, content, cited_chunk_ids(JSONB), llm_model, created_at |

**砍掉的表**(产品 PRD 有,今天不建):`users`、`user_profile_static/dynamic`、`food_items`、`meal_logs`、`daily_glucose_snapshot`、`feedback`、`knowledge_sources_watch`。

---

### M2 · PDF 入库 CLI

**入口**:

```bash
python -m app.ingest <pdf_path> \
  --title="ADA Standards of Care 2024" \
  --source-org="ADA" \
  --pub-year=2024 \
  --tier=1
```

**流程**:

```
PDF
 │
 ├─→ parse_pdf(path) → list[Section]      ← 抽象接口,今天 pdfplumber
 │     Section { text, page_number, section_title }
 │
 ├─→ 写入 articles 表(元数据来自 CLI 参数)
 │
 ├─→ 分块: 800 字 + 100 overlap            ← 固定窗口,不做 semantic
 │     合并所有 Section 的 text 后整体切
 │     每块记录 chunk_index / page_number
 │
 ├─→ 写入 article_chunks 表
 │
 └─→ 同步索引到 Meilisearch
       index: article_chunks
       searchable: content, section_title
       filterable: article_id, tier, chunk_type
```

**关键设计:`parse_pdf` 是隔离层**

```
app/services/pdf_parser.py
  └─ parse_pdf(path: str) -> list[Section]   ← 对外契约,签名不变
       └─ 内部今天用 pdfplumber 实现
       └─ 明天换 MinerU 只改这个文件
```

下游 chunker 不知道 PDF 是怎么解析的。这是**给 MinerU 预留的唯一接缝**。

**不做**:

- LLM 抽元数据(用户手动 CLI 传)
- semantic chunking
- 表格/图片特殊处理

---

### M3 · 检索 + 主对话(SSE)

**端点**:`POST /api/chat`(SSE 流式)

**入参**:

```json
{
  "conversation_id": "uuid 或 null(null 时新建)",
  "message": "今天想喝奶茶"
}
```

**流程**(全同步):

```
1. 拿到/新建 conversation
2. 加载本会话最近 10 轮 messages → 上下文
3. Meilisearch 全文检索 query → top-5 chunks
4. 组装 system prompt(见下)
5. LiteLLM 流式调用 DeepSeek
6. SSE 边推边拼,完成后写 messages 表
   - 解析 LLM 输出里的 [chunk_id:xxx] → 存到 cited_chunk_ids
```

**system prompt(简化版,基于产品 PRD 6.4.4)**:

```
你是 NourishFlow 的营养陪伴 AI。

# 核心使命
帮用户预防肥胖和 2 型糖尿病,通过血糖管理和食物质量优化。

# 立场
- 长期肥胖/糖尿病的核心驱动是食物结构,不是热量
- 预防层面:血糖管理 > 热量计数
- 不数卡路里,只看添加糖、血糖负荷(GL)、加工等级(NOVA)

# 用户画像(MVP 写死)
代谢状态: at_risk
目标: 预防糖尿病和肥胖

# 检索到的相关知识
{retrieved_chunks_with_ids}
  每条格式: [chunk_id:xxx] (来源: 文献名, tier N) 内容...

# 回应原则
- 用户每个选择都尊重,不劝退
- 涉及血糖/胰岛素/添加糖的断言必须引用 [chunk_id:xxx]
- 不教训,不羞辱,不用"应该""必须"

# 兜底
- 如果用户描述疑似糖尿病典型症状(多饮多食多尿、体重骤降),建议就医
```

**砍掉**(产品 PRD 有):

- 加载画像(静态/动态)
- 加载最近 3 天饮食 + 今日血糖累积
- 代谢状态加权重排
- 异步后处理(画像提取、饮食提取、引用校验)

---

### M4 · 引用查看

**端点**:`GET /api/citations/{chunk_id}`

**返回**:

```json
{
  "chunk_id": "uuid",
  "content": "原文 chunk 全文",
  "section_title": "...",
  "page_number": 12,
  "article": {
    "title": "ADA Standards of Care 2024",
    "source_org": "ADA",
    "pub_year": 2024,
    "tier": 1
  }
}
```

不做引用真实性校验。LLM 偶尔幻觉就先记着,后续迭代加。

---

### M5 · 极简前端

**单页**(只有聊天页,**没有画像设置页/没有上传页**):

```
┌──────────────────────────────────┐
│  NourishFlow                     │
├──────────────────────────────────┤
│                                  │
│  [对话区,流式渲染]              │
│   - 用户气泡 + AI 气泡           │
│   - AI 气泡里 [chunk_id:xxx]     │
│     渲染成可点击的小徽章         │
│                                  │
├──────────────────────────────────┤
│  [输入框]              [发送]    │
└──────────────────────────────────┘
```

**徽章交互**:点击 → 调 `/api/citations/{chunk_id}` → shadcn Dialog 弹层显示原文。

**不做**:

- 三数字卡(添加糖 / GL / NOVA 累积)
- 画像设置页
- 会话历史浏览
- 新对话切换(单会话先跑通)

---

## 四、目录结构

```
nourishflow/
├── docker-compose.yml          # 只起 PG + Meilisearch
├── backend/
│   ├── pyproject.toml          # uv 管理
│   ├── .env.example
│   └── app/
│       ├── main.py             # FastAPI 入口,启动时建表 + Meili 索引
│       ├── core/
│       │   ├── config.py       # pydantic-settings
│       │   └── db.py           # engine + session
│       ├── models/
│       │   └── tables.py       # 4 张表
│       ├── services/
│       │   ├── pdf_parser.py   # ⭐ MinerU 接缝在这里
│       │   ├── chunker.py      # 800+100 固定窗口
│       │   ├── search.py       # Meilisearch 客户端封装
│       │   └── chat.py         # 检索 + prompt 组装 + LLM 调用
│       ├── api/
│       │   ├── chat.py         # POST /api/chat (SSE)
│       │   └── citations.py    # GET /api/citations/{id}
│       └── ingest.py           # CLI 入口,typer
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx             # 单页聊天
        ├── components/
        │   ├── ChatView.tsx    # 对话区 + SSE 解析
        │   ├── MessageBubble.tsx  # 渲染徽章
        │   └── CitationDialog.tsx # 弹层
        └── lib/api.ts          # fetch 封装
```

---

## 五、API 契约清单

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/chat` | SSE 流式对话 |
| GET | `/api/citations/{chunk_id}` | 引用详情 |

**今天不做**(产品 PRD 7.2 列了但今天砍):

- `/api/profile` —— 没画像
- `/api/conversations` —— 不做历史浏览
- `/api/glucose/today` —— 不做血糖累积
- `/api/upload` —— CLI 替代

---

## 六、开发顺序与时间盒

| Phase | 任务 | 时间盒 | 验收 |
|---|---|---|---|
| P1 骨架 | docker-compose 起服务 + FastAPI 项目骨架 + 建 4 张表 | 1h | `/api/health` 返 200 |
| P2 入库 | `pdf_parser` + chunker + ingest CLI + Meili 索引 | 1.5h | 跑通 1 篇 PDF,Meili 能搜到 |
| P3 主对话 | `/api/chat` SSE + LiteLLM + prompt 组装 | 2h | curl 能流式返回带 chunk_id 的回答 |
| P4 引用 | `/api/citations/{id}` | 0.5h | curl 拿到原文 |
| P5 前端 | Vite + React 单页 + SSE 解析 + 徽章弹层 | 1.5h | 浏览器能聊能点徽章 |
| **合计** | | **6.5h** | |

留 1.5h buffer 给踩坑(Meili 中文配置、SSE 跨域、LiteLLM 鉴权这几个最容易卡)。

---

## 七、明天起的延展点(今天先留好接缝)

| 接缝 | 今天做的事 | 明天能干的事 |
|---|---|---|
| `parse_pdf()` 函数 | pdfplumber 实现 | 换 MinerU 只改文件内部 |
| `chunk_type` 字段 | 全部写 `text` | 接入 figure / table 类型 |
| 检索的 `rerank()` 函数 | 不存在,直接 top-5 | 加代谢状态加权 |
| `Conversation` 表 | 已建 | 加 `user_id` 字段时不破表 |
| LLM 模型字符串 | 写在 config.py | 切 Claude 兜底改一行 |

---

## 八、本地启动手册(给你自己看的)

### 一次性准备

```bash
# 1. 起 PG + Meilisearch
docker compose up -d

# 2. 后端依赖
cd backend
uv sync

# 3. 配置环境变量
cp .env.example .env
# 填入 DEEPSEEK_API_KEY

# 4. 启动后端(自动建表 + 创建 Meili 索引)
uv run uvicorn app.main:app --reload --port 8000

# 5. 前端
cd ../frontend
pnpm install
pnpm dev
```

### 入库一篇 PDF

```bash
cd backend
uv run python -m app.ingest /path/to/ada_2024.pdf \
  --title="ADA Standards of Care 2024" \
  --source-org="ADA" \
  --pub-year=2024 \
  --tier=1
```

### 验证

- 浏览器开 `http://localhost:5173` —— 看到聊天页
- 发一条 "今天想喝奶茶,但我担心血糖" —— 流式返回,含徽章
- 点徽章 —— 弹层显示原文

---

*开发 PRD Day 1 完。*
