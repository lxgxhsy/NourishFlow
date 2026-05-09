# NourishFlow MVP · 开发 PRD(Day 2 · v2)

> 基于 Day 1 完整 MVP,Day 2 目标是**打通午餐外卖决策场景的端到端闭环**。
> 路线:**P2(菜品库 + 高德 POI 真实周边商家),时间 7-9h,熔断 9h**
> 核心人设:**用户(本人)是合伙人不是甲方,会真上手测试 + 真审菜单 + 真审 prompt + 真审文档**

---

## 一、Day 2 范围

### 1.1 核心场景验收

```
用户: 现在 11:15,我中午想吃外卖,午休短,你推荐一下

系统:
  1. 识别时间 11:15 → 推断午餐场景 + 30 分钟决策窗口
  2. 知道用户位置(用户文字告知或前端授权)
  3. 调高德 POI 拿周边 500m 真实商家列表
  4. 匹配菜品库,识别"出餐快+血糖友好"的连锁品牌
  5. 检索营养文献支撑推荐理由
  6. 综合输出 1-2 个真实店家 + 具体推荐菜 + 引用文献
```

**验收 3 个核心场景 + 2 个边界场景**:
- 场景 A:11:15 急午餐 → 推快 + 轻
- 场景 B:14:30 想吃下午茶 → 低糖小食选项
- 场景 C:18:30 晚餐选择 → 均衡膳食结构
- 场景 D(边界):用户位置在小镇/郊区,周边几乎没连锁店
- 场景 E(边界):用户问"我家附近只有一家不知名小馆"

(原 22:00 宵夜场景砍掉,产品价值低)

### 1.2 做什么

| 能力 | 验收 |
|---|---|
| 菜品库(20 个连锁品牌)入库 | Meili `brands` 索引返回真实品牌 + 招牌菜营养画像 |
| 高德 POI 周边搜索 | 给定经纬度返回 500m 内真实商家列表 |
| 双索引检索(文献 + 菜品库) | 一次对话同时召回两类数据 |
| 用户上下文注入 | 时间 / 位置 / 偏好进入 prompt |
| 推荐输出格式化 | 每条推荐含真实店名 + 具体菜品 + 引用文献 |
| Harness 复盘 | 每 Phase 结束更新 `HARNESS_LEARNINGS.md`,你加批注 |

### 1.3 不做的事(Day 2 红线)

- ❌ Function Calling / Tool Use(MiMo 工具调用质量风险)
- ❌ 浏览器原生定位 navigator.geolocation(需要 https)
- ❌ 用户画像系统(画像继续写死 at_risk)
- ❌ 三数字卡 / 饮食日志
- ❌ 50 个品牌的"完美数据集"(目标 20 个,够 demo)
- ❌ MinerU(Day 1 接缝已留,Day 3 再做)
- ❌ UI 全面重做(Day 2 只动必需的部分)
- ❌ 爬虫(法律 + 技术双重风险)

---

## 二、技术栈(在 Day 1 基础上)

**沿用**:Python 3.11 + FastAPI + uv + SQLModel + PostgreSQL 16 + Meilisearch 1.10 + LiteLLM(MiMo)+ React 19 + Vite 6 + shadcn/ui

**新增**:
- `httpx>=0.27,<0.28` — 调用高德 POI API(必须用 async,和 litellm.acompletion 保持一致,**禁止用 sync requests**)
- 高德地图开发者账号 + Web 服务 API key

---

## 三、模块切分

### M0 · 高德开发者准备(异步进行,~1h)

(用户已申请,本节内容沿用 v1)

详见 v1。**熔断**:申请超过 2h 没拿到 key,Day 2 降级到"菜品库 only,不接 POI"。

---

### M1 · 菜品库设计(~30min)

**目标**:定义品牌 + 菜品的数据 schema。

**新建文件**:`backend/app/schemas/brand.py`

```python
from pydantic import BaseModel
from typing import Literal

class Dish(BaseModel):
    name: str
    estimated_calories: int
    added_sugar_level: Literal["low", "medium", "high"]
    gl_level: Literal["low", "medium", "high"]
    protein_g: int
    blood_sugar_friendly: bool
    tags: list[str]
    key_concerns: list[str] = []
    customization_tips: list[str] = []

class Brand(BaseModel):
    brand: str
    category: str
    typical_wait_minutes: int
    lunch_short_score: int
    blood_sugar_strategy: str
    best_choice_for_at_risk: str
    signature_dishes: list[Dish]
```

