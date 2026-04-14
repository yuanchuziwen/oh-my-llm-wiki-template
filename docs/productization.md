# LLM Wiki — 产品化路线

> 从「个人项目 + 外部 Agent」到「独立产品」的四阶段演进。

---

## 一、现状分析

### 当前架构

```
用户 → 外部 Agent 平台（Claude Code / Cursor / OpenClaw）→ 读取规范 → 操作 wiki
```

LLM Wiki 本身是「数据 + 规范」，所有智能能力完全依赖宿主平台的大模型。这意味着：

- **优势**：零 LLM 成本、零基础设施、用户用自己熟悉的工具
- **局限**：不能脱离 Agent 平台独立运行、无法作为产品分发、无法控制用户体验

### 核心资产

已经积累的、可以直接复用到产品中的部分：

| 资产 | 说明 |
|---|---|
| `wiki-schema.yml` | 完整的知识库规范（页面格式、操作流程、图谱规范） |
| `graph-server.py` | 知识图谱 MCP Server（6 个查询工具） |
| 四个核心操作 | Ingest / Query / Lint / Review 的完整定义 |
| 多平台 Mapper | CLAUDE.md / AGENTS.md / .cursor/rules 的生成体系 |
| 图谱优化方案 | 语义化关系、置信度、跨域关联分析 |

### 产品化的核心转变

从「告诉 Agent 怎么做」变成「自己执行」：

```
当前：wiki-schema.yml（规范）→ Agent 按规范操作
目标：wiki-schema.yml（规范）→ 代码引擎按规范执行 → 调 LLM 完成需要智能的部分
```

---

## 二、四阶段路线

### 推荐顺序：Phase 1 → 2 → 3 → 4

每个阶段自然建立在上一个之上，前一个是后一个的基础。

```
Phase 1: CLI 核心引擎      ← 把"规范"变成"代码"
Phase 2: Agent 平台插件    ← 把引擎接入各 Agent 平台
Phase 3: 桌面应用          ← 给引擎套上 UI
Phase 4: Web SaaS          ← 多用户 + 云端
```

---

## 三、Phase 1 — CLI 工具

> 把散落在 CLAUDE.md 里的「指令」变成可执行代码。

### 3.1 用户体验

```bash
# 安装
pip install llm-wiki

# 初始化（生成项目结构 + 配置文件）
llm-wiki init

# 配置 LLM（首次使用时交互式引导）
llm-wiki config set llm.provider openai
llm-wiki config set llm.api_key sk-xxx

# 四个核心操作
llm-wiki ingest raw/articles/xxx.md
llm-wiki ingest --url "https://example.com/article"
llm-wiki query "LLM Wiki 和 RAG 有什么区别？"
llm-wiki lint
llm-wiki lint --level deep
llm-wiki review --period weekly

# 图谱工具
llm-wiki graph stats
llm-wiki graph neighbors llm-wiki
llm-wiki graph path llm-wiki rag
```

### 3.2 核心模块

```
llm_wiki/
├── cli.py                  # CLI 入口（click / typer）
├── config.py               # 配置管理（LLM provider、API Key、项目路径）
├── llm/                    # LLM 适配层
│   ├── adapter.py          # 统一接口
│   ├── openai.py           # OpenAI 实现
│   ├── anthropic.py        # Anthropic 实现
│   └── ollama.py           # 本地模型实现
├── engine/                 # 核心引擎
│   ├── ingest.py           # Ingest 引擎：解析资料 → 生成 wiki 页面 → 更新图谱
│   ├── query.py            # Query 引擎：检索 + 图谱遍历 + LLM 综合
│   ├── lint.py             # Lint 引擎：轻量规则检查 + LLM 深度检查
│   └── review.py           # Review 引擎：生成 journal 页面
├── graph/                  # 图谱引擎
│   ├── manager.py          # 图谱 CRUD（基于现有 graph-server.py 逻辑）
│   └── server.py           # MCP Server（复用 graph-server.py）
├── wiki/                   # Wiki 管理
│   ├── page.py             # 页面读写（frontmatter 解析、wiki-link 处理）
│   ├── index.py            # index.md 管理
│   └── log.py              # log.md 管理
├── parsers/                # 多模态解析
│   ├── markdown.py         # Markdown / 纯文本
│   ├── pdf.py              # PDF 提取
│   ├── image.py            # Vision 识别
│   ├── audio.py            # Whisper 转录
│   └── url.py              # Jina Reader / 直接抓取
└── schema/                 # 内置 schema
    └── wiki-schema.yml     # 打包进 CLI，init 时复制到项目
```

