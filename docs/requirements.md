# LLM Wiki — 需求文档

> 跨设备、跨 Agent 的个人知识操作系统

## 一、背景与动机

Andrej Karpathy 提出 LLM Wiki 概念：用 LLM 作为知识管理员，自动将零散资料整理为结构化的可查询知识库。其核心洞察：

1. 人类擅长**收集**资料，不擅长**组织**资料
2. LLM 擅长阅读、摘要、关联，可以承担组织工作
3. 纯 Markdown + 本地文件 = 数据主权 + 工具无关性

但 Karpathy 只给出了抽象框架，未解决以下问题：
- 多设备、多 Agent 工具之间如何协同
- 非编程场景（生活、阅读、健康、财务）如何覆盖
- Lint 操作如何从「单次调用」升级为「持续演进的 Agent」
- 知识图谱与 wiki 如何互补

本项目的目标：**在 Karpathy 框架基础上，构建一个真正可用的、跨平台的个人知识操作系统。**

---

## 二、核心诉求

### 诉求 1：跨设备、跨 Agent

**现状**：用户在不同设备上使用不同的 AI 工具：
- 设备 A：Cursor + Claude Code
- 设备 B：OpenClaw
- 未来可能：Codex、Gemini CLI、Aider 等

**要求**：
- 所有 Agent 读写同一份 wiki，知识不因工具切换而丢失
- 每个 Agent 通过各自平台的机制感知 wiki（CLAUDE.md / .cursor/rules / AGENTS.md）
- 同步机制可靠，冲突可控

### 诉求 2：不局限于编程，普适性工具

**要求**：wiki 覆盖个人知识的所有维度：

| 领域 | 示例 |
|---|---|
| 技术 | 架构设计、源码分析、最佳实践 |
| 阅读 | 书籍笔记、论文摘要、文章剪藏 |
| 工作 | 项目进展、会议纪要、决策记录 |
| 生活 | 健身计划、饮食记录、旅行攻略 |
| 财务 | 投资笔记、消费分析 |
| 学习 | 课程笔记、语言学习、技能提升 |
| 人脉 | 重要联系人、社交记录 |
| 思考 | 个人反思、灵感记录、价值观梳理 |

wiki 不是代码工具的附庸，而是**个人第二大脑**。

### 诉求 3：满足并超越 Karpathy 构想

**Karpathy 框架（基线）**：
- 三层架构：Raw → Wiki → Schema
- 三个操作：Ingest / Query / Lint
- 两个导航文件：index.md / log.md

**超越方向**：

| 维度 | Karpathy | 本项目目标 |
|---|---|---|
| 平台 | 单 Agent | 多 Agent 协同 |
| 领域 | 隐含偏向编程 | 全生活域 |
| 输入 | 手动放文件 | 多渠道自动采集 |
| 知识结构 | 扁平 wiki | wiki + 知识图谱双模态 |
| Lint | 单次 LLM 调用 | 多步 Agent + 定期调度 |
| 输出 | 纯查询 | 查询 + 综述生成 + 知识导出 |
| 演化 | 静态 | 知识自动生长（Agent 主动发现关联） |

---

## 三、系统架构

### 3.1 三层架构（继承 Karpathy）

```
project-root/
├── raw/                    ← 原始资料层（只读，LLM 不改）
│   ├── articles/           ← 文章、博客
│   ├── papers/             ← 论文
│   ├── books/              ← 书籍笔记
│   ├── screenshots/        ← 截图、照片
│   ├── audio/              ← 录音、播客
│   ├── clippings/          ← 网页剪藏
│   └── misc/               ← 其他
│
├── wiki/                   ← Wiki 层（LLM 写和维护）
│   ├── index.md            ← 全局目录
│   ├── log.md              ← 操作日志
│   ├── concepts/           ← 概念页
│   ├── entities/           ← 实体页（人物、项目、工具）
│   ├── sources/            ← 原始资料摘要页
│   ├── outputs/            ← 查询产出（综述、对比、分析）
│   ├── areas/              ← 生活领域页（健身、财务、阅读等）
│   └── journal/            ← 时间线（周报、月度回顾）
│
├── graph/                  ← 知识图谱层（可选，增强）
│   ├── graph.json          ← 结构化图谱（Graphify 生成）
│   └── GRAPH_REPORT.md     ← 图谱摘要
│
└── schema/                 ← Schema 层（规范和配置）
    ├── CLAUDE.md           ← Claude Code 规范
    ├── AGENTS.md           ← Codex / OpenClaw / Aider 规范
    ├── .cursor/rules/      ← Cursor 规范
    └── wiki-schema.yml     ← wiki 结构定义、命名规范、工作流
```

