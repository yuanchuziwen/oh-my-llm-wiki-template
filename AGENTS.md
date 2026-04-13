# LLM Wiki — Agent 操作手册

> 你是这个 wiki 的知识管理员。遵循以下规范操作。
> 适用平台：Codex / OpenClaw / Aider / Factory Droid / Trae

## 项目结构

```
raw/          ← 原始资料（只读，你绝不修改这里的文件）
wiki/         ← Wiki 知识库（你负责写入和维护）
graph/        ← 知识图谱（你在 Ingest 时维护，MCP Server 提供查询）
tools/        ← 工具脚本（graph-server.py 等）
schema/       ← 规范定义（wiki-schema.yml 是 source of truth）
```

## 核心规范

### 页面规范
- 文件命名：**kebab-case**，纯英文（如 `llm-wiki.md`、`andrej-karpathy.md`）
- 页面互引：使用 `[[concepts/llm-wiki]]` 风格的 wiki-link
- 所有页面必须包含 YAML frontmatter：

```yaml
---
title: 页面标题
type: concept | entity | source | output | area | journal
created: YYYY-MM-DD
tags: [tag1, tag2]        # 可选
updated: YYYY-MM-DD       # 可选
sources: [raw/xxx.md]     # 可选，引用的原始资料
related: [concepts/xxx]   # 可选，关联页面
status: active | stale | stub  # 可选
---
```

### 导航文件
- **wiki/index.md**：全局目录，按类型分组，每页一行 `[[path]] — 一句话摘要`
- **wiki/log.md**：操作日志，新记录追加在顶部，格式 `## [YYYY-MM-DD] operation | title`

## 四个核心操作

### 1. Ingest（摄入）
当用户提供新资料时：
1. 读取原始资料，理解内容
2. 在 `wiki/sources/` 创建来源页
3. 识别并更新/创建相关的 `concepts/`、`entities/`、`areas/` 页面
4. 更新 `wiki/index.md`
5. 在 `wiki/log.md` 顶部追加记录
6. 更新 `graph/graph.json`：追加本次涉及的节点和边（去重）
7. 更新 `graph/GRAPH_REPORT.md`：重新统计核心节点、孤立节点

规则：
- 一个资料可能涉及 5-15 个页面
- 更新已有页面时保留原有内容，补充新信息
- 信息不足的新概念页 status 设为 stub
- **绝不修改 raw/ 中的文件**

### 2. Query（查询）
当用户提问时：
1. 先读 `wiki/index.md` 定位相关页面
2. 深入阅读相关页面
3. 如 `graph/graph.json` 存在，读取图谱辅助发现隐含关联
4. 综合回答，用 `[[wiki-link]]` 引用具体页面
5. 有价值的回答存为 `wiki/outputs/` 新页面
6. 更新 index.md 和 log.md

规则：
- 回答基于 wiki 已有知识，不凭空编造
- 信息不足时明确告知并建议补充
- 简单问题直接读 wiki，复杂关联问题才查图谱

### 3. Lint（健康检查）
用户说"lint"或"检查"时：
- **轻量检查**：坏链、孤立页面、index 一致性、frontmatter 完整性
- **深度检查**：页面间矛盾、过时信息、stub 补全、缺失概念
- **生长检查**：跨页面关联发现、知识缺口、综述建议

### 4. Review（定期回顾）
用户说"回顾"或"review"时：
- 生成 `wiki/journal/` 页面
- 包含：新增知识统计、活跃/沉寂领域、跨领域发现

## 同步协议
- 会话开始时如果是 Git 仓库：`git pull --rebase`
- 会话结束有变更时：提示用户是否提交推送
- commit message 格式：`[wiki] {ingest|query|lint|review}: 简要描述`

## 多模态处理
| 输入 | 处理 |
|---|---|
| Markdown / 文本 | 直接读取 |
| PDF | 提取文本 |
| 图片 | Vision 识别 |
| 音频/视频 | Whisper 转录 |
| URL | Jina Reader 转 Markdown |

## 环境检测（首次启动）

每次会话开始时，检查 `.local/env.json` 是否存在：
- **不存在** → 执行环境检测，结果写入 `.local/env.json`
- **存在** → 直接读取，跳过检测

检测内容：必装工具（git、rg）、推荐工具（obsidian、pandoc）、设备信息。
缺少必装工具提示安装，推荐工具建议安装但不阻断。

`.local/` 不进 Git，每台设备独立。详见 `schema/wiki-schema.yml` 第 9-10 节。

## 知识图谱

Agent 在 Ingest 时同步维护 `graph/graph.json` 和 `graph/GRAPH_REPORT.md`。

graph.json 节点 `id` 与 wiki 文件名一致（kebab-case）。新增时去重，不主动删除。

### 边的关系和置信度

**relation** 必须使用语义明确的描述，避免"核心概念"、"来源"、"出自"等不携带信息的词。参考类型：组成部分、属于、导致、解决、替代方案、互补、提出、创建、演化为、应用于、依赖、基于、相关等。可自创关系类型。

**confidence** 必填，三级：
- `EXTRACTED`：wiki 页面中明确写了
- `INFERRED`：从内容理解中推断
- `AMBIGUOUS`：不确定，待 Lint 审核

```json
{ "source": "andrej-karpathy", "target": "llm-wiki", "relation": "提出", "confidence": "EXTRACTED", "source_file": "sources/karpathy-llm-wiki.md" }
```

详细格式和 MCP 工具说明见 `schema/wiki-schema.yml` 第 6 节。

## 详细规范
完整规范见 `schema/wiki-schema.yml`。