### 3.3 LLM Adapter 设计

```python
class LLMAdapter:
    """统一的 LLM 调用接口。所有引擎通过此接口调用大模型。"""

    def complete(self, prompt: str, system: str = "") -> str: ...
    def complete_json(self, prompt: str, schema: dict) -> dict: ...
    def vision(self, image_path: str, prompt: str) -> str: ...
    def transcribe(self, audio_path: str) -> str: ...
```

支持的 Provider：

| Provider | 模型 | 适用场景 |
|---|---|---|
| OpenAI | gpt-4o, gpt-4o-mini | 默认推荐 |
| Anthropic | claude-sonnet, claude-haiku | 长文本理解更强 |
| Ollama | llama3, qwen2 等 | 离线 / 隐私敏感场景 |
| 兼容 API | DeepSeek, 月之暗面等 | OpenAI 兼容接口 |

### 3.4 与现有规范的关系

CLI 引擎直接读取 `wiki-schema.yml` 作为配置源：

- 页面模板、frontmatter 规范 → `wiki/page.py` 读取 schema 生成
- 操作步骤 → 各 engine 按 schema 定义的 steps 执行
- 图谱规范 → `graph/manager.py` 按 schema 定义的字段写入
- 关系类型和置信度 → Ingest 时的 LLM prompt 中引用

### 3.5 商业模式

- **开源核心**：CLI 工具 MIT 开源，吸引用户
- **付费增强**（可选）：高级 Lint 规则、团队同步、优先支持
- **主要价值**：建立用户基础和口碑，为后续阶段铺路

### 3.6 技术栈

- Python 3.11+
- click 或 typer（CLI 框架）
- NetworkX（图谱）
- httpx（LLM API 调用）
- PyYAML（schema 解析）
- rich（终端美化输出）

---

## 四、Phase 2 — Agent 平台插件

> 把 CLI 引擎包装成各 Agent 平台的原生插件。

### 4.1 形态

| 平台 | 插件形态 | 说明 |
|---|---|---|
| Claude Code / Cursor | MCP Server | 把 CLI 命令暴露为 MCP tools |
| VS Code | Extension | 侧边栏 + 命令面板，底层调 CLI |
| JetBrains | Plugin | 同上 |
| Raycast / Alfred | 快捷命令 | 快速 ingest / query |

### 4.2 MCP Server 升级

当前已有 `graph-server.py`（6 个图谱查询工具）。Phase 2 扩展为完整的 wiki MCP Server：

```
现有工具（图谱查询）：
  get_neighbors, shortest_path, top_nodes, graph_stats, get_node, reload

新增工具（wiki 操作）：
  wiki_ingest    — 摄入资料（调 CLI ingest engine）
  wiki_query     — 查询知识库（调 CLI query engine）
  wiki_lint      — 健康检查（调 CLI lint engine）
  wiki_search    — 全文搜索 wiki 页面
  wiki_get_page  — 获取指定页面内容
  wiki_stats     — wiki 整体统计
```

这样 Agent 平台不再需要读 CLAUDE.md 来「理解」如何操作 wiki——直接调用 MCP 工具即可。Agent 变成了纯粹的「对话层」，wiki 操作由引擎保证正确性。

### 4.3 商业模式

- **免费**：MCP Server 免费（推广 CLI）
- **付费**：VS Code Extension Pro 版（高级功能、优先更新）
- **核心价值**：降低使用门槛，让用户在自己的工作流中无缝使用

### 4.4 技术栈

- MCP SDK（Python）
- VS Code Extension API（TypeScript）
- 底层均调用 Phase 1 的 Python CLI