### 3.2 跨平台同步层

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  设备 A      │     │  设备 B      │     │  设备 C      │
│  Cursor + CC │     │  OpenClaw   │     │  Codex      │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────┬───────┴───────────────────┘
                   │
            ┌──────▼──────┐
            │   Git Repo   │
            │  (私有仓库)   │
            └─────────────┘
```

**同步协议**：
- 每次 Agent 会话开始：`git pull --rebase`
- 每次 Agent 会话结束（有写入时）：`git add + commit + push`
- 冲突策略：见第五节

### 3.3 Schema 注入机制

每个 Agent 平台通过各自机制读取 schema：

| 平台 | 注入方式 | 文件 |
|---|---|---|
| Claude Code | 项目根 CLAUDE.md | `schema/CLAUDE.md` |
| Cursor | alwaysApply rules | `schema/.cursor/rules/wiki.mdc` |
| OpenClaw | AGENTS.md | `schema/AGENTS.md` |
| Codex | AGENTS.md | `schema/AGENTS.md` |
| Aider | AGENTS.md | `schema/AGENTS.md` |

所有平台的 schema **内容一致**，只是注入格式不同。维护一份 `wiki-schema.yml` 作为 single source of truth，通过脚本生成各平台文件。

---

## 四、核心操作

### 4.1 Ingest（摄入）

**触发方式**：
- 手动：用户将文件放入 `raw/` 并告知 Agent
- 半自动：Obsidian Web Clipper / Jina Reader 剪藏到 `raw/clippings/`
- 自动：Git hook 检测 `raw/` 新增文件，提示 Agent 处理

**流程**：
1. Agent 读取原始资料
2. 与用户讨论要点（可选，可配置为全自动）
3. 在 `wiki/sources/` 创建摘要页（YAML frontmatter + 摘要 + 关键概念 + 引用）
4. 更新/创建涉及的 `concepts/` 和 `entities/` 页面
5. 更新 `wiki/index.md`
6. 追加 `wiki/log.md`
7. 如果启用图谱：增量更新 `graph/graph.json`

**多模态支持**：

| 输入类型 | 处理方式 |
|---|---|
| Markdown / 纯文本 | 直接阅读 |
| PDF | 提取文本 + 引用挖掘 |
| 图片 / 截图 | Vision 模型识别 |
| 音频 / 视频 | Whisper 转录 → 文本处理 |
| URL | Jina Reader 转 Markdown → 文本处理 |

### 4.2 Query（查询）

**流程**：
1. Agent 先读 `wiki/index.md` 定位相关页面
2. 深入阅读相关页面
3. 如果启用图谱：查询 `graph.json` 发现隐含关联
4. 综合回答，引用具体 wiki 页面
5. 有价值的回答存为 `wiki/outputs/` 新页面
6. 更新 `wiki/index.md` 和 `wiki/log.md`

**查询增强**（超越 Karpathy）：
- **路径查询**：两个概念之间的关联链路（借鉴 Graphify 的 `path` 命令）
- **社区发现**：自动发现知识聚类（借鉴 Graphify 的 Leiden 社区检测）
- **时间线查询**：按时间维度回溯知识演化
- **跨领域关联**：发现不同生活领域之间的意外联系

### 4.3 Lint（健康检查）

这是最关键也最容易做差的操作。**必须设计为多步 Agent，而非单次 LLM 调用。**

**检查项**：

| 类别 | 检查内容 | 实现方式 |
|---|---|---|
| 结构完整性 | 坏链检测（引用了不存在的页面） | 确定性脚本，零 token |
| 结构完整性 | 孤立页面（无任何入链） | 确定性脚本，零 token |
| 结构完整性 | index.md 与实际文件的一致性 | 确定性脚本，零 token |
| 内容质量 | 页面之间的矛盾检测 | LLM Agent |
| 内容质量 | 过时信息标记（新资料覆盖旧结论） | LLM Agent |
| 知识生长 | 提到但未建页的概念 → 自动创建 | LLM Agent |
| 知识生长 | 发现跨页面的隐含关联 → 自动补充 | LLM Agent |
| 知识生长 | 信息缺口识别 → 建议用户补充 | LLM Agent |

**执行策略**：
- **轻量 lint**：每次 ingest 后自动执行结构完整性检查（确定性脚本，秒级）
- **深度 lint**：用户主动触发或定期执行（LLM Agent，分钟级）
- **生长 lint**：周级/月级，Agent 主动发现关联、生成综述、建议扩展方向

### 4.4 Review（定期回顾）— 新增操作

**超越 Karpathy 的第四个操作**：定期自动生成知识回顾。

- **周报**：本周新增了什么知识、哪些领域活跃、哪些沉寂
- **月度综述**：跨领域的知识关联发现、知识版图变化
- **年度总结**：个人知识资产盘点

存入 `wiki/journal/`，也是一种特殊的 Query 输出。

---

## 五、冲突与一致性策略

### 5.1 设计原则：从结构上避免冲突

| 文件类型 | 写入模式 | 冲突概率 |
|---|---|---|
| `wiki/sources/*.md` | 一资料一文件，创建后少改 | 极低 |
| `wiki/concepts/*.md` | 一概念一文件，多 Agent 可能更新同一概念 | 低 |
| `wiki/log.md` | Append-only | Git auto-merge 可解决 |
| `wiki/index.md` | Append-only 为主 | Git auto-merge 可解决 |
| `graph/graph.json` | 整体替换 | 需特殊处理 |

### 5.2 冲突解决策略

**Level 1 — Git auto-merge**（大多数情况）
- 不同文件的修改：自动合并，零冲突
- 同一文件不同位置的修改：Git auto-merge 解决

**Level 2 — LLM 自动 resolve**（少数情况）
- 同一文件同一位置的修改：Agent 读取冲突内容，理解双方语义，合并
- 对于 Markdown 知识文件，LLM resolve 的准确率很高

**Level 3 — 人工介入**（极少数情况）
- LLM 无法判断的冲突：标记为待解决，下次用户会话时提示

### 5.3 graph.json 的特殊处理

graph.json 是二进制式的整体文件，不适合 Git 文本合并。策略：
- 只在一台设备上生成/更新图谱（推荐主力设备）
- 其他设备只读
- 或：将图谱拆分为 nodes.jsonl + edges.jsonl（append-friendly）

---

## 六、多渠道采集

### 6.1 采集工具矩阵

| 渠道 | 工具 | 输出格式 | 落地位置 |
|---|---|---|---|
| 网页文章 | Obsidian Web Clipper / MarkDownload | Markdown | `raw/clippings/` |
| 任意 URL | Jina Reader（r.jina.ai） | Markdown | `raw/clippings/` |
| 学术论文 | Zotero | PDF + BibTeX | `raw/papers/` |
| Kindle / 微信读书 | Readwise | Markdown | `raw/books/` |
| 语音想法 | 微信输入法 / 系统录音 | 文本 / 音频 | `raw/audio/` |
| 微信聊天 / 收藏 | 手动导出或 OpenClaw 辅助 | Markdown | `raw/misc/` |
| 截图 / 照片 | 直接放入 | 图片 | `raw/screenshots/` |
| 播客 / 视频 | yt-dlp + Whisper | 转录文本 | `raw/audio/` |

### 6.2 自动采集 Pipeline（进阶）

```
采集源 → raw/ → Git commit → Agent 检测新文件 → 自动 Ingest
```

可通过 Git hook 或 cron job 实现半自动化。

---

## 七、工具选型

### 7.1 必装

| 工具 | 用途 | 安装方式 |
|---|---|---|
| Git | wiki 版本控制 + 跨设备同步 | 系统自带 |
| Obsidian | wiki 浏览和手动编辑 | 官网下载 |
| ripgrep (rg) | Agent 搜索底层工具 | `brew install ripgrep` |
| 至少一个 LLM Agent | 写入和维护 wiki | Claude Code / Cursor / OpenClaw 等 |

### 7.2 推荐

| 工具 | 用途 | 安装方式 |
|---|---|---|
| Obsidian Web Clipper | 网页一键剪藏 | 浏览器扩展 |
| Jina Reader | URL → Markdown | 免费 API |
| Graphify | 知识图谱生成 | `pip install graphifyy` |

### 7.3 按需

| 工具 | 用途 | 何时安装 |
|---|---|---|
| qmd | 语义搜索 | wiki 积累到几百篇后 |
| Zotero | 论文管理 | 有学术需求时 |
| Readwise | 阅读标注同步 | 有 Kindle/微信读书需求时 |
| Pandoc | 多格式导出 | 需要导出 PDF/HTML 时 |

---

## 八、Wiki 页面规范

### 8.1 Frontmatter 标准

```yaml
---
title: 页面标题
type: concept | entity | source | output | area | journal
tags: [tag1, tag2]
created: 2026-04-12
updated: 2026-04-12
sources: [raw/articles/xxx.md]  # 引用的原始资料
related: [concepts/yyy.md]      # 关联页面
status: active | stale | stub   # 页面状态
---
```

### 8.2 页面模板

**Source 页**（原始资料摘要）：
```markdown
---
title: 《文章标题》
type: source
tags: [AI, knowledge-management]
created: 2026-04-12
sources: [raw/articles/xxx.md]
---

## 摘要
一段话概括核心内容。

## 关键要点
- 要点 1
- 要点 2

## 相关概念
- [[concepts/llm-wiki]] — 本文讨论的核心概念
- [[entities/karpathy]] — 作者

## 原文引用
> 重要原文摘录
```

**Concept 页**（概念）：
```markdown
---
title: LLM Wiki
type: concept
tags: [AI, knowledge-management]
created: 2026-04-12
updated: 2026-04-12
---

## 定义
一句话定义。

## 详细说明
展开描述。

## 来源
- [[sources/karpathy-llm-wiki]] — 原始提出
- [[sources/graphify-readme]] — 工程化实现

## 关联概念
- [[concepts/rag]] — 对比：RAG vs LLM Wiki
- [[concepts/knowledge-graph]] — 互补方案
```

### 8.3 index.md 格式

```markdown
# Wiki Index

> 最后更新：2026-04-12 | 共 N 个页面

## Concepts
- [[concepts/llm-wiki]] — LLM 驱动的个人知识管理系统
- [[concepts/knowledge-graph]] — 实体和关系的结构化表示

## Entities
- [[entities/karpathy]] — AI 研究者，LLM Wiki 概念提出者

## Sources
- [[sources/karpathy-gist]] — Karpathy 的 LLM Wiki 原始文档

## Areas
- [[areas/fitness]] — 健身与增肌
- [[areas/reading]] — 阅读记录

## Outputs
- [[outputs/llm-wiki-vs-rag]] — LLM Wiki 与 RAG 的对比分析

## Journal
- [[journal/2026-W15]] — 2026 年第 15 周回顾
```

### 8.4 log.md 格式

```markdown
# Wiki Log

## [2026-04-12] ingest | Karpathy LLM Wiki Gist
- 新增 sources/karpathy-gist.md
- 新增 concepts/llm-wiki.md
- 新增 entities/karpathy.md
- 更新 index.md

## [2026-04-12] query | LLM Wiki vs RAG 对比
- 新增 outputs/llm-wiki-vs-rag.md
- 更新 index.md
```

---

## 九、里程碑

### Phase 0：骨架搭建
- 创建目录结构
- 编写 wiki-schema.yml
- 生成各平台 schema 文件（CLAUDE.md / AGENTS.md / .cursor/rules）
- 初始化 Git 仓库

### Phase 1：单设备 MVP
- 在一台设备上完成 Ingest / Query / Lint 闭环
- 手动放入 3-5 篇资料，验证 wiki 生成质量
- 验证 Obsidian 浏览体验

### Phase 2：跨设备同步
- 推送到 Git 远端（私有仓库）
- 在第二台设备上克隆并配置 Agent
- 验证双设备读写 + 同步
- 实现冲突自动解决

### Phase 3：采集增强
- 接入 Obsidian Web Clipper
- 接入 Jina Reader
- 实现半自动 Ingest pipeline

### Phase 4：知识图谱
- 集成 Graphify，生成 graph.json
- 实现图谱增强的 Query
- wiki + 图谱双模态检索

### Phase 5：自动化运维
- 定期 Lint 调度（cron / Git hook）
- 自动 Review（周报 / 月度综述）
- 知识生长：Agent 主动发现关联和缺口

---

## 十、开放问题

| # | 问题 | 备注 |
|---|---|---|
| 1 | wiki 仓库是独立 Git 仓库，还是嵌入到某个项目中？ | 建议独立仓库 |
| 2 | raw/ 是否也纳入 Git？大文件（PDF/图片/音频）如何处理？ | Git LFS 或 .gitignore 大文件 |
| 3 | 是否需要加密？个人敏感信息（财务、健康）的安全性 | git-crypt 或 private repo |
| 4 | token 成本预估？大量资料 ingest 的成本控制策略 | AST 优先 + 缓存 + 增量更新 |
| 5 | Obsidian vault 和 wiki/ 目录是同一个，还是 Obsidian 单独管理？ | 建议 wiki/ 即 vault |
| 6 | 多人协作？是否考虑家庭/团队共享 wiki？ | MVP 先做单人 |

---

## 参考资料

1. [Karpathy LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — 原始框架
2. [Graphify](https://github.com/safishamsi/graphify) — 22.5k star 知识图谱工具，支持 wiki 导出
3. [量子位报道](https://www.qbitai.com/2026/04/396983.html) — Graphify 介绍，71.5x token 优化
4. [搬砖的小明](https://www.xiaoming.io/llm-wiki-practice/) — LLM Wiki 实测，指出 Lint 是核心难点
5. 知乎工具清单文章 — 实操版工具矩阵 + 可复制 prompt
