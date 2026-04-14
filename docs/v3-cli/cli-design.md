# LLM Wiki CLI — 详细设计文档

> 把 wiki-schema.yml 中的规范变成可执行代码，对外暴露统一的命令接口。

---

## 一、设计目标

### 1.1 核心命题

当前 LLM Wiki 的智能完全依赖外部 Agent 平台（Claude Code / Cursor），操作质量取决于 Agent 对自然语言指令（CLAUDE.md）的理解——不可控、不可复现、不可测试。

CLI 化的目标是将操作流程固化为**确定性代码**，只在真正需要智能判断的环节调用 LLM：

```
当前：Agent 自由发挥整个 Ingest 流程（10 步全靠 LLM 理解 CLAUDE.md）
CLI： 代码控制流程骨架（读文件、写文件、更新索引、更新图谱）→ 3-4 个环节调 LLM（理解内容、抽取概念、生成摘要、推断关系）
```

### 1.2 设计原则

| 原则 | 说明 |
|---|---|
| **Schema 驱动** | CLI 读取 wiki-schema.yml 作为配置源，不硬编码规范 |
| **LLM 最小化** | 确定性操作（文件读写、索引更新、去重）用代码完成，只在语义理解环节调 LLM |
| **Provider 无关** | 统一 LLM 接口，支持 OpenAI / Anthropic / Ollama / 兼容 API |
| **渐进式复用** | 代码组织为库（library），CLI 是第一个壳，后续 MCP / App / API 是其他壳 |
| **向后兼容** | CLI 产出的 wiki 结构和现有外挂模式完全一致，两种模式可共存 |

---

## 二、用户体验设计

### 2.1 安装

```bash
pip install llm-wiki
```

或开发模式：

```bash
git clone https://github.com/yuanchuziwen/llm-wiki.git
cd llm-wiki
pip install -e ".[dev]"
```

### 2.2 初始化

```bash
# 在空目录初始化一个新的 wiki 项目
llm-wiki init

# 在已有 wiki 目录中初始化（检测并保留现有内容）
cd ~/llm-wiki
llm-wiki init --existing
```

`init` 执行：
1. 创建目录结构（raw/、wiki/、graph/、schema/）
2. 生成 wiki-schema.yml（内置版本）
3. 生成 wiki/index.md 和 wiki/log.md（空模板）
4. 生成 .gitignore
5. 交互式引导配置 LLM provider 和 API Key → 写入 `.local/config.toml`

### 2.3 配置

```bash
# 交互式配置（首次使用时自动触发）
llm-wiki config setup

# 单项设置
llm-wiki config set llm.provider openai
llm-wiki config set llm.api_key sk-xxx
llm-wiki config set llm.model gpt-4o

# 查看当前配置（API Key 脱敏显示）
llm-wiki config show

# 验证配置（发一个测试请求）
llm-wiki config check
```

配置文件位置：`{project}/.local/config.toml`（已在 .gitignore 中，不同步）

```toml
[llm]
provider = "openai"          # openai | anthropic | ollama | compatible
api_key = "sk-xxx"           # 仅 openai / anthropic / compatible 需要
model = "gpt-4o"             # 默认模型
base_url = ""                # 仅 compatible 模式需要（如 DeepSeek）

[llm.models]
# 不同操作可以用不同模型（省钱）
ingest = "gpt-4o"            # Ingest 需要强理解能力
query = "gpt-4o"             # Query 需要综合推理
lint_light = ""              # 轻量 Lint 不调 LLM
lint_deep = "gpt-4o-mini"    # 深度 Lint 用便宜模型够了
review = "gpt-4o-mini"       # Review 用便宜模型

[wiki]
language = "zh"              # 输出语言：zh | en | auto
```

### 2.4 四个核心命令