---

## 五、Phase 3 — 桌面应用

> 给引擎套上图形界面，面向非技术用户。

### 5.1 用户体验

```
┌──────────────────────────────────────────────────────┐
│  LLM Wiki                                    ─ □ ×  │
├──────────┬───────────────────────────────────────────┤
│ 📁 Wiki  │  # LLM Wiki                              │
│  concepts│                                           │
│   ├ llm  │  ## 定义                                  │
│   ├ rag  │  LLM 驱动的个人知识管理系统...             │
│   └ ...  │                                           │
│  entities│  ## 来源                                   │
│   ├ karp │  - [[sources/karpathy-gist]]              │
│   └ ...  │                                           │
│  sources │                                           │
│  areas   ├───────────────────────────────────────────┤
│          │ 💬 AI 助手                                 │
│ 📊 图谱   │                                           │
│ ⚙️ 设置   │ > LLM Wiki 和 RAG 有什么区别？            │
│          │                                           │
│          │ LLM Wiki 是...而 RAG 是...                 │
│          │ 参考：[[concepts/llm-wiki]] [[concepts/rag]]│
└──────────┴───────────────────────────────────────────┘
```

### 5.2 核心功能

- **左栏**：Wiki 文件树浏览、图谱可视化
- **中间**：Markdown 渲染 + 编辑（类 Obsidian）
- **右栏**：AI 对话（Query / Ingest 交互）
- **拖拽导入**：文件拖入即 Ingest
- **图谱可视化**：交互式知识图谱（D3.js / Cytoscape.js）
- **全局搜索**：wiki 全文搜索 + 图谱语义搜索

### 5.3 与 Obsidian 的差异化

| 维度 | Obsidian | LLM Wiki 桌面版 |
|---|---|---|
| AI 能力 | 插件（受限） | 原生深度集成 |
| 知识图谱 | 仅展示链接关系 | 语义关系 + 置信度 + 跨域分析 |
| 自动化 | 手动组织 | 自动 Ingest / Lint / Review |
| 输入 | 手动编辑 | 拖拽文件 / 粘贴 URL / 对话输入 |
| 定位 | 通用笔记工具 | AI 驱动的知识管理系统 |

### 5.4 商业模式

- **免费版**：基础浏览 + 有限 AI 操作（本地模型）
- **Pro 版**：完整 AI 能力、云端模型、高级图谱分析
- **定价参考**：一次性买断 ¥198 或年订阅 ¥98/年

### 5.5 技术栈

- **Tauri**（Rust + Web 前端）— 比 Electron 更轻量
- 前端：React / Vue + Tailwind
- Markdown 渲染：markdown-it 或 unified
- 图谱可视化：D3.js / Cytoscape.js
- 底层引擎：Phase 1 CLI（作为 sidecar 进程或 WASM 编译）

---

## 六、Phase 4 — Web SaaS

> 多用户、云端、团队协作。

### 6.1 用户体验

- 浏览器访问，无需安装
- 个人空间 + 团队空间
- 实时同步，多端访问
- 团队成员共建知识库

### 6.2 架构变化

```
Phase 1-3 架构（单用户本地）：
  用户 → CLI/App → 本地文件系统 → Git 同步

Phase 4 架构（多用户云端）：
  用户 → Web 前端 → API Server → 云存储 + 数据库
                         ↓
                    LLM API + 异步任务队列
```

| 组件 | 技术选型 | 说明 |
|---|---|---|
| 前端 | React / Next.js | 复用 Phase 3 的 Web 组件 |
| API | FastAPI / Django | Python 生态，复用 CLI 引擎 |
| 数据库 | PostgreSQL | 用户、空间、权限 |
| 存储 | S3 + 本地文件 | wiki Markdown + 原始资料 |
| 图谱 | Neo4j 或 PostgreSQL + AGE | 多用户图谱需要真正的图数据库 |
| 任务队列 | Celery / Dramatiq | Ingest 异步处理 |
| 搜索 | Elasticsearch / Meilisearch | 全文搜索 |
| 缓存 | Redis | 会话、热数据 |

