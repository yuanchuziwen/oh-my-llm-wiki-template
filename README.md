# LLM Wiki

[English](README.md) | [简体中文](README.zh-CN.md)

> Cross-device, cross-agent personal knowledge operating system.

Drop raw materials — articles, papers, screenshots, audio, URLs — into `raw/`. Your AI agent reads, summarizes, links concepts, and maintains a structured Markdown wiki automatically. Query it like a second brain. Lint it to keep it healthy. Review it to see how your knowledge grows.

Built on [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) concept, extended with multi-agent collaboration, knowledge graphs, and life-domain coverage beyond code.

## Architecture

```
raw/          → Raw materials (read-only, agent never modifies)
wiki/         → Structured Markdown wiki (agent writes & maintains)
graph/        → Knowledge graph (agent maintains during ingest, MCP server for queries)
tools/        → Tool scripts (graph-server.py MCP server, etc.)
schema/       → Schema definitions & platform mappers
```

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Device A    │     │  Device B    │     │  Device C    │
│  Claude Code │     │  OpenClaw    │     │  Cursor      │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       └───────────┬───────┴───────────────────┘
                   │
            ┌──────▼──────┐
            │   Git Repo   │
            └─────────────┘
```

Every agent reads the same `wiki-schema.yml` through platform-specific mappers:

| Platform | Mapper File |
|---|---|
| Claude Code | `CLAUDE.md` |
| Cursor | `schema/.cursor/rules/wiki.mdc` |
| Codex / OpenClaw / Aider | `AGENTS.md` |

## Four Operations

### Ingest

Put a file in `raw/` and tell your agent to process it. The agent will:

1. Create a summary page in `wiki/sources/`
2. Create or update `wiki/concepts/` and `wiki/entities/` pages
3. Update `wiki/index.md` and `wiki/log.md`
4. Update `graph/graph.json` with new nodes and edges
5. Update `graph/GRAPH_REPORT.md` with stats

One source can touch 5–15 wiki pages.

### Query

Ask your agent a question. It reads `wiki/index.md`, uses the knowledge graph MCP server to discover hidden connections, drills into relevant pages, and answers with `[[wiki-link]]` citations. Valuable answers are saved as `wiki/outputs/` pages.

### Lint

Three levels of health checks:

- **Light** — broken links, orphan pages, index consistency (deterministic, zero tokens)
- **Deep** — contradictions, stale info, stub completion, missing concepts (LLM agent)
- **Growth** — cross-page associations, knowledge gaps, synthesis suggestions, graph-powered isolation/overload detection (periodic)

### Review

Periodic knowledge retrospectives — weekly, monthly, yearly — saved to `wiki/journal/`.

## Quick Start

### 1. Clone

```bash
git clone git@github.com:yuanchuziwen/llm-wiki-template.git ~/llm-wiki
cd ~/llm-wiki
```

### 2. Open with your agent

```bash
# Claude Code
cd ~/llm-wiki && claude

# Or open in Cursor / any other agent
```

On first launch, the agent detects your local environment, checks required tools, and writes `.local/env.json` (not synced — each device has its own).

### 3. Required tools

| Tool | Purpose | Install |
|---|---|---|
| Git | Version control & sync | `xcode-select --install` |
| ripgrep | Agent search backend | `brew install ripgrep` |

### 4. Recommended tools

| Tool | Purpose | Install |
|---|---|---|
| [Obsidian](https://obsidian.md) | Browse wiki (open `wiki/` as vault) | `brew install --cask obsidian` |
| Pandoc | Format conversion | `brew install pandoc` |
| [Jina Reader](https://r.jina.ai) | URL → Markdown | Free API, no install |
| networkx + mcp | Knowledge graph MCP server dependencies | `pip install networkx mcp` |

### 5. Verify it works

Fetch Karpathy's original article as your first raw material:

```bash
curl -sL "https://r.jina.ai/https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f" \
  > ~/llm-wiki/raw/articles/karpathy-llm-wiki.md