```bash
# ─── Ingest（摄入）───────────────────────────────────────
llm-wiki ingest raw/articles/karpathy-llm-wiki.md          # 本地文件
llm-wiki ingest raw/papers/*.pdf                            # 批量（glob）
llm-wiki ingest --url "https://example.com/article"         # URL（自动 Jina Reader）
llm-wiki ingest --text "粘贴的文本内容..."                   # 直接文本
llm-wiki ingest --dry-run raw/articles/xxx.md               # 预览模式（不写文件，只显示计划）

# ─── Query（查询）────────────────────────────────────────
llm-wiki query "LLM Wiki 和 RAG 有什么区别？"
llm-wiki query "总结一下最近摄入的所有 AI 相关资料"
llm-wiki query --save "xxx"                                  # 强制保存到 outputs/
llm-wiki query --no-save "xxx"                               # 不保存

# ─── Lint（健康检查）─────────────────────────────────────
llm-wiki lint                                                # 默认：轻量检查
llm-wiki lint --level light                                  # 轻量：坏链、孤立页、索引一致性
llm-wiki lint --level deep                                   # 深度：矛盾、过时、stub 补全
llm-wiki lint --level growth                                 # 生长：跨域关联、知识缺口
llm-wiki lint --fix                                          # 自动修复可修复的问题

# ─── Review（回顾）───────────────────────────────────────
llm-wiki review                                              # 默认：根据距上次 review 时间自动判断
llm-wiki review --period weekly                              # 周报
llm-wiki review --period monthly                             # 月报
```

### 2.5 图谱命令

```bash
llm-wiki graph stats                                         # 图谱统计
llm-wiki graph neighbors llm-wiki                            # 查看关联节点
llm-wiki graph neighbors llm-wiki --depth 2                  # 2 跳邻居
llm-wiki graph neighbors llm-wiki --min-confidence EXTRACTED # 置信度过滤
llm-wiki graph path llm-wiki rag                             # 最短路径
llm-wiki graph top                                           # 核心节点 Top 10
llm-wiki graph top --limit 20                                # Top 20
llm-wiki graph node llm-wiki                                 # 节点详情
```

### 2.6 辅助命令

```bash
llm-wiki status                                              # wiki 整体状态
llm-wiki search "关键词"                                      # 全文搜索 wiki 页面
llm-wiki sync                                                # git pull + push
llm-wiki mcp serve                                           # 启动 MCP Server（供 Agent 平台调用）
```

---

## 三、模块架构

### 3.1 目录结构

```
src/llm_wiki/
├── __init__.py
├── __main__.py              # python -m llm_wiki 入口
├── cli/                     # CLI 层（命令定义，尽量薄）
│   ├── __init__.py
│   ├── main.py              # 顶层命令组
│   ├── ingest.py            # llm-wiki ingest
│   ├── query.py             # llm-wiki query
│   ├── lint.py              # llm-wiki lint
│   ├── review.py            # llm-wiki review
│   ├── graph.py             # llm-wiki graph *
│   └── config.py            # llm-wiki config *
│
├── engine/                  # 核心引擎（所有业务逻辑在这里）
│   ├── __init__.py
│   ├── ingest.py            # Ingest 引擎
│   ├── query.py             # Query 引擎
│   ├── lint.py              # Lint 引擎
│   └── review.py            # Review 引擎
│
├── llm/                     # LLM 适配层
│   ├── __init__.py
│   ├── base.py              # 抽象基类
│   ├── openai.py            # OpenAI 实现
│   ├── anthropic.py         # Anthropic 实现
│   ├── ollama.py            # Ollama 实现
│   └── compatible.py        # OpenAI 兼容 API（DeepSeek 等）
│
├── graph/                   # 图谱管理
│   ├── __init__.py
│   ├── manager.py           # 图谱 CRUD（NetworkX）
│   ├── report.py            # GRAPH_REPORT.md 生成
│   └── server.py            # MCP Server（复用现有 graph-server.py）
│
├── wiki/                    # Wiki 页面管理
│   ├── __init__.py
│   ├── page.py              # 页面模型（frontmatter 解析、序列化）
│   ├── index.py             # index.md 管理
│   ├── log.py               # log.md 管理
│   └── search.py            # wiki 全文搜索
│
├── parsers/                 # 输入解析器
│   ├── __init__.py
│   ├── markdown.py          # Markdown / 纯文本
│   ├── pdf.py               # PDF 提取
│   ├── image.py             # Vision 识别
│   ├── audio.py             # Whisper 转录
│   └── url.py               # URL → Markdown（Jina Reader）
│
├── schema/                  # Schema 管理
│   ├── __init__.py
│   ├── loader.py            # 加载和解析 wiki-schema.yml
│   └── wiki-schema.yml      # 内置 schema（打包进 CLI）
│
├── prompts/                 # LLM Prompt 模板
│   ├── __init__.py
│   ├── ingest.py            # Ingest 相关 prompt
│   ├── query.py             # Query 相关 prompt
│   ├── lint.py              # Lint 相关 prompt
│   └── review.py            # Review 相关 prompt
│
├── config.py                # 配置管理（读写 .local/config.toml）
├── project.py               # 项目上下文（路径解析、目录发现）
└── sync.py                  # Git 同步
```