**Meili 索引契约**:每个 brand 作为一个文档,searchable 是 `brand + category + signature_dishes.name + tags`,filterable 是 `category + lunch_short_score`。

---

### M2 · 菜品库生成 CLI + 用户主导填写(~3h, 用户介入重)

**这一节是 Day 2 最重要的设计变化**——基于用户(你)对连锁品牌熟悉的事实,**你不再是 reviewer,你是 author**。

#### M2.1 你手写 5 个黄金样本(45-60min)

**你来写**(因为你熟):
- 肯德基(KFC)
- 麦当劳(McDonald's)
- 瑞幸咖啡(Luckin)
- 星巴克(Starbucks)
- 霸王茶姬(Chagee)

**写法**:Claude Code 提供一个空的 JSON 模板和 1 个完整示例,**你直接填空**。每个 5-8 分钟。

写完这 5 个,这 5 个 JSON 就成了 LLM 后续生成的 **few-shot 样本**——LLM 看到这 5 个真实样本,生成质量会提升 50%+。

#### M2.2 LLM 批量生成 15 个(~1h)

**LLM 生成**(因为你不熟或写着累):
- 必胜客 / 汉堡王 / 塔斯汀
- 华莱士 / 永和大王 / 真功夫 / 和府捞面
- 寿司郎 / 萨莉亚
- 紫光园 / 西贝莜面村 / 海底捞
- 杨国福麻辣烫 / 张亮麻辣烫 / 兰州拉面

**新建脚本**:`scripts/generate_brands.py`

**入口**:
```bash
uv run python scripts/generate_brands.py \
  --brand="必胜客" \
  --few-shot=data/brands/kfc.json,data/brands/luckin.json \
  --output=data/brands/pizzahut.json
```

**LLM prompt** 必须包含:
1. Brand schema 定义
2. 你写的 5 个黄金样本作为 few-shot
3. 强约束:"严格按 schema 输出,不输出解释"
4. 防幻觉:"如果不知道某品牌的真实菜单,宁可不输出也不要编造菜品名"

**Pydantic 校验**:schema 不通过的重试 2 次,仍然失败就**手工降级**(转你来写)。

#### M2.3 你抽审 30%(~30min)

**你的任务**:
- LLM 生成的 15 个里,**抽 5 个**(随机选)
- 每个**对照品牌官网/小程序**真实查 1-2 个菜品
- 比如 LLM 写"必胜客有'香辣鸡腿堡'",你查官网发现没有,**这 1 个 JSON 整批重写**
- 抽审通过率 < 70% 时,**剩余的全部你重写**

**判定标准**(写进 PRD,Claude Code 知道):
- ✅ **通过**:招牌菜真实存在,营养画像方向对
- ⚠️ **小错**:菜品名小变体(例如"原味鸡" vs "原味鸡块"),营养画像差不多 → 修改一下
- ❌ **大错**:编造菜品名 / 营养完全错(把高 GL 写成低 GL) → 这个 JSON 整体作废重写

---

### M3 · 菜品库入库 + Meili 索引(~30min)

(沿用 v1)

---

### M4 · 高德 POI 服务封装(~1h)

(沿用 v1)

**重申**:必须用 `httpx.AsyncClient`,禁止 `requests` 同步库。

---

### M5 · 用户上下文注入 + Prompt 改造(~1h, 用户介入)

**关键**:**任何 system prompt 改动必须 PR-style diff 审过才能 commit**。

#### M5.1 流程

1. Claude Code 写出新 prompt
2. **不直接改 chat.py**,先在 LEARNINGS 里写出 diff(老 prompt → 新 prompt)
3. **你审 diff**,可以提修改意见
4. 你说"OK"才能改 chat.py 并 commit

#### M5.2 接口扩展

```typescript
// 前端 POST /api/chat
{
  conversation_id: string | null,
  message: string,
  user_context: {
    current_time: string,        // ISO 8601
    location_text?: string,       // "北京市朝阳区国贸三期"
    location_coords?: string      // 可选
  }
}
```

#### M5.3 Prompt 结构设计(v2 加强,基于业界最佳实践)

Day 2 system prompt 必须按以下 3 个技术原则设计:

**原则 1:用 XML-like tag 隔离不同数据源**

理由:LLM 对 XML 结构化标签的解析比 markdown 标题更稳定(Anthropic 官方推荐做法)。
不同数据源不会混淆,LLM 也更容易学会"先看用户上下文,再看检索数据,最后输出"的处理顺序。

**原则 2:输出格式用"好坏对照"而不是只给规则**

理由:LLM 看 "✅ 好示例 + ❌ 坏示例" 的学习效率,远高于看一条条 "输出必须包含 X、Y、Z" 的规则。

**原则 3:工具结果带"可信度等级"**

理由:LLM 不知道哪些数据是权威、哪些是辅助、哪些可能过期。显式告诉它,可以防止"AI 编造不存在的店家或菜品"——这是 Day 2 红线 3 的核心防御。

#### M5.4 Day 2 完整 system prompt 结构

```
<role>
你是 NourishFlow 的营养陪伴 AI。
(沿用 Day 1 立场:食物结构 > 热量,血糖管理优先,不教训不羞辱)

用户画像(MVP 写死): at_risk,目标预防糖尿病和肥胖
</role>

<user_context>
当前时间: {current_time}
位置: {location_text or "未提供"}
推断场景: {auto_detect_scene}
   ↑ 后端预处理,不让 LLM 推理
   场景值: 早餐决策 / 午餐决策(可能赶时间) / 下午茶 / 晚餐决策 / 通用
</user_context>

<retrieved_literature>
[chunk_id:xxx] (来源: 文献名, tier N) 内容...
[chunk_id:yyy] (来源: 文献名, tier N) 内容...
   ↑ Day 1 的文献检索结果,top-5
</retrieved_literature>

<nearby_places>
1. 肯德基(国贸店) - 距离 200m, 评分 4.5
2. 瑞幸咖啡(国贸三期店) - 距离 350m
3. ...
   ↑ 高德 POI 真实数据,可能为空
   如果为空: "(本次未获取到真实周边数据)"
</nearby_places>

<matched_brands>
[brand:kfc] 肯德基: { 营养画像 JSON }
[brand:luckin] 瑞幸: { 营养画像 JSON }
   ↑ 菜品库匹配,基于 query 检索 brands 索引
</matched_brands>

<data_trust_level>
- <retrieved_literature>: 营养学权威,可放心引用,断言必须配 [chunk_id:xxx]
- <nearby_places>: 高德地图真实数据,但可能过期(店家可能搬/关),不要保证
- <matched_brands>: 你的菜品库,真实但只覆盖 20 个连锁品牌
- 如果用户问的店不在以上数据中,诚实说"我没有这家店的数据,可以告诉我招牌菜吗?",**不要编造**
</data_trust_level>

<output_format>
✅ 好示例:
推荐 1: 肯德基(国贸店)- 三对鸡翅 + 玉米沙拉 [brand:kfc]
  理由: 蛋白质足,玉米沙拉提供膳食纤维,血糖反应平缓 [chunk_id:xxx]
  点单技巧: 选原味鸡而非辣翅,可乐换零度可乐
推荐 2: 瑞幸(国贸三期店)- 美式 + 三明治 [brand:luckin]
  ...
避开的: 
- 香辣鸡腿堡套餐(精制面包 + 高 GL,午后困倦) [chunk_id:yyy]

❌ 坏示例:
推荐: 你可以选一些健康的食物,比如沙拉和瘦肉
(原因:太空泛,没引用,没具体店,没点单技巧)

❌ 也是坏示例:
推荐: 楼下有家叫"陈记小炒"的店,他们的青椒肉丝很不错
(原因:陈记小炒不在 <nearby_places> 也不在 <matched_brands>,这是编造)
</output_format>

<safety>
- 用户每个选择都尊重,不劝退
- 涉及血糖/胰岛素/添加糖的断言必须引用 [chunk_id:xxx]
- 引用真实店家用 [brand:xxx],brand_id 必须来自 <matched_brands>
- 如果用户描述疑似糖尿病典型症状(多饮多食多尿、体重骤降),建议就医
</safety>
```

#### M5.5 Prompt 改动审查流程(强制)

**任何 chat.py 的 system prompt 改动**:

1. Claude Code 在聊天里贴出 diff(`old prompt` → `new prompt`),**不直接改文件**
2. 你审 diff,可以提修改意见或拍板
3. 你说"OK"后,Claude Code 才能改 chat.py 并 commit
4. commit message 格式:`refine(p6-prompt): <一行说明改了什么>`

**这一条是 CLAUDE.md 3.3 的强化版,Day 2 必须严格执行**。

---

### M6 · 双索引检索 + 数据汇集(~1h)

(沿用 v1)

---

### M7 · 前端适配(~1.5h)

(沿用 v1)

---

### M8 · 端到端测试 + Harness 复盘(~1h, 用户介入)

#### M8.1 用户视角真实测试

**你的任务**:不只是跑 curl,**真在浏览器里发消息,以一个上班族真实期待去判断**。

**验收标准**(主观,但要明确):
- **满意**:真的会照这个 AI 的建议去点餐
- **一般**:建议合理但不让我心动,我宁可自己看外卖 App
- **不满意**:建议明显跑题/不实用/AI 像在说套话

**任一场景"不满意",当场记录到 LEARNINGS,Day 2 不收工**。

#### M8.2 边界场景必测

- 场景 D:你输入"内蒙古通辽科尔沁区",看 AI 怎么处理(高德 POI 大概率返回少量结果或都是非连锁)
- 场景 E:你直接说"我家附近只有一家不知名小馆,叫做老李川菜",看 AI 怎么处理(应该回到品类建议,不强求引用品牌库)

#### M8.3 Harness 复盘

每个 Phase 结束写一段 LEARNINGS。详见第七节。

---

## 四、Phase 顺序与时间盒(v2 调整)

| Phase | 任务 | 时间盒 | 熔断 | 用户介入 |
|---|---|---|---|---|
| **P0** | 高德 key 申请(异步) | 0(等待) | 2h | ✅ 你申请 |
| **P1** | M1 schema + M2 CLI 骨架 | 1h | 1.5h | |
| **P2** | **你手写 5 个黄金样本** | 1h | 1.5h | ✅✅ 你主写 |
| **P3** | LLM 批量生成 15 个 + 你抽审 30% | 2.5h | 3h | ✅ 你抽审 |
| **P4** | M3 入库 + Meili `brands` 索引 | 0.5h | 1h | |
| **P5** | M4 高德服务 | 1h | 1.5h | |
| **P6** | M5 prompt 改造 + 双检索 | 1.5h | 2h | ✅ 你审 prompt diff |
| **P7** | M7 前端适配 | 1.5h | 2h | |
| **P8** | M8 端到端 + Harness 复盘 | 1h | 1h | ✅✅ 你做用户测试 + 加批注 |

**合计**:8-10h(比 v1 多 1h,因为加了你介入时间),**硬熔断 9h**(超过当天收工)。

**关键并行**:P0 高德申请 ↔ P1+P2 完全并行,P5 才需要 key。

---

## 五、API 契约清单

(沿用 v1)

---

## 六、目录结构(增量)

(沿用 v1,补充)

```
backend/data/brands/                  ← Day 2 新增,git commit(品牌资产)
├── kfc.json                          ← P2 你手写
├── mcdonalds.json                    ← P2 你手写
├── luckin.json                       ← P2 你手写
├── starbucks.json                    ← P2 你手写
├── chagee.json                       ← P2 你手写
├── pizzahut.json                     ← P3 LLM 生成 + 你审
├── ...(共 20 个)
```

**`data/brands/*.json` 是否 commit**:**是**,品牌名是公开常识,营养画像不敏感,提交保证可复现。

---

## 七、用户(你)的强制介入点(v2 新增章节)

**这一节是 v2 与 v1 的核心差异**,基于"用户是合伙人不是甲方"的人设。

### 7.1 P2 黄金样本关 — 你手写 5 个

详见 M2.1。**你不写完这 5 个,P3 不能启动**。

### 7.2 P3 抽审关 — 你抽 5 个对照官网真审

详见 M2.3。**抽审通过率 < 70%,P3 重新做或转手工**。

### 7.3 Prompt 改动关 — PR-style diff 审

详见 M5.1。**任何 chat.py 的 system prompt 改动,Claude Code 必须先在聊天里贴 diff,你说 OK 才能改文件**。

### 7.4 LEARNINGS 加批注关 — 你不只是看,要写一行

每个 Phase 的 LEARNINGS,**Claude Code 写完后,你必须加一行批注**:
- "同意,后续按此沉淀进 CLAUDE.md"
- "不同意,我的看法是 X"
- "需讨论:Y 这点 Claude Code 视角和我的视角差异"

**没有你批注的 LEARNINGS 段,不能进 CLAUDE.md v0.2**。

### 7.5 CLAUDE.md 升级关 — Claude Code 出 patch,你亲自合并

**Claude Code 不能直接修改 CLAUDE.md**。规则升级流程:

1. Day 2 末尾,Claude Code 把所有"建议沉淀进 CLAUDE.md"的条目整理成 patch
2. patch 以 markdown diff 形式贴给你
3. 你逐条审,**手动复制粘贴**进 CLAUDE.md(不让 Claude Code 自己改)
4. 提交 commit:`chore(harness): upgrade CLAUDE.md to v0.2 (manually applied)`

**理由**:Harness 规范污染一条会污染未来所有项目,这是项目的"宪法",必须人工签名。

### 7.6 用户视角测试关 — 真在浏览器发消息按用户感受判断

详见 M8.1。**4 个场景全部"满意"才算 Day 2 通过**。

### 7.7 负面场景必测关 — 小镇 / 不知名小馆

详见 M8.2。

---

## 八、Harness 升级目标(用户视角加强版)

每个 Phase 结束后,**你**(不是 Claude Code)主导这个动作:

```
1. Claude Code 完成 Phase B/C/D
2. Claude Code 起草 LEARNINGS 段落(模板见下)
3. 你审,加批注(7.4)
4. Phase 才算闭合,进入下一 Phase
```

### LEARNINGS 模板(v2,加了"用户批注"字段)

```markdown
## Day 2 P{X} - {任务名}

### 实际耗时 vs 预算
预算 X.Xh,实际 Y.Yh,偏差原因:...

### Claude Code 撞到的纪律盲区
1. ...

### Claude Code 即时打的临时补丁
- ...

### Claude Code 建议沉淀进 CLAUDE.md v0.2 的条目
- 新条目 X.Y:...

### 用户批注(必填,不能跳过)
- 同意 / 不同意 / 需讨论:...
```

### 强制反思 prompt(防止 Claude Code 写"一切顺利"水报告)

LEARNINGS 模板里加一条:

> **如果重做这个 Phase,你会做哪些改进?(必须列至少 1 条,不允许"一切顺利")**

---

## 九、Day 2 不可妥协的红线(v2 新增)

1. 不引入 Function Calling
2. 不爬商家数据
3. 不让 LLM 编造真实店名/菜品(只用高德返回 + 菜品库)
4. POI 失败必须有降级
5. 每 Phase 必写 LEARNINGS
6. **(v2 新增)** 用户没批注的 LEARNINGS 不进 CLAUDE.md
7. **(v2 新增)** 任何 prompt 改动必须 PR-style 审过
8. **(v2 新增)** 用户视角测试 4 场景全"满意"才收工

---

## 十、本地启动手册(Day 2 版)

(沿用 v1)

---

## 十一、Day 2 → Day 3 移交(v2 新增)

Day 2 结束时,你和 Claude Code 共同产出:

1. ✅ 20 个品牌的 JSON 资产(commit 在 `backend/data/brands/`)
2. ✅ Meili 第二个索引 `brands`
3. ✅ 高德 POI 集成(`backend/app/services/amap.py`)
4. ✅ 双索引检索的 chat.py
5. ✅ 用户上下文注入的前端
6. ✅ `docs/HARNESS_LEARNINGS.md`(8 个 Phase 的 LEARNINGS + 你的批注)
7. ✅ `CLAUDE.md` v0.2(你亲手合并的 patch)
8. ✅ `docs/MVP_DAY2_REPORT.md`(参考 Day 1 格式)

---

*Day 2 PRD v2 · 2026-05-09 · 用户介入版*
