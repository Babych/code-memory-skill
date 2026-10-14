# ⚡ Code Memory Skill

> **Zero-dependency, 0 MB VRAM local BM25/IDF & symbol search for AI coding agents (Antigravity, Gemini CLI, Claude Code, Cursor, Windsurf, Continue.dev, Cline / Roo Code, Aider).**  
> Reduces LLM context token usage and local Prompt Processing time (TTFT) by **80–90%**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.7+](https://img.shields.io/badge/Python-3.7%2B-brightgreen.svg)](https://python.org)
[![Dependencies: Zero](https://img.shields.io/badge/Dependencies-Zero-success.svg)]()
[![VRAM Overhead: 0 MB](https://img.shields.io/badge/VRAM_Overhead-0_MB-orange.svg)]()

---

## 💡 Why This Exists (The Cloud Quota & Local VRAM Problem)

When AI coding agents navigate repositories with large files (1,000–4,000+ lines), two bad things happen:
1. **On Cloud APIs (Gemini Flash/Pro, Claude, GPT):** Reading monolithic files burns 20,000–40,000 tokens per turn, exhausting rate limits and polluting attention.
2. **On Local LLMs (Ollama, llama.cpp, LM Studio on 8GB–16GB laptops):**
   - Dumping a 2,000-line file into an 8K/16K context window causes **60–120 seconds of prompt processing (prefill) lag** on laptop GPUs/APUs and pushes the KV cache into system RAM swap.
   - Traditional RAG tools require heavy vector DBs (ChromaDB, LanceDB, PyTorch) and local embedding models (`nomic-embed-text`, `bge-m3`) that eat **500MB–1.2GB of precious VRAM**.

**Code Memory solves both problems using pure Python standard library:**
- **0 MB VRAM / 0 Dependencies:** Uses true **BM25 / Inverse Document Frequency (IDF)** + AST-like symbol boosting across `camelCase`, `PascalCase`, `ACRONYMS`, and `snake_case`.
- **Zero-Hop Retrieval (1 Tool Call instead of 2):** Automatically expands the full, brace-balanced code block for the `#1 Top Match` while keeping `#2` and `#3` as compact 4-line dynamic previews. The AI agent gets the exact method code on the first call and can **immediately apply edits without an extra `view_file` round-trip**.

---

## 🏛️ Architectural Lineage

1. **The Classical Era (`ctags`, `gtags`, [BM25](https://en.wikipedia.org/wiki/Okapi_BM25)):** Sub-millisecond lookup, zero overhead, but predated LLMs and agent range boundaries.
2. **The Intermediate Era (Aider’s Repo Map):** Tree-sitter + PageRank maps, but injected globally into prompts rather than exposed as a lightweight, zero-dependency CLI skill.
3. **The Heavyweight Vector Era (ChromaDB, Local Embeddings):** High RAM/VRAM overhead, slow indexing, and dependency hell (`pip install torch chromadb`).

**Code Memory synthesizes the sweet spot:** `ctags` speed + `BM25/IDF` sub-token ranking + brace-aligned slicing for LLM tools.

---

## ⚖️ When to Use vs. When NOT to Use

| Task Type | Recommended Strategy | Reason |
| :--- | :--- | :--- |
| **Branch / PR Reviews & Git Diffs** | 🛑 Use native `git diff` / `git log` | Git already isolates exact line changes; indexing adds unnecessary overhead. |
| **Small Files (<300 lines)** | 🛑 Direct read (`view_file`) | Fits comfortably in context; chunking provides marginal benefit. |
| **Feature Work & Unknown Call Sites** | ⚡ **Use Code Memory** | Pinpoints exact function boundaries across unfamiliar multi-layer repos. |
| **Monolithic Files (>300 lines)** | ⚡ **Use Code Memory** | Avoids dumping thousands of lines, saving 80–90% of context tokens & prefill time. |
| **Local LLM Coding (7B–32B Models)** | ⚡ **Use Code Memory** | Keeps context under 1,500 tokens so quantized models stay sharp and fast. |

---

## 🚀 Key Capabilities

- **Zero-Hop Smart Output**: Rank `#1` automatically outputs the full brace-aligned method slice (`[TOP MATCH - FULL SLICE]`) with line numbers (`L42 | ...`), eliminating the extra `view_file` step. Ranks `#2` and `#3` show 4-line dynamic hit previews.
- **Smart Start & End Boundary Snapping**: Detects `class`, `interface`, `record`, `mixin`, `struct`, `fn`, `func`, `def`, `Widget`, `Future<T>`, `Task<T>`, and methods. Tracks `{ ... }` brace balance so functions are **cleanly framed instead of cut in half**.
- **True IDF + Symbol Boosting**: Rare domain identifiers (`RefreshTokenValidator`) automatically outweigh common words (`get`, `user`, `string`), with a priority boost when matching declared symbol names.
- **Git & Working-Tree Auto-Refresh**: Tracks `git rev-parse HEAD`, uncommitted `git status --porcelain`, and file `mtime`. Editing a file or switching branches triggers an automatic ~0.15s refresh on the next search.
- **Git-Clean by Design**: Automatically adds `.code_index.json` to `.git/info/exclude` so AI agents never commit the index.
- **Multi-Language Out of the Box**: C#, Dart/Flutter, TypeScript, JavaScript, Python, Go, Rust, Java, Kotlin, C/C++, PHP, Ruby, SQL, Vue, JSX/TSX, HTML, and CSS while ignoring build artifacts (`bin`, `obj`, `.dart_tool`, `node_modules`, `*.g.cs`, `*.g.dart`, `*.freezed.dart`).

---

## 🤖 Zero-Hop Autonomous Workflow

```mermaid
flowchart LR
    User["Developer Prompt<br/>'Fix token expiry check'"] --> Agent["AI Agent<br/>(Gemini Flash / Local Qwen / Claude)"]
    Agent -->|1. Calls search| CM["code_memory.py search"]
    CM -->|Returns full #1 method<br/>+ #2/#3 previews| Slice["📍 auth.ts (Lines 42-68)<br/>[TOP MATCH - FULL SLICE]"]
    Slice -->|2. Direct surgical edit<br/>(No view_file needed!)| Fix["Atomic Edit<br/>~350 tokens total"]
```

### 1. Give the Skill to Your Agent
Simply clone this repository or drop `SKILL.md` into your agent's skills directory:
- **Antigravity / Gemini:** Clone to your skills directory or reference via prompt.
- **Claude Code:** Add to `CLAUDE.md` or tools directory.
- **Cursor / Windsurf:** Add to `.cursorrules` or `.windsurfrules`.

### 2. Prompt Naturally
Ask your agent to implement a feature, find a bug, or explore the architecture:
> *"Implement user session refresh in the authentication flow."*

The AI agent will:
1. Detect that the repository has large/monolithic files.
2. Autonomously execute `python scripts/code_memory.py search "session refresh"`.
3. Receive the exact file and line bounds with full top match slice (`[TOP MATCH - FULL SLICE]`).
4. Apply the edit directly—saving 80–90% of context tokens with zero token bloat and no extra round-trip.

---

## 🛠️ CLI Reference (For Debugging / Manual Verification)

If you ever want to test or inspect the index manually:

```bash
# Search for symbols or concepts (auto-indexes if needed!)
python scripts/code_memory.py search "jwt refresh token expiry middleware"

# Optional: Force full index rebuild
python scripts/code_memory.py index
```

---

## 📄 License
MIT License. Free to use, modify, and share.