### 3.2 层次关系

```
┌─────────────────────────────────────────────────────┐
│  CLI 层（cli/）                                      │
│  职责：解析命令行参数，调用 engine，格式化输出          │
│  未来替代：MCP Server / REST API / GUI 事件处理       │
└──────────────────────┬──────────────────────────────┘
                       │ 调用
┌──────────────────────▼──────────────────────────────┐
│  Engine 层（engine/）                                │
│  职责：编排操作流程，协调各模块                        │
│  这是核心——所有「壳」最终都调用这一层                  │
└──┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│ wiki/│ │graph/│ │ llm/ │ │ parsers/ │
│页面管理│ │图谱管理│ │LLM调用│ │ 输入解析  │
└──────┘ └──────┘ └──────┘ └──────────┘
```

关键设计：**CLI 层尽量薄**。cli/ingest.py 只做参数解析和输出格式化，真正的逻辑在 engine/ingest.py。这样 MCP Server 调 engine.ingest() 和 CLI 调 engine.ingest() 走的是完全相同的代码路径。

---

## 四、核心模块详细设计

### 4.1 LLM Adapter（llm/）

```python
# llm/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """LLM 返回结果。"""
    content: str
    usage: dict[str, int]  # {"prompt_tokens": ..., "completion_tokens": ...}
    model: str


class LLMAdapter(ABC):
    """LLM 统一接口。所有引擎通过此接口调用大模型。"""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """文本补全。"""
        ...

    @abstractmethod
    async def complete_json(
        self,
        prompt: str,
        *,
        system: str = "",
        schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> dict:
        """结构化 JSON 输出。用于抽取概念、关系等需要结构化返回的场景。"""
        ...

    @abstractmethod
    async def vision(
        self,
        image_path: str,
        prompt: str,
    ) -> LLMResponse:
        """图片理解。用于截图、图表等视觉内容。"""
        ...
```

**为什么用 async**：Ingest 一篇资料可能需要多次 LLM 调用（抽取概念、生成摘要、推断关系），async 允许并发执行不依赖彼此的调用，减少总耗时。

**Provider 实现**：

```python
# llm/openai.py（示例）

class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str | None = None):
        self.client = httpx.AsyncClient(...)
        self.model = model

    async def complete(self, prompt, *, system="", temperature=0.3, max_tokens=4096):
        response = await self.client.post("/v1/chat/completions", json={
            "model": self.model,
            "messages": [
                {"role": "system", "content": system} if system else None,
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        ...

    async def complete_json(self, prompt, *, system="", schema=None, temperature=0.1):
        # 使用 response_format={"type": "json_object"} 或 json_schema
        ...
```

**Compatible 模式**：`llm/compatible.py` 继承 `OpenAIAdapter`，只改 base_url，即可支持 DeepSeek、月之暗面、零一万物等 OpenAI 兼容 API。

### 4.2 Ingest Engine（engine/ingest.py）

Ingest 是最核心的操作。下面拆解每一步中**哪些是代码做的、哪些调 LLM**：

```
Ingest 流程：

1. [代码] 解析输入源
   ├── 本地文件 → parsers/ 按文件类型解析为纯文本
   ├── URL → parsers/url.py 调 Jina Reader 获取 Markdown
   └── 直接文本 → 透传

2. [LLM] 理解内容，抽取结构化信息
   输入：原始文本
   输出（JSON）：
   {
     "title": "资料标题",
     "summary": "200 字摘要",
     "key_points": ["要点1", "要点2", ...],
     "concepts": [
       {"id": "llm-wiki", "label": "LLM Wiki", "description": "...", "is_new": true}
     ],
     "entities": [
       {"id": "andrej-karpathy", "label": "Andrej Karpathy", "description": "...", "is_new": true}
     ],
     "areas": ["AI", "knowledge-management"],
     "relations": [
       {"source": "andrej-karpathy", "target": "llm-wiki", "relation": "提出", "confidence": "EXTRACTED"},
       {"source": "llm-wiki", "target": "rag", "relation": "替代方案", "confidence": "INFERRED"}
     ],
     "quotes": ["原文重要引用1", "原文重要引用2"]
   }

3. [代码] 创建/更新 wiki 页面
   ├── wiki/sources/{id}.md     ← 来源页（用 source 模板填充）
   ├── wiki/concepts/{id}.md    ← 新概念页（用 concept 模板）或追加已有页面
   ├── wiki/entities/{id}.md    ← 新实体页（用 entity 模板）或追加已有页面
   └── wiki/areas/{id}.md       ← 更新领域页

4. [代码] 更新导航文件
   ├── wiki/index.md            ← 追加新条目，按类型分组排序
   └── wiki/log.md              ← 顶部追加操作记录

5. [代码] 更新图谱
   ├── graph/graph.json          ← 追加节点和边（去重）
   └── graph/GRAPH_REPORT.md     ← 重新生成统计报告

6. [代码] 后处理
   ├── 轻量 Lint（坏链检测）
   └── 输出摘要
```

