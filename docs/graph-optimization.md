# 知识图谱优化：从 Graphify 源码中学到的

> 基于对 [Graphify](https://github.com/safishamsi/graphify) 全部源码的逐文件深度阅读，提炼出对 LLM Wiki 图谱的优化方向。

---

## 一、当前问题

第一次 Ingest 后，`graph.json` 中的边只有粗粒度的结构性关系：

```json
{ "source": "cat-system", "target": "cr-allocation-mechanism", "relation": "核心概念" }
{ "source": "banma-education", "target": "banma-cat-org-arch", "relation": "来源" }
{ "source": "ai-consultant", "target": "interview-prep-with-ai", "relation": "案例" }
```

这些关系和 wiki 页面里的 `[[wiki-link]]` 高度重复——本质上都是"A 和 B 有关联"，没有回答"什么关联"。

**图谱的核心价值不在于记录"有关联"，而在于记录"什么样的关联"。**

---

## 二、Graphify 的设计哲学

### 2.1 关系类型：自由文本 + 示例引导

Graphify **没有**预定义一个关系类型的枚举列表。它在 LLM prompt 中给了一组示例（`calls`、`implements`、`references`、`cites`、`conceptually_related_to`、`semantically_similar_to`、`rationale_for`），但明确允许 LLM 自由填写。

实际输出中出现过：`contains`、`uses`、`inherits`、`method`、`referenced`、`semantic_similarity` 等各种类型——LLM 根据内容自行判断最合适的关系描述。

**设计原因**：知识域多样，限死枚举会很快不够用。引导而不约束。

### 2.2 三级置信度

每条边有一个 `confidence` 字段（枚举）+ 一个 `confidence_score` 字段（浮点数）：

| 级别 | 含义 | 默认分数 | 示例 |
|---|---|---|---|
| `EXTRACTED` | 原文明确提到的关系 | 1.0 | import 语句、函数调用、明确引用 |
| `INFERRED` | 从上下文合理推断的关系 | 0.6–0.9 | 共享数据结构、隐含依赖、同一篇文档中讨论 |
| `AMBIGUOUS` | 不确定的关系，标记待审 | 0.1–0.3 | 可能相关但证据不足 |

**设计原因**：
- 让 Query 时可以优先走高置信度边
- 让 Lint 可以专门审核 AMBIGUOUS 边
- 可视化时用不同样式区分（实线 vs 虚线）

### 2.3 惊喜连接分析

`analyze.py` 中有一个 **surprising connections** 算法，用复合得分找到"意外"的关联：

- 跨社区的边得分更高（不同知识领域之间的联系）
- 跨文件类型的边得分更高（代码 ↔ 文档之间的联系）
- AMBIGUOUS 和 INFERRED 边得分更高（明确的关系不算"惊喜"）
- 低度数节点连接到高度数节点的边得分更高（边缘知识连接到核心知识）

**设计原因**：帮助用户发现自己没意识到的知识关联——这才是图谱超越简单 wiki-link 的独特价值。

### 2.4 知识缺口识别

Graphify 将**低度数节点**（degree ≤ 1 且没有 source_location）标记为知识缺口——这些是提到过但缺乏充分信息的概念。

### 2.5 Query 记忆反馈循环

`ingest.py` 中有一个精妙的设计：Query 的问答结果会被保存为 `.md` 文件，在下次 `--update` 时作为输入被提取进图谱。这样，过去的提问和回答本身成为了知识图谱的一部分——**问答产生新知识**。

对应到我们的 wiki：`wiki/outputs/` 页面在下次 Ingest 时也应该被纳入图谱节点。

---

## 三、优化方案

### 3.1 语义化关系类型

**改动**：`relation` 字段从粗粒度描述词改为有语义区分度的自由文本，schema 中给一组参考类型引导 Agent。

参考关系类型：

| 类别 | 参考关系 | 适用场景 |
|---|---|---|
| **结构性** | `组成部分`、`属于`、`包含` | A 是 B 的一部分 |
| **因果性** | `导致`、`解决`、`驱动` | A 导致了 B 的出现 |
| **对比性** | `替代方案`、`对比`、`互补` | A 和 B 解决同一问题但方式不同 |
| **来源性** | `提出`、`创建`、`贡献` | A（人/组织）创建了 B |
| **演化性** | `演化为`、`升级`、`取代` | A 发展成了 B |
| **应用性** | `应用于`、`实践`、`案例` | A 在 B 场景中被使用 |
| **依赖性** | `依赖`、`前置条件`、`基于` | A 需要 B 才能工作 |
| **关联性** | `相关`、`类似`、`跨域关联` | 弱关联兜底，鼓励升级为更精确的类型 |

**规则**：Agent 可以自创关系类型，不限于以上列表。但应尽量使用语义明确的描述，避免使用"来源"、"文档"、"核心概念"这种不携带信息的词。

### 3.2 引入置信度

**改动**：边增加 `confidence` 字段。

```json
{
  "source": "llm-wiki",
  "target": "rag",
  "relation": "替代方案",
  "confidence": "EXTRACTED",
  "source_file": "sources/karpathy-llm-wiki.md"
}
```

| 级别 | 含义 | 何时使用 |
|---|---|---|
| `EXTRACTED` | wiki 页面中明确写了这个关系 | `[[wiki-link]]`、frontmatter `related`、正文明确描述 |
| `INFERRED` | Agent 从内容理解中推断 | 两个概念在同一篇资料中被讨论但没有直接互引 |
| `AMBIGUOUS` | 不确定的关联 | Agent 觉得可能相关但不太确定 |

**应用**：
- Query 时优先走 EXTRACTED 边
- Lint 生长级审核 AMBIGUOUS 边，决定升级或删除
- GRAPH_REPORT.md 单独列出 AMBIGUOUS 边

### 3.3 graph.json 格式升级

**节点**（不变）：

```json
{
  "id": "llm-wiki",
  "label": "LLM Wiki",
  "type": "concept",
  "wiki_path": "concepts/llm-wiki.md",
  "description": "LLM 驱动的个人知识管理系统"
}
```

**边**（新增 `confidence` 字段）：

```json
{
  "source": "andrej-karpathy",
  "target": "llm-wiki",
  "relation": "提出",
  "confidence": "EXTRACTED",
  "source_file": "sources/karpathy-llm-wiki.md"
}
```

**对比改进前后**：

| 改进前 | 改进后 |
|---|---|
| `"relation": "核心概念"` | `"relation": "组成部分", "confidence": "EXTRACTED"` |
| `"relation": "来源"` | `"relation": "创建", "confidence": "EXTRACTED"` |
| `"relation": "出自"` | `"relation": "提出", "confidence": "EXTRACTED"` |
| `"relation": "案例"` | `"relation": "应用于", "confidence": "INFERRED"` |
| （无） | `"relation": "类似", "confidence": "INFERRED"` ← 推断出的跨页面关联 |

### 3.4 GRAPH_REPORT.md 增强

在现有的核心节点、孤立节点、最近更新基础上，增加：

**跨领域关联**：列出连接不同 `type` 或不同 `area` 的边，帮助发现意外联系。

```markdown
## 跨领域关联

| 从 | 到 | 关系 | 置信度 |
|----|----|----|--------|
| AI 顾问系统 (concept) | 面试备考 (area) | 应用于 | INFERRED |
| C/R 分配机制 (concept) | 地区大拆 (concept) | 驱动 | EXTRACTED |
```

**待审关系**：AMBIGUOUS 置信度的边，供 Lint 审核。

```markdown
## 待审关系（AMBIGUOUS）

- cat-system → interview-prep-with-ai: "间接相关" — 需确认是否有直接联系
```

**知识缺口**：度数 ≤ 1 的节点，可能是信息不足的 stub。

```markdown
## 知识缺口（低连接度节点）

- [[concepts/xxx]] — 仅 1 条关联，可能需要更多资料补充
```

### 3.5 MCP Server 增强

现有 6 个工具不变，增加查询能力：

- `get_neighbors` 增加可选 `confidence` 参数：只返回指定置信度以上的边
- `graph_stats` 增加置信度分布统计

### 3.6 outputs 页面纳入图谱

`wiki/outputs/` 中的 Query 产出页面也应该被纳入图谱节点（type 标记为 output），它们引用的 wiki 页面作为边。这样 Query 的产出本身成为知识图谱的一部分——下次查询时可以参考之前的分析结论。

---

## 四、不采纳的 Graphify 设计

| Graphify 特性 | 不采纳原因 |
|---|---|
| AST 提取 | 我们的输入是 Markdown 不是代码 |
| Hyperedge（超边） | 前期没必要，多节点关系用两两边表达 |
| Watch mode | wiki 变更通过 Agent Ingest 触发，不需要文件监听 |
| Rationale 节点 | 代码注释提取，wiki 不需要 |
| 可视化 HTML | 前期不需要，wiki 在 Obsidian 里浏览 |
| Obsidian 导出 | wiki 本身就是 Obsidian 兼容的 Markdown |
| Neo4j 推送 | 前期不需要图数据库 |
| `confidence_score` 浮点数 | 三级枚举足够，精确到小数点没有实际意义 |
| `file_type` 字段 | 我们已有 `type`（concept/entity/source/area），不需要代码的文件类型 |
| Community label 自动命名 | 我们有 `areas/` 做手动分类，前期不需要自动社区 |

---

## 五、实施优先级

### 立即可做（schema 和 prompt 层面的变化）

- [x] 更新 `wiki-schema.yml`：graph.json 边增加 `confidence` 字段定义
- [x] 更新 `wiki-schema.yml`：添加参考关系类型列表
- [x] 更新 `CLAUDE.md` / `AGENTS.md`：引导 Agent 使用语义化关系和置信度
- [x] 更新 `tools/graph-server.py`：`get_neighbors` 支持 confidence 过滤
- [ ] 更新现有 `graph.json`：给已有边补充 `confidence: "EXTRACTED"`（当前 graph.json 为空，下次 Ingest 时自动生效）

### 下次 Lint 时验证

- [ ] 检查新 Ingest 产生的关系是否语义化
- [ ] 检查是否有 INFERRED 和 AMBIGUOUS 边产生
- [ ] 审核 AMBIGUOUS 边是否合理

### 后续可做

- [ ] GRAPH_REPORT.md 增加跨领域关联、待审关系、知识缺口板块
- [ ] outputs 页面纳入图谱节点
- [ ] 社区检测（当 wiki 规模超过 100 页时再考虑）

---

## 六、参考

- [Graphify extract.py](https://github.com/safishamsi/graphify/blob/main/graphify/extract.py) — AST + LLM 双路提取
- [Graphify analyze.py](https://github.com/safishamsi/graphify/blob/main/graphify/analyze.py) — 惊喜连接、知识缺口
- [Graphify validate.py](https://github.com/safishamsi/graphify/blob/main/graphify/validate.py) — 数据校验规范
- [Graphify serve.py](https://github.com/safishamsi/graphify/blob/main/graphify/serve.py) — MCP Server 7 个工具
- [Graphify skill.md](https://github.com/safishamsi/graphify/blob/main/graphify/skill.md) — LLM 提取 prompt（关系类型示例、置信度规则）
- [Graphify ingest.py](https://github.com/safishamsi/graphify/blob/main/graphify/ingest.py) — Query 记忆反馈循环