### 6.3 同步机制变化

| 阶段 | 同步方式 | 适用场景 |
|---|---|---|
| Phase 1-3 | Git push/pull | 个人用户、技术用户 |
| Phase 4 | 云端实时同步 | 团队、非技术用户 |
| 混合模式 | Git ↔ 云端双向同步 | 高级用户（本地编辑 + 云端协作） |

### 6.4 商业模式

| 层级 | 价格 | 包含 |
|---|---|---|
| Free | ¥0 | 1 个 wiki、100 页、本地模型 |
| Pro | ¥29/月 | 无限页面、云端模型、高级图谱 |
| Team | ¥99/月/人 | 团队空间、权限管理、共建 |
| Enterprise | 定制 | 私有部署、SSO、审计日志 |

### 6.5 数据主权

LLM Wiki 的核心价值观之一是**数据主权**——用户的知识属于用户。SaaS 化后需要保证：

- 随时导出全部数据（标准 Markdown + graph.json）
- 支持自托管（开源 self-hosted 版本）
- 明确的数据使用政策（不用用户数据训练模型）

---

## 七、阶段关系与复用

```
Phase 1（CLI 引擎）
  ├── engine/ingest.py ──────────────────┐
  ├── engine/query.py ───────────────────┤
  ├── engine/lint.py ────────────────────┤
  ├── engine/review.py ──────────────────┤
  ├── graph/manager.py ──────────────────┤
  ├── llm/adapter.py ───────────────────┤
  └── wiki/page.py ──────────────────────┤
                                         │
Phase 2（MCP Server + 插件）             │ 调用
  └── 包装 Phase 1 引擎为 MCP tools ←────┤
                                         │
Phase 3（桌面 App）                       │ 调用
  └── UI 层调用 Phase 1 引擎 ←───────────┤
                                         │
Phase 4（Web SaaS）                       │ 调用
  └── API Server 调用 Phase 1 引擎 ←─────┘
```

**Phase 1 的代码质量决定了后续所有阶段的上限。**

---

## 八、风险与考量

| 风险 | 影响 | 应对 |
|---|---|---|
| LLM API 成本 | 用户使用成本高 | 支持本地模型（Ollama）、智能缓存、轻量操作零 token |
| Obsidian 竞争 | 桌面版用户获取难 | 差异化定位：不是笔记工具，是 AI 知识管理系统 |
| 数据安全顾虑 | SaaS 用户信任 | 开源核心、支持自托管、明确数据政策 |
| 开发资源 | 个人项目精力有限 | 严格按阶段推进，Phase 1 充分验证后再做 Phase 2 |
| LLM 能力波动 | 不同模型输出质量不一 | Adapter 层统一接口 + 输出校验 + 降级策略 |

---

## 九、里程碑建议

| 里程碑 | 目标 | 预期产出 |
|---|---|---|
| Phase 1 Alpha | CLI 核心可用 | `pip install llm-wiki`，支持 ingest + query |
| Phase 1 Beta | 完整 CLI | 四个操作完整、多 LLM provider、图谱集成 |
| Phase 1 GA | 正式发布 | PyPI 发布、文档完善、社区反馈 |
| Phase 2 | MCP + VS Code 插件 | 各平台可用 |
| Phase 3 Alpha | 桌面 App 可用 | 基础浏览 + AI 对话 |
| Phase 3 GA | 桌面 App 正式版 | 完整功能、付费版本 |
| Phase 4 Beta | SaaS 内测 | 多用户、云端同步 |
| Phase 4 GA | SaaS 正式版 | 团队功能、企业版 |

---

## 十、下一步

Phase 1（CLI 核心引擎）是一切的基础。建议立即开始的工作：

1. 搭建 Python 包结构（pyproject.toml + src layout）
2. 实现 LLM Adapter（先对接 OpenAI）
3. 从 Ingest 操作开始——这是最核心、最能验证价值的功能
4. 把现有 `graph-server.py` 的逻辑迁入 `graph/manager.py`
5. 写第一个端到端测试：一篇文章进去 → wiki 页面 + 图谱节点出来