**关键设计决策**：步骤 2 是唯一调 LLM 的地方。一次 LLM 调用返回全部结构化信息（概念、实体、关系、摘要），而不是分多次调用。这样：
- 减少 API 调用次数和成本
- LLM 一次性看到完整上下文，抽取质量更高
- 代码层拿到结构化 JSON 后，后续步骤全部确定性执行

```python
# engine/ingest.py（核心接口）

@dataclass
class IngestResult:
    """Ingest 操作的结果。"""
    source_page: str           # 创建的来源页路径
    created_pages: list[str]   # 新创建的页面
    updated_pages: list[str]   # 更新的页面
    graph_nodes_added: int     # 新增图谱节点数
    graph_edges_added: int     # 新增图谱边数
    llm_tokens_used: int       # LLM token 消耗


class IngestEngine:
    def __init__(self, project: Project, llm: LLMAdapter, schema: WikiSchema):
        self.project = project
        self.llm = llm
        self.schema = schema
        self.wiki = WikiManager(project)
        self.graph = GraphManager(project)

    async def ingest(
        self,
        source: str | Path,
        *,
        source_type: str = "auto",  # auto | file | url | text
        dry_run: bool = False,
    ) -> IngestResult:
        """执行 Ingest 操作。"""

        # 1. 解析输入
        raw_text = await self._parse_source(source, source_type)

        # 2. LLM 抽取（唯一的 LLM 调用）
        extraction = await self._extract(raw_text)

        if dry_run:
            return self._preview(extraction)

        # 3. 写 wiki 页面
        created, updated = await self._write_pages(extraction, source)

        # 4. 更新导航
        self.wiki.update_index()
        self.wiki.append_log("ingest", extraction.title, created + updated)

        # 5. 更新图谱
        nodes_added, edges_added = self.graph.merge(extraction.to_graph_data())
        self.graph.regenerate_report()

        # 6. 轻量 Lint
        self._quick_lint(created + updated)

        return IngestResult(...)
```

### 4.3 LLM Prompt 设计（prompts/ingest.py）

Prompt 是决定 Ingest 质量的关键。当前 CLAUDE.md 中的规范要转化为精确的 prompt：

```python
# prompts/ingest.py

INGEST_SYSTEM = """你是一个知识管理系统的内容分析引擎。
你的任务是从原始资料中抽取结构化信息，包括概念、实体、关系和摘要。

输出要求：
1. 严格按照 JSON schema 返回
2. 概念和实体的 id 使用 kebab-case 英文命名（如 llm-wiki, andrej-karpathy）
3. 关系使用语义化描述（参考类型：组成部分、属于、导致、解决、替代方案、提出、创建、应用于、依赖、基于等）
4. 置信度标注：
   - EXTRACTED：原文明确写了这个关系
   - INFERRED：从内容理解中合理推断
   - AMBIGUOUS：不确定的关联
5. 不要编造原文中没有的信息"""

INGEST_PROMPT_TEMPLATE = """请分析以下资料，抽取结构化信息。

{existing_context}

---
## 原始资料

{raw_text}

---
## 输出格式

请返回 JSON：
{{
  "title": "资料标题（简洁准确）",
  "summary": "200 字以内的摘要",
  "key_points": ["要点1", "要点2", ...],
  "concepts": [
    {{"id": "kebab-case-id", "label": "显示名称", "description": "一句话描述", "is_new": true/false}}
  ],
  "entities": [
    {{"id": "kebab-case-id", "label": "显示名称", "description": "一句话描述", "is_new": true/false}}
  ],
  "areas": ["领域名称"],
  "relations": [
    {{"source": "source-id", "target": "target-id", "relation": "语义化关系", "confidence": "EXTRACTED/INFERRED/AMBIGUOUS"}}
  ],
  "quotes": ["重要引用原文"]
}}"""
```

