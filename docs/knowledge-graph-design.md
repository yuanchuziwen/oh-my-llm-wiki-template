# 知识图谱设计

> Agent 在 Ingest 时顺手维护图谱，通过自建 MCP Server 提供按需查询。零外部依赖，零额外 token 开销。

---

## 一、背景与决策

### 1.1 为什么要知识图谱

wiki 页面是扁平的文件列表，Agent 查询时只能通过 `index.md` + `[[wiki-link]]` 找关联。当 wiki 增长到几十上百页，页面之间的**隐含关系**（没有直接互引但实际相关）会越来越多，Agent 仅靠读文件很难发现。

知识图谱用**节点（实体/概念）+ 边（关系）** 的结构显式记录这些关联，让 Agent 能高效查询：
- "和 X 相关的都有哪些？"
- "A 和 B 之间有什么联系？"
- "知识库里最核心的概念是哪些？"

### 1.2 为什么不用 Graphify

[Graphify](https://github.com/safishamsi/graphify) 是一个成熟的知识图谱工具（22.5k star），深入分析其源码后，决定**不直接使用**，原因：

| 问题 | 说明 |
|---|---|
| 额外 LLM 调用 | Graphify 自己调 LLM API 做语义提取，产生额外 token 费用 |
| 信息重复提取 | Agent 在 Ingest 时已经理解了内容，Graphify 又读一遍再提取，浪费 |
| 外部依赖 | 需要 `pip install graphifyy`，增加环境复杂度 |
| 功能冗余 | 社区检测、可视化等功能前期不需要 |

**核心洞察**：Agent 在写 wiki 页面的时候，**已经知道**有哪些实体、概念、以及它们之间的关系。只需要让 Agent 把这些信息顺手写入 graph.json，就完成了图谱构建——不需要事后再用另一个工具重新提取。

### 1.3 整体方案

```
Agent Ingest raw/xxx.md
  │
  ├─ 写 wiki 页面（现有流程，不变）
  │   → wiki/sources/xxx.md
  │   → wiki/concepts/yyy.md
  │   → wiki/entities/zzz.md
  │
  └─ 同时更新图谱（新增步骤）
      → 追加节点和边到 graph/graph.json
      → 更新 graph/GRAPH_REPORT.md（统计摘要）

Agent Query "A 和 B 有什么关系？"
  │
  ├─ 读 index.md（现有流程，不变）
  │
  └─ 调 MCP 工具查图谱（新增步骤）
      → get_neighbors("A") / shortest_path("A", "B")
      → 返回精确结果，不需要读整个 graph.json
```

---

## 二、图谱数据格式

### 2.1 graph.json

使用 NetworkX node-link 格式（通用、可被各种工具读取）：

```json
{
  "directed": false,
  "nodes": [
    {
      "id": "llm-wiki",
      "label": "LLM Wiki",
      "type": "concept",
      "wiki_path": "concepts/llm-wiki.md",
      "description": "LLM 驱动的个人知识管理系统"
    },
    {
      "id": "andrej-karpathy",
      "label": "Andrej Karpathy",
      "type": "entity",
      "wiki_path": "entities/andrej-karpathy.md",
      "description": "AI 研究者，LLM Wiki 概念提出者"
    },
    {
      "id": "rag",
      "label": "RAG",
      "type": "concept",
      "wiki_path": "concepts/rag.md",
      "description": "检索增强生成"
    }
  ],
  "links": [
    {
      "source": "andrej-karpathy",
      "target": "llm-wiki",
      "relation": "提出者",
      "source_file": "sources/karpathy-llm-wiki.md"
    },
    {
      "source": "llm-wiki",
      "target": "rag",
      "relation": "替代方案",
      "source_file": "sources/karpathy-llm-wiki.md"
    }
  ]
}
```

**字段说明**：

节点（nodes）：

| 字段 | 说明 |
|---|---|
| `id` | 唯一标识，与 wiki 文件名一致（kebab-case） |
| `label` | 显示名称 |
| `type` | concept / entity / area |
| `wiki_path` | 对应的 wiki 页面路径 |
| `description` | 一句话描述 |

边（links）：

| 字段 | 说明 |
|---|---|
| `source` | 起始节点 id |
| `target` | 目标节点 id |
| `relation` | 关系描述（如"提出者"、"替代方案"、"属于"） |
| `source_file` | 这条关系来源于哪个 wiki 页面 |

### 2.2 GRAPH_REPORT.md

Agent 生成的人/AI 可读摘要：

```markdown
# 知识图谱报告

> 最后更新：2026-04-13 | 节点 42 个 | 边 87 条

## 核心节点（连接度 Top 10）

| 节点 | 类型 | 连接数 | Wiki 页面 |
|---|---|---|---|
| LLM Wiki | concept | 12 | [[concepts/llm-wiki]] |
| Andrej Karpathy | entity | 8 | [[entities/andrej-karpathy]] |
| RAG | concept | 7 | [[concepts/rag]] |
| ... | ... | ... | ... |

## 孤立节点（连接度 = 0）

- [[concepts/xxx]] — 没有与其他节点建立关系，可能需要补充

## 最近更新

- 2026-04-13: 新增 3 个节点、5 条边（来源：ingest karpathy-llm-wiki）
```

---

## 三、Agent 如何维护图谱

### 3.1 Ingest 时更新

Agent 完成 wiki 页面创建/更新后，额外执行：

1. **识别节点**：本次 Ingest 涉及了哪些 concepts、entities、areas → 确保 graph.json 中有对应节点
2. **识别关系**：这些节点之间有什么关系 → 追加边（去重）
3. **更新 GRAPH_REPORT.md**：重新统计核心节点、孤立节点

这些信息 Agent 在写 wiki 页面时已经掌握了（frontmatter 中的 `related` 字段、正文中的 `[[wiki-link]]`），不需要额外分析。

### 3.2 更新规则

- **新增节点**：创建新 wiki 页面时，同步追加节点
- **新增边**：发现新关系时追加（通过 source + target 去重，避免重复边）
- **删除**：不主动删除节点和边（wiki 页面很少删除，保持图谱稳定）
- **修改**：如果 wiki 页面的标题或描述变了，同步更新对应节点

### 3.3 写入 graph.json 的方式

Agent 读取当前 graph.json → 在内存中追加新节点/边 → 写回文件。

对于小规模 wiki（<200 页），graph.json 通常只有几十 KB，Agent 可以完整读入和写出，不会有性能问题。

---

## 四、MCP Server：按需查询

### 4.1 为什么需要 MCP Server

当 wiki 增长到几百页，graph.json 可能有上千节点和上万条边。Agent 每次查询都读整个文件会浪费大量上下文窗口。

MCP Server 把 graph.json 加载到内存，Agent 通过工具调用按需查询，只返回需要的结果。

### 4.2 自建 MCP Server

一个 ~80 行的 Python 脚本（`tools/graph-server.py`），依赖 `networkx`（单个 Python 包）：

```python
# tools/graph-server.py（伪代码，展示核心逻辑）

import networkx as nx
import json

# 启动时加载图谱
G = load_graph("graph/graph.json")

# MCP 工具 1：获取邻居节点
def get_neighbors(node_id, depth=1):
    """查询某节点的关联节点（1-N 跳）"""
    subgraph = nx.ego_graph(G, node_id, radius=depth)
    return format_nodes_and_edges(subgraph)

# MCP 工具 2：最短路径
def shortest_path(source, target):
    """查询两个节点之间的关联链"""
    path = nx.shortest_path(G, source, target)
    return path_with_relations(path)

# MCP 工具 3：核心节点
def top_nodes(limit=10):
    """按连接度排序，返回最核心的节点"""
    return sorted(G.degree(), key=lambda x: x[1], reverse=True)[:limit]

# MCP 工具 4：图谱统计
def graph_stats():
    """返回图谱的基本统计"""
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "isolated": len(list(nx.isolates(G)))
    }

# MCP 工具 5：查询单个节点
def get_node(node_id):
    """返回节点详情"""
    return G.nodes[node_id]
```

### 4.3 平台自动管理

配置到 MCP 配置文件后，Agent 平台（Claude Code / Cursor）**自动启动和关闭** MCP Server，用户无需手动管理：

**Claude Code**（`.claude/mcp.json`）：
```json
{
  "mcpServers": {
    "wiki-graph": {
      "command": "python3",
      "args": ["tools/graph-server.py"],
      "type": "stdio"
    }
  }
}
```

**Cursor**（`.cursor/mcp.json`）：
```json
{
  "mcpServers": {
    "wiki-graph": {
      "command": "python3",
      "args": ["tools/graph-server.py"],
      "type": "stdio"
    }
  }
}
```

启动 Agent → 自动拉起 graph-server.py → Agent 可用图谱查询工具
关闭 Agent → 自动停止进程

### 4.4 图谱不存在时的降级

graph-server.py 启动时检测 graph.json 是否存在：
- **存在** → 正常加载，所有工具可用
- **不存在** → 返回空结果，不报错，不阻断 Agent 其他操作

这意味着新设备、新 wiki 都能正常工作，图谱功能随着第一次 Ingest 自然启用。

---

## 五、与四个核心操作的集成

### 5.1 Ingest

```
现有流程（不变）：
  读 raw → 写 wiki 页面 → 更新 index.md + log.md

新增步骤：
  → 更新 graph/graph.json（追加节点和边）
  → 更新 graph/GRAPH_REPORT.md（重新统计）
```

Agent 在操作手册（CLAUDE.md / AGENTS.md）中增加一步即可。

### 5.2 Query

```
现有流程（不变）：
  读 index.md → 读相关 wiki 页面 → 回答

新增步骤（可选）：
  → 调 MCP 工具辅助定位关联
     get_neighbors: 扩展搜索范围
     shortest_path: 发现隐含关联链
     top_nodes: 了解知识库全局重点
```

Agent 自行判断是否需要查图谱——简单问题直接读 wiki，复杂关联问题才查图谱。

### 5.3 Lint

图谱为 Lint 提供新的检查维度：

| 检查项 | 方式 | 说明 |
|---|---|---|
| 孤立节点 | `graph_stats` | wiki 页面存在但没有任何关系，可能需要补充关联 |
| 核心节点过载 | `top_nodes` | 某个概念连接度过高，可能需要拆分 |
| 图谱-index 不一致 | 对比 graph.json 节点 vs index.md 条目 | 确保两者同步 |
| 缺失关系 | Agent 阅读 wiki 页面后与图谱对比 | 发现应有但未记录的关系 |

### 5.4 Review

journal 页面可增加图谱维度：
- 本期新增了多少节点和边
- 核心节点排名变化
- 新出现的跨领域关联

---

## 六、目录结构

```
llm-wiki/
├── graph/
│   ├── graph.json              ← 图谱数据（Git 跟踪）
│   └── GRAPH_REPORT.md         ← 统计摘要（Git 跟踪）
│
├── tools/
│   └── graph-server.py         ← MCP Server（Git 跟踪）
│
├── .claude/mcp.json            ← Claude Code MCP 配置
└── .cursor/mcp.json            ← Cursor MCP 配置
```

### Git 策略

| 文件 | Git 状态 | 说明 |
|---|---|---|
| `graph/graph.json` | 跟踪 | 跨设备共享图谱 |
| `graph/GRAPH_REPORT.md` | 跟踪 | 跨设备共享报告 |
| `tools/graph-server.py` | 跟踪 | 跨设备共享代码 |
| `.claude/mcp.json` | 跟踪 | Agent 配置 |

---

## 七、实施步骤

### Step 1：定义图谱规范

- [ ] 更新 `wiki-schema.yml`，增加 graph.json 格式定义
- [ ] 更新 `CLAUDE.md` / `AGENTS.md`，在 Ingest 和 Query 流程中增加图谱步骤

### Step 2：编写 MCP Server

- [ ] 创建 `tools/graph-server.py`
- [ ] 实现 5 个工具：`get_neighbors`、`shortest_path`、`top_nodes`、`graph_stats`、`get_node`
- [ ] 处理 graph.json 不存在的降级情况
- [ ] 配置 `.claude/mcp.json` 和 `.cursor/mcp.json`

### Step 3：验证闭环

- [ ] Ingest 一篇资料，确认 graph.json 被正确更新
- [ ] 通过 MCP 工具查询图谱，确认返回正确结果
- [ ] 执行 Query，确认 Agent 能结合图谱回答

### Step 4：后续可选增强

- [ ] 社区检测：加几行 Leiden/Louvain 代码，自动给节点打社区标签
- [ ] 可视化：生成交互式 HTML（D3.js 或 vis.js）
- [ ] 查询脚本：独立于 MCP 的命令行查询工具

---

## 八、存储层扩展路径

### 8.1 性能估算

当前方案使用 NetworkX（纯 Python 内存图库）+ graph.json 文件存储。性能参考：

| wiki 规模 | 节点数 | 边数 | graph.json 大小 | 内存占用 | 查询延迟 |
|---|---|---|---|---|---|
| 100 页 | ~200 | ~500 | ~50 KB | ~1 MB | <1ms |
| 1,000 页 | ~2,000 | ~10,000 | ~2 MB | ~20 MB | <10ms |
| 10,000 页 | ~20,000 | ~100,000 | ~20 MB | ~200 MB | <100ms |
| 100,000 页 | ~200,000 | ~1,000,000 | ~200 MB | ~2 GB | 秒级 |

个人 wiki 每天 ingest 3 篇，一年约 1,000 篇。**1 万页以内 NetworkX 完全没有性能问题**，当前方案预计可以支撑数年使用。

真正的瓶颈不在查询速度，而在 **graph.json 文件读写**：Agent 每次 Ingest 需要读取完整 JSON → 追加 → 写回。到了几万节点，这个 I/O 会成为瓶颈。

### 8.2 如果需要图数据库

当 wiki 规模真的突破万页，可以考虑引入图数据库（如 Neo4j、DuckDB）：

| 维度 | NetworkX + JSON（当前） | 图数据库（如 Neo4j） |
|---|---|---|
| 安装 | `pip install networkx` | 需要装数据库服务（Neo4j 需要 Java） |
| 部署 | 零部署，Python 脚本 | 需要启动数据库进程，配置端口/认证 |
| 跨设备同步 | graph.json 直接 Git 同步 | 数据库文件不好 Git 同步，需要导入导出 |
| 增量写入 | 读全量 → 追加 → 写全量 | 直接 INSERT，真正的增量 |
| 查询能力 | 基础图算法（够用） | Cypher 查询语言，更强大 |
| 适合规模 | <10,000 节点 | 任意规模 |
| 维护成本 | 几乎为零 | 需要关注数据库进程、备份、版本升级 |

**收益**：大规模时查询更快、增量写入更高效、查询语言更强大。

**代价**：每台设备都要装数据库、跨设备同步变复杂（graph.json 一个文件 Git push 就完了，数据库做不到）、部署维护成本显著增加。

### 8.3 推荐的渐进路径

```
NetworkX + graph.json（现在）
  │
  │  wiki 到几千页，JSON 读写变慢
  ↓
SQLite 存储（中期过渡，零部署，文件级 Git 同步）
  │
  │  wiki 到万页以上，需要复杂图查询
  ↓
Neo4j / 专用图数据库（远期，按需引入）
```

**当前不需要为此做任何准备**——graph.json 格式是通用的，迁移时只需写一个导入脚本。

---

## 九、与 Graphify 的关系

我们**借鉴了 Graphify 的设计思路**（graph.json 格式、MCP Server 查询接口、GRAPH_REPORT.md 摘要），但实现上完全独立：

| 维度 | Graphify | 我们的方案 |
|---|---|---|
| 图谱构建 | 独立 CLI 工具，自己调 LLM | Agent 在 Ingest 时顺手写入 |
| LLM 调用 | 额外调用（费 token） | 零额外调用（Agent 已经在处理内容） |
| MCP Server | ~200 行，7 个工具 | ~80 行，5 个工具（够用） |
| 社区检测 | 内置 Leiden 算法 | 不做（前期不需要，后续可加） |
| 可视化 | 内置 D3 HTML | 不做（前期不需要，后续可加） |
| 安装依赖 | `pip install graphifyy` | 只需 `networkx`（graph-server.py 用） |

如果将来 wiki 规模很大、需要社区检测和可视化，可以直接用 Graphify 读取我们的 graph.json（格式兼容），不需要改任何东西。
