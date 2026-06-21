<div align="center">

# prompt-versioner — Git-style version control for production prompts

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![CLI](https://img.shields.io/badge/Interface-CLI%20%2B%20library-555)](#)
[![Status](https://img.shields.io/badge/Status-Working%20code-blue)](#)

</div>

---

> Prompt management as a first-class artifact. Versioned in a SQLite store, diffable, rollback-able, with weighted A/B routing so you can ship a new prompt to 10% of traffic and watch the evals before going to 100%.

**Why this exists.** Prompts in production are code — they have versions, they have bugs, they get rolled back. But most teams keep prompts as Python string literals inside a Python file, which means: no diff, no rollback, no A/B without redeploying. This library makes prompts as managed as any other piece of production code, without forcing them into your repo.

Pairs naturally with [prompt-eval-toolkit](https://github.com/darrshangovender/prompt-eval-toolkit) (which decides whether to promote) and [llm-cost-tracker](https://github.com/darrshangovender/llm-cost-tracker) (which measures the dollars).

---

## What it does

```bash
# Register a prompt by name. First version is v1.
$ pv set extractor < extractor_v1.txt
[extractor] saved as v1

# Edit the file, register again. Auto-bumped to v2.
$ pv set extractor < extractor_v2.txt
[extractor] saved as v2

# See the diff between any two versions.
$ pv diff extractor 1 2

# Route 10% of traffic to v2, 90% to v1. (Stable per prompt-hash for repeatable rollouts.)
$ pv route extractor --split 1:0.9,2:0.1

# Promote v2 to 100%.
$ pv promote extractor 2

# Roll back instantly.
$ pv promote extractor 1
```

```python
from prompt_versioner import PromptStore

ps = PromptStore("prompts.db")

# In production code:
prompt_template = ps.get("extractor")  # returns the routed version
final = prompt_template.format(text=input_text)
# Behind the scenes: weighted route resolves once per call, recorded for analysis.
```

## Why hash-stable routing

Naive random A/B routing means the same user hitting the chatbot twice could get v1, then v2 — confusing UX and noisy evals. We hash the input prompt and route on the hash, so the same prompt always lands on the same version within a routing config. When you change the route, the hash space re-partitions consistently.

## Why SQLite

Same reason as `llm-cost-tracker`: one file, zero infra, works for hobby projects and production-medium scale. Swap to Postgres when you outgrow it; the `PromptStore` interface is intentionally small.

## Repo structure

```
.
├── prompt_versioner/
│   ├── __init__.py
│   ├── store.py        # PromptStore — set, get, route, promote
│   ├── routing.py      # hash-stable weighted picker
│   ├── diff.py         # unified diff between versions
│   └── cli.py          # `pv set/get/diff/route/promote/list`
├── tests/
│   ├── test_store.py
│   └── test_routing.py
└── pyproject.toml
```

## Schema

```sql
-- One row per prompt + version. Routes live in a separate table.
CREATE TABLE prompts (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    version INTEGER NOT NULL,
    body    TEXT NOT NULL,
    sha256  TEXT NOT NULL,
    created TEXT NOT NULL,
    UNIQUE(name, version)
);

-- name -> JSON like {"1": 0.9, "2": 0.1}
CREATE TABLE routes (
    name      TEXT PRIMARY KEY,
    weights   TEXT NOT NULL,
    updated   TEXT NOT NULL
);
```

## CLI commands

| Command | What it does |
|---|---|
| `pv list` | List all prompts and their current route |
| `pv set <name>` | Read stdin, save as next version of `<name>` |
| `pv get <name> [version]` | Print a prompt body. Omit version for current route |
| `pv diff <name> <v1> <v2>` | Unified diff between two versions |
| `pv route <name> --split 1:0.9,2:0.1` | Set weighted route |
| `pv promote <name> <version>` | Shorthand for `--split version:1.0` |
| `pv history <name>` | Show all versions with timestamps |

## Status

- [x] PromptStore with set/get/route/promote
- [x] Hash-stable weighted routing
- [x] Unified-diff command
- [x] Full CLI
- [x] SQLite store
- [ ] Postgres adapter
- [ ] Per-version usage stats (combine with llm-cost-tracker for "cost per prompt version")

## Author

Darrshan Govender · Founder, [Agulhas Code](https://agulhascode.co.za)