`{existing_context}` 部分：会注入当前 wiki 中已有的概念和实体列表（id + label），让 LLM 知道哪些概念已经存在，避免重复创建或命名不一致。

### 4.4 Query Engine（engine/query.py）

```
Query 流程：

1. [代码] 关键词/语义匹配，定位相关页面
   ├── 搜索 wiki/index.md 中的条目描述
   ├── 搜索图谱节点的 label 和 description
   └── 全文搜索 wiki 页面内容

2. [代码] 图谱扩展
   ├── 对匹配到的节点，调 graph.get_neighbors() 扩展
   └── 如果问题涉及两个概念，调 graph.shortest_path() 发现关联链

3. [代码] 收集上下文
   ├── 读取所有相关页面的完整内容
   └── 按相关度排序，截断到 LLM 上下文窗口限制

4. [LLM] 综合回答
   输入：用户问题 + 相关页面内容 + 图谱关系信息
   输出：回答文本（包含 [[wiki-link]] 引用）

5. [代码] 后处理
   ├── 如有价值，保存到 wiki/outputs/
   ├── 更新 index.md 和 log.md
   └── 返回回答
```

```python
# engine/query.py

@dataclass
class QueryResult:
    answer: str                # 回答文本
    referenced_pages: list[str]  # 引用的页面
    saved_to: str | None       # 保存的 output 路径（如果保存了）
    llm_tokens_used: int


class QueryEngine:
    async def query(
        self,
        question: str,
        *,
        save: bool | None = None,  # None=自动判断, True=强制保存, False=不保存
    ) -> QueryResult:
        # 1. 定位相关页面
        candidates = self._search_relevant_pages(question)

        # 2. 图谱扩展
        candidates = self._expand_via_graph(candidates, question)

        # 3. 收集上下文
        context = self._build_context(candidates)

        # 4. LLM 回答
        answer = await self._generate_answer(question, context)

        # 5. 后处理
        if save or (save is None and self._is_valuable(answer)):
            saved_to = self._save_output(question, answer)
        ...
```

### 4.5 Lint Engine（engine/lint.py）

Lint 三个级别中，light 级别**完全不调 LLM**：

```python
# engine/lint.py

@dataclass
class LintIssue:
    level: str      # error | warning | info
    category: str   # broken-link | orphan | missing-frontmatter | ...
    file: str       # 涉及的文件
    message: str    # 问题描述
    fixable: bool   # 是否可自动修复


class LintEngine:
    def lint_light(self) -> list[LintIssue]:
        """轻量检查（零 LLM token）。"""
        issues = []
        issues += self._check_broken_links()     # wiki-link 指向的文件是否存在
        issues += self._check_orphan_pages()      # 有无页面没有任何入链
        issues += self._check_index_consistency() # index.md 是否收录了所有页面
        issues += self._check_frontmatter()       # 必填字段是否齐全
        issues += self._check_graph_consistency() # 图谱节点是否都有对应 wiki 页面
        return issues

    async def lint_deep(self) -> list[LintIssue]:
        """深度检查（调 LLM）。"""
        issues = self.lint_light()  # 先跑轻量
        issues += await self._check_contradictions()  # 页面间矛盾
        issues += await self._check_stale_info()      # 过时信息
        issues += await self._check_stub_completable() # stub 是否可补全
        issues += await self._check_missing_concepts() # 缺失概念
        return issues

    async def lint_growth(self) -> list[LintIssue]:
        """生长检查（调 LLM + 图谱分析）。"""
        issues = await self.lint_deep()  # 先跑深度
        issues += self._check_graph_isolated()     # 图谱孤立节点
        issues += self._check_graph_overloaded()   # 核心节点过载
        issues += await self._discover_cross_domain_relations()  # 跨域关联
        issues += self._identify_knowledge_gaps()  # 知识缺口
        return issues

    def fix(self, issues: list[LintIssue]) -> list[str]:
        """自动修复可修复的问题。"""
        fixed = []
        for issue in issues:
            if issue.fixable:
                self._fix_issue(issue)
                fixed.append(issue.message)
        return fixed
```