```

Then tell your agent:

```
帮我 ingest raw/articles/karpathy-llm-wiki.md
```

Check that the agent:
- [ ] Created `wiki/sources/karpathy-llm-wiki.md`
- [ ] Created several `wiki/concepts/*.md` pages (e.g. llm-wiki, ingest, lint, rag)
- [ ] Created `wiki/entities/andrej-karpathy.md`
- [ ] Updated `wiki/index.md` with all new pages
- [ ] Appended an ingest record to `wiki/log.md`
- [ ] Updated `graph/graph.json` with nodes and edges
- [ ] Updated `graph/GRAPH_REPORT.md` with stats
- [ ] All pages have correct YAML frontmatter and `[[wiki-links]]`

Then test a query:

```
LLM Wiki 和 RAG 有什么区别？
```

The agent should read `wiki/index.md` → drill into relevant pages → answer with `[[wiki-link]]` citations → optionally save to `wiki/outputs/`.

## Wiki Page Format

All pages use YAML frontmatter + Markdown + `[[wiki-links]]`:

```markdown
---
title: LLM Wiki
type: concept
created: 2026-04-12
tags: [AI, knowledge-management]
status: active
---

## Definition
...

## Sources
- [[sources/karpathy-gist]]

## Related
- [[concepts/knowledge-graph]]
```

Page types: `concept` | `entity` | `source` | `output` | `area` | `journal`

## Multimodal Input

| Input | Processing |
|---|---|
| Markdown / text | Direct read |
| PDF | Text extraction |
| Images | Vision model |
| Audio / video | Whisper transcription |
| URL | Jina Reader → Markdown |

## Cross-Device Sync

Git is the sync layer. Each agent session:
- **Start**: `git pull --rebase`
- **End** (if changed): `git commit` + `git push`

Conflicts are rare by design (one file per concept, append-only logs). When they occur, the agent resolves them semantically.

## Project Structure

```
llm-wiki/
├── CLAUDE.md                    # Claude Code agent instructions
├── AGENTS.md                    # Codex / OpenClaw / Aider instructions
├── raw/                         # Raw materials (read-only)
│   ├── articles/
│   ├── papers/
│   ├── books/
│   ├── screenshots/
│   ├── audio/
│   ├── clippings/
│   └── misc/
├── wiki/                        # Structured wiki (agent-maintained)
│   ├── index.md                 # Global directory
│   ├── log.md                   # Operation log
│   ├── concepts/
│   ├── entities/
│   ├── sources/
│   ├── outputs/
│   ├── areas/
│   └── journal/
├── graph/                       # Knowledge graph (agent-maintained)
│   ├── graph.json               # Structured graph (NetworkX node-link format)
│   └── GRAPH_REPORT.md          # Graph stats & top nodes
├── tools/                       # Tool scripts
│   └── graph-server.py          # Knowledge graph MCP server
├── docs/                        # Design documents
├── schema/
│   ├── wiki-schema.yml          # Single source of truth
│   └── .cursor/rules/wiki.mdc  # Cursor mapper
└── .local/                      # Per-device env (not synced)
    └── env.json
```

## Knowledge Graph

The agent builds a knowledge graph during ingest — no external tools or extra LLM calls needed. Since the agent already understands the content while writing wiki pages, it simply writes the entities and relationships into `graph/graph.json` at the same time.

A lightweight MCP server (`tools/graph-server.py`) loads the graph into memory and exposes 6 query tools:

| Tool | Purpose |
|---|---|
| `get_neighbors` | Find related nodes (1-N hops) |
| `shortest_path` | Discover hidden connections between two concepts |
| `top_nodes` | Identify the most connected knowledge |
| `graph_stats` | Graph health metrics |
| `get_node` | Node details with edges |
| `reload` | Refresh after ingest |

The MCP server is auto-managed by your agent platform — configured once in `.claude/mcp.json` or `.cursor/mcp.json`, started when you open the project, stopped when you close it. If `graph.json` doesn't exist yet, all tools return empty results gracefully.

## Inspired By

- [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — original concept
- [Graphify](https://github.com/safishamsi/graphify) — knowledge graph engine, wiki export, multi-platform support

## License

MIT
