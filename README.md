# LLM Wiki

> Cross-device, cross-agent personal knowledge operating system.

Drop raw materials — articles, papers, screenshots, audio, URLs — into `raw/`. Your AI agent reads, summarizes, links concepts, and maintains a structured Markdown wiki automatically. Query it like a second brain. Lint it to keep it healthy. Review it to see how your knowledge grows.

Built on [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) concept, extended with multi-agent collaboration, knowledge graphs, and life-domain coverage beyond code.

## Architecture

```
raw/          → Raw materials (read-only, agent never modifies)
wiki/         → Structured Markdown wiki (agent writes & maintains)
graph/        → Knowledge graph (optional, Graphify-powered)
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

One source can touch 5–15 wiki pages.

### Query

Ask your agent a question. It reads `wiki/index.md`, drills into relevant pages, and answers with `[[wiki-link]]` citations. Valuable answers are saved as `wiki/outputs/` pages.

### Lint

Three levels of health checks:

- **Light** — broken links, orphan pages, index consistency (deterministic, zero tokens)
- **Deep** — contradictions, stale info, stub completion, missing concepts (LLM agent)
- **Growth** — cross-page associations, knowledge gaps, synthesis suggestions (periodic)

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

### 5. Start ingesting

```
> I put an article in raw/articles/. Please ingest it.
```

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
├── graph/                       # Knowledge graph (optional)
├── schema/
│   ├── wiki-schema.yml          # Single source of truth
│   └── .cursor/rules/wiki.mdc  # Cursor mapper
└── .local/                      # Per-device env (not synced)
    └── env.json
```

## Inspired By

- [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — original concept
- [Graphify](https://github.com/safishamsi/graphify) — knowledge graph engine, wiki export, multi-platform support

## License

MIT