### 4.6 Graph Manager（graph/manager.py）

把现有 `graph-server.py` 中的逻辑拆为两部分：
- `graph/manager.py`：图谱的读写、查询（纯 Python 库，不依赖 MCP）
- `graph/server.py`：MCP Server 壳（调用 manager 的方法）

```python
# graph/manager.py

class GraphManager:
    """知识图谱管理器。封装 NetworkX 操作。"""

    def __init__(self, project: Project):
        self.project = project
        self.graph_path = project.path / "graph" / "graph.json"
        self._graph: nx.Graph | None = None

    @property
    def graph(self) -> nx.Graph:
        if self._graph is None:
            self._graph = self._load()
        return self._graph

    def merge(self, data: GraphData) -> tuple[int, int]:
        """合并新的节点和边到图谱（去重）。返回 (新增节点数, 新增边数)。"""
        nodes_added = 0
        for node in data.nodes:
            if node.id not in self.graph:
                self.graph.add_node(node.id, **node.attrs())
                nodes_added += 1
            else:
                # 更新已有节点属性
                self.graph.nodes[node.id].update(node.attrs())

        edges_added = 0
        for edge in data.edges:
            if not self.graph.has_edge(edge.source, edge.target):
                self.graph.add_edge(edge.source, edge.target, **edge.attrs())
                edges_added += 1

        self._save()
        return nodes_added, edges_added

    def get_neighbors(self, node_id: str, depth: int = 1, min_confidence: str | None = None) -> dict:
        """查询邻居节点（复用现有 graph-server.py 逻辑）。"""
        ...

    def shortest_path(self, source: str, target: str) -> dict:
        ...

    def top_nodes(self, limit: int = 10) -> list[dict]:
        ...

    def stats(self) -> dict:
        """含置信度分布。"""
        ...

    def regenerate_report(self) -> None:
        """重新生成 GRAPH_REPORT.md。"""
        ...
```

### 4.7 Wiki Page 模型（wiki/page.py）

```python
# wiki/page.py

@dataclass
class WikiPage:
    """一个 wiki 页面的内存模型。"""
    path: Path                  # 相对路径（如 concepts/llm-wiki.md）
    title: str
    type: str                   # concept | entity | source | output | area | journal
    created: date
    updated: date | None = None
    tags: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    status: str | None = None   # active | stale | stub
    author: str | None = None
    body: str = ""              # frontmatter 之后的 Markdown 正文

    @classmethod
    def load(cls, file_path: Path) -> "WikiPage":
        """从 .md 文件加载。解析 YAML frontmatter + body。"""
        ...

    def save(self, base_dir: Path) -> None:
        """写入 .md 文件。序列化 frontmatter + body。"""
        ...

    def append_section(self, heading: str, content: str) -> None:
        """向指定章节追加内容（更新已有页面时使用）。"""
        ...

    def wiki_links(self) -> list[str]:
        """提取页面中所有 [[wiki-link]]。"""
        ...

    @classmethod
    def from_template(cls, page_type: str, schema: WikiSchema, **kwargs) -> "WikiPage":
        """根据 schema 中定义的模板创建新页面。"""
        ...
```

---

## 五、Prompt 策略

### 5.1 Ingest Prompt 上下文注入

Ingest 时，LLM 需要知道 wiki 中**已有哪些概念和实体**，否则会重复创建或命名不一致。

策略：在 prompt 中注入 `existing_context`：

```
## 当前 wiki 已有概念（请复用已有 id，不要重复创建）

concepts:
- llm-wiki: LLM 驱动的个人知识管理系统
- rag: 检索增强生成
- knowledge-graph: 知识图谱
- ...

entities:
- andrej-karpathy: AI 研究者，前 Tesla AI 总监
- ...
```

当 wiki 规模增大时（>100 个概念），不注入全部列表，而是：
1. 先用原始文本的关键词搜索图谱，找到可能相关的节点
2. 只注入相关的 20-30 个已有概念

### 5.2 不同操作的 LLM 使用量

