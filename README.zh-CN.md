# LLM Wiki

> 跨设备、跨 Agent 的个人知识操作系统

把原始资料 — 文章、论文、截图、音频、URL — 丢进 `raw/`，你的 AI Agent 自动阅读、摘要、关联概念，维护一个结构化的 Markdown 知识库。像第二大脑一样查询它，定期体检保持健康，回顾它看知识如何生长。

基于 [Karpathy 的 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 概念，扩展了多 Agent 协同、知识图谱、以及编程之外的全生活领域覆盖。

## 架构

```
raw/          → 原始资料（只读，Agent 不修改）
wiki/         → 结构化 Markdown 知识库（Agent 写入和维护）
graph/        → 知识图谱（可选，Graphify 驱动）
schema/       → Schema 定义和平台 Mapper
```

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  设备 A      │     │  设备 B      │     │  设备 C      │
│  Claude Code │     │  OpenClaw    │     │  Cursor      │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       └───────────┬───────┴───────────────────┘
                   │
            ┌──────▼──────┐
            │   Git 仓库   │
            └─────────────┘
```

每个 Agent 通过各自平台的机制读取同一份规范：

| 平台 | Mapper 文件 |
|---|---|
| Claude Code | `CLAUDE.md` |
| Cursor | `schema/.cursor/rules/wiki.mdc` |
| Codex / OpenClaw / Aider | `AGENTS.md` |

## 四个核心操作

### 摄入（Ingest）

把文件放进 `raw/`，告诉 Agent 处理。Agent 会：

1. 在 `wiki/sources/` 创建摘要页
2. 创建或更新 `wiki/concepts/` 和 `wiki/entities/` 页面
3. 更新 `wiki/index.md` 和 `wiki/log.md`

一篇资料可能涉及 5–15 个 wiki 页面的创建或更新。

### 查询（Query）

向 Agent 提问。它先读 `wiki/index.md` 定位相关页面，深入阅读后用 `[[wiki-link]]` 引用回答。有价值的回答会存为 `wiki/outputs/` 页面。

### 健康检查（Lint）

三个级别：

- **轻量** — 坏链、孤立页面、索引一致性（确定性脚本，零 token）
- **深度** — 矛盾检测、过时信息、stub 补全、缺失概念（LLM Agent）
- **生长** — 跨页面关联发现、知识缺口、综述建议（定期执行）

### 回顾（Review）

定期自动生成知识回顾 — 周报、月度综述、年度总结 — 存入 `wiki/journal/`。

## 快速开始

### 1. 克隆

```bash
git clone git@github.com:yuanchuziwen/llm-wiki-template.git ~/llm-wiki
cd ~/llm-wiki
```

### 2. 用你的 Agent 打开

```bash
# Claude Code
cd ~/llm-wiki && claude

# 或者用 Cursor / 其他 Agent 打开
```

首次启动时，Agent 会自动检测本地环境、检查工具依赖，并写入 `.local/env.json`（不同步 — 每台设备独立）。

### 3. 必装工具

| 工具 | 用途 | 安装 |
|---|---|---|
| Git | 版本控制和同步 | `xcode-select --install` |
| ripgrep | Agent 搜索底层工具 | `brew install ripgrep` |

### 4. 推荐工具

| 工具 | 用途 | 安装 |
|---|---|---|
| [Obsidian](https://obsidian.md) | 浏览 wiki（`wiki/` 目录直接作为 vault） | `brew install --cask obsidian` |
| Pandoc | 格式转换 | `brew install pandoc` |
| [Jina Reader](https://r.jina.ai) | URL → Markdown | 免费 API，无需安装 |

### 5. 开始摄入

```
> 我在 raw/articles/ 放了一篇文章，帮我 ingest。
```

## Wiki 页面格式

所有页面使用 YAML frontmatter + Markdown + `[[wiki-links]]`：

```markdown
---
title: LLM Wiki
type: concept
created: 2026-04-12
tags: [AI, knowledge-management]
status: active
---

## 定义
...

## 来源
- [[sources/karpathy-gist]]

## 关联概念
- [[concepts/knowledge-graph]]
```

页面类型：`concept` | `entity` | `source` | `output` | `area` | `journal`

## 多模态输入

| 输入类型 | 处理方式 |
|---|---|
| Markdown / 纯文本 | 直接读取 |
| PDF | 提取文本 |
| 图片 | Vision 模型识别 |
| 音频 / 视频 | Whisper 转录 |
| URL | Jina Reader → Markdown |

## 跨设备同步

Git 是同步层。每次 Agent 会话：
- **开始时**：`git pull --rebase`
- **结束时**（有变更）：`git commit` + `git push`

冲突在设计上就很少发生（一概念一文件、日志 append-only）。万一发生，Agent 语义合并。

## 项目结构

```
llm-wiki/
├── CLAUDE.md                    # Claude Code Agent 操作手册
├── AGENTS.md                    # Codex / OpenClaw / Aider 操作手册
├── raw/                         # 原始资料（只读）
│   ├── articles/
│   ├── papers/
│   ├── books/
│   ├── screenshots/
│   ├── audio/
│   ├── clippings/
│   └── misc/
├── wiki/                        # 结构化知识库（Agent 维护）
│   ├── index.md                 # 全局目录
│   ├── log.md                   # 操作日志
│   ├── concepts/
│   ├── entities/
│   ├── sources/
│   ├── outputs/
│   ├── areas/
│   └── journal/
├── graph/                       # 知识图谱（可选）
├── schema/
│   ├── wiki-schema.yml          # Single Source of Truth
│   └── .cursor/rules/wiki.mdc  # Cursor Mapper
└── .local/                      # 设备本地环境（不同步）
    └── env.json
```

## 灵感来源

- [Karpathy 的 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — 原始概念
- [Graphify](https://github.com/safishamsi/graphify) — 知识图谱引擎，wiki 导出，多平台支持

## License

MIT