| 操作 | LLM 调用次数 | 说明 |
|---|---|---|
| Ingest | 1 次 | 一次调用完成全部抽取（概念 + 实体 + 关系 + 摘要） |
| Query | 1 次 | 检索用代码完成，只在最终回答时调 LLM |
| Lint light | 0 次 | 纯代码检查 |
| Lint deep | N 次 | 每组可能矛盾的页面对调一次 |
| Lint growth | 少量 | 图谱分析用代码，跨域关联发现可能调 LLM |
| Review | 1 次 | 统计用代码，生成综述文本调 LLM |

### 5.3 Token 优化

- **Ingest**：原始资料如果超过 LLM 上下文窗口，先用代码分段，每段独立抽取，最后合并去重
- **Query**：相关页面内容按相关度排序，截断到 context window 的 70%，留 30% 给回答
- **便宜模型降级**：Lint deep 和 Review 不需要最强模型，config 中可配置使用 gpt-4o-mini

---

## 六、与现有系统的关系

### 6.1 共存方案

CLI 化后，**现有的外挂文档库模式继续可用**：

```
方式 A（现有）：用户 → Claude Code → 读 CLAUDE.md → 直接操作 wiki 文件
方式 B（CLI）：  用户 → 终端 → llm-wiki ingest → 引擎操作 wiki 文件
方式 C（混合）：用户 → Claude Code → 调 MCP wiki_ingest → 引擎操作 wiki 文件
```

三种方式产出的 wiki 格式完全一致（都遵循 wiki-schema.yml），可以混用。

### 6.2 迁移路径

```
阶段 1：CLI 和外挂模式并存
  - CLAUDE.md 保持不变
  - CLI 作为补充工具
  - 用户可以选择用哪种方式 ingest

阶段 2：CLI 作为 MCP 工具接入 Agent 平台
  - CLAUDE.md 简化为：「使用 MCP wiki 工具执行操作」
  - Agent 不再自己解析 schema，而是调用 CLI 引擎
  - 操作一致性大幅提升

阶段 3：CLI 成为唯一引擎
  - CLAUDE.md / AGENTS.md 仅描述 MCP 工具用法
  - 所有操作都经过引擎，质量可控可测
```

### 6.3 现有代码复用

| 现有文件 | CLI 中的去向 |
|---|---|
| `wiki-schema.yml` | 打包进 `src/llm_wiki/schema/`，作为内置 schema |
| `graph-server.py` 查询逻辑 | 迁入 `graph/manager.py` |
| `graph-server.py` MCP 壳 | 迁入 `graph/server.py` |
| `CLAUDE.md` 中的操作步骤 | 转化为 `engine/*.py` 中的代码流程 |
| `CLAUDE.md` 中的格式规范 | 转化为 `wiki/page.py` 中的模板和验证 |

---

## 七、打包和分发

### 7.1 项目配置

```toml
# pyproject.toml

[project]
name = "llm-wiki"
version = "0.1.0"
description = "AI-powered personal knowledge management system"
requires-python = ">=3.11"
license = { text = "MIT" }

dependencies = [
    "click>=8.0",
    "httpx>=0.27",
    "networkx>=3.0",
    "pyyaml>=6.0",
    "rich>=13.0",
    "tomli>=2.0; python_version < '3.12'",
    "tomli-w>=1.0",
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.30"]
pdf = ["marker-pdf>=1.0"]
audio = ["openai-whisper>=20230918"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
]
all = ["llm-wiki[anthropic,pdf,audio]"]

[project.scripts]
llm-wiki = "llm_wiki.cli.main:app"
```

### 7.2 最小依赖原则

核心依赖（必装）：
- `click`：CLI 框架
- `httpx`：HTTP 客户端（调 LLM API、Jina Reader）
- `networkx`：图谱
- `pyyaml`：schema 解析
- `rich`：终端输出美化
- `tomli` / `tomli-w`：配置文件读写

可选依赖（按需安装）：
- `anthropic`：使用 Anthropic Claude 时
- `marker-pdf`：处理 PDF 时
- `openai-whisper`：处理音频时

不引入重框架：不用 LangChain、不用 LlamaIndex、不用 SQLAlchemy。保持轻量。

---

## 八、测试策略

### 8.1 测试分层

```
tests/
├── unit/                    # 单元测试（不调 LLM，不读写文件系统）
│   ├── test_page.py         # WikiPage 的 frontmatter 解析、序列化
│   ├── test_graph.py        # GraphManager 的增删查改
│   ├── test_index.py        # index.md 的更新逻辑
│   ├── test_log.py          # log.md 的追加逻辑
│   └── test_prompts.py      # prompt 模板的格式化
│
├── integration/             # 集成测试（mock LLM，读写临时文件系统）
│   ├── test_ingest.py       # 完整 Ingest 流程（mock LLM 返回固定 JSON）
│   ├── test_query.py        # 完整 Query 流程
│   └── test_lint.py         # Lint 检查流程
│
└── e2e/                     # 端到端测试（真实 LLM 调用，按需运行）
    └── test_ingest_real.py  # 真实 Ingest：一篇文章进去 → 检查产出
```

### 8.2 Mock LLM

集成测试中，mock LLM 返回预定义的 JSON：

```python
# tests/conftest.py

class MockLLMAdapter(LLMAdapter):
    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.call_log = []

    async def complete_json(self, prompt, **kwargs):
        self.call_log.append(prompt)
        # 根据 prompt 中的关键词匹配预定义响应
        for key, response in self.responses.items():
            if key in prompt:
                return json.loads(response)
        raise ValueError(f"No mock response for prompt: {prompt[:100]}")
```

这样可以测试完整的 Ingest 流程而不消耗 API token。

### 8.3 关键测试用例

| 测试 | 验证内容 |
|---|---|
| Ingest 新文章 | source 页创建、concepts 页创建、index 更新、graph 更新 |
| Ingest 重复概念 | 已有 concept 页被追加而非覆盖 |
| Ingest 更新实体 | 已有 entity 页补充新信息 |
| Query 简单问题 | 正确引用 wiki 页面 |
| Query 跨域关联 | 通过图谱发现间接关系 |
| Lint light | 检出坏链、孤立页、缺失 frontmatter |
| Lint fix | 自动修复 index 缺失条目 |
| Graph merge | 节点去重、边去重 |
| Graph confidence | 置信度过滤正确 |
| Page frontmatter | 序列化 → 反序列化 round-trip |

---

## 九、实现优先级

### Phase 1a — 最小可用（MVP）

目标：`llm-wiki ingest` 和 `llm-wiki query` 能跑通。

```
1. 项目骨架（pyproject.toml、src layout、CLI 框架）
2. config 模块（读写 .local/config.toml）
3. LLM Adapter（先做 OpenAI）
4. WikiPage 模型（frontmatter 解析 + 序列化）
5. Ingest Engine（完整流程）
6. Ingest prompt（设计 + 调优）
7. index.md / log.md 管理
8. GraphManager（merge + save）
9. Query Engine（搜索 + LLM 回答）
10. CLI 命令（ingest + query）
```

### Phase 1b — 完整 CLI

```
11. Lint Engine（三级检查 + --fix）
12. Review Engine
13. Anthropic Adapter
14. Ollama Adapter
15. Compatible Adapter
16. URL parser（Jina Reader）
17. PDF parser
18. graph 子命令（stats / neighbors / path / top / node）
19. search 命令
20. sync 命令（git pull/push）
21. init 命令（交互式初始化）
22. dry-run 模式
23. GRAPH_REPORT.md 生成（含跨域关联、待审关系、知识缺口）
```

### Phase 1c — 打磨发布

```
24. 测试覆盖（unit + integration）
25. 错误处理和用户友好提示
26. 文档（README + --help）
27. PyPI 发布
28. mcp serve 命令（Phase 2 预埋）
```

---

## 十、开放问题

| 问题 | 选项 | 建议 |
|---|---|---|
| CLI 框架选型 | click vs typer | click（更成熟、更灵活，typer 对 async 支持弱） |
| 异步运行时 | asyncio vs 同步 | async（LLM 调用天然异步，用 asyncio.run 包装） |
| 配置格式 | TOML vs YAML vs JSON | TOML（Python 生态标准，pyproject.toml 同款） |
| Ingest 时 LLM 一次调还是多次 | 1 次 vs 分步 | 1 次（减少调用、保持上下文完整） |
| 长文档处理 | 截断 vs 分段 | 分段抽取 + 合并去重（不丢信息） |
| wiki 搜索 | 全文扫描 vs 索引 | 初期全文扫描（ripgrep），wiki 大了再加索引 |
| 输出语言 | 固定中文 vs 可配置 | 可配置（config.toml 中设 language），默认 zh |
