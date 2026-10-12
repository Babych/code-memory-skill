# ⚡ Code Memory Skill

> **Zero-dependency local vector & symbol search for AI coding agents (Antigravity, Cursor, Claude Code, Windsurf, Aider).**  
> Reduces LLM context token usage by **80–90%** during codebase refactoring.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.7+](https://img.shields.io/badge/Python-3.7%2B-brightgreen.svg)](https://python.org)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-success.svg)]()

---

## 🎯 Why This Exists

When AI coding assistants refactor code or implement features, they often read entire files into their context window. In projects with monolithic files (e.g., 4,000+ line HTML files or 2,000+ line backend controllers):
- Reading a file costs **15,000 – 35,000 tokens per prompt**.
- AI quotas burn out within minutes.
- Long contexts degrade AI reasoning quality (Lost-in-the-Middle phenomenon).

**Code Memory** indexes code into overlapping syntactic chunks using an offline BM25/TF-IDF sparse-vector algorithm with camelCase, snake_case, and multilingual tokenization. The AI retrieves **only the exact 20–30 lines** it needs to modify, dropping token consumption to ~500–1,500 tokens.

---

## 🚀 Key Features

- **Zero External Dependencies**: Standard Python standard library only (`re`, `math`, `json`, `pathlib`). No PyTorch, ChromaDB, Hugging Face, or OpenAI API keys needed.
- **Blazing Fast**: Indexes 10,000 lines of code in < 0.2s; searches in < 0.02s.
- **Agent Native**: Formatted specifically for LLMs and agent tool calls (`SKILL.md` compliant).
- **Cross-Platform**: Handles Windows console encodings (UTF-8, cp1251, cp1252) and Linux/macOS out of the box.

---

## 📦 Quick Start

### 1. Copy into your project
Drop `scripts/code_memory.py` into your project's `scripts/` directory:
```bash
mkdir -p scripts
curl -o scripts/code_memory.py https://raw.githubusercontent.com/Babych/code-memory-skill/main/scripts/code_memory.py
```

Add `.code_index.json` to your `.gitignore`:
```bash
echo ".code_index.json" >> .gitignore
```

### 2. Build index
```bash
python scripts/code_memory.py index
```

### 3. Search code
```bash
python scripts/code_memory.py search "jwt refresh token expiry middleware"
```

**Output:**
```text
🔍 Top relevant code locations for: 'jwt refresh token expiry middleware'
============================================================
📍 src/middleware/auth.js (Lines 42 - 78) [Score: 0.315]
   | export async function verifyRefreshToken(token) {
   |     const decoded = await jwt.verify(token, SECRET);
   |     if (Date.now() >= decoded.exp * 1000) throw new Error("Expired");
------------------------------------------------------------
📍 src/controllers/authController.js (Lines 112 - 145) [Score: 0.284]
   | const newToken = await refreshUserSession(refreshToken);
------------------------------------------------------------
```

---

## 🤖 Using as an Antigravity / Cursor Skill

1. Place `SKILL.md` into your `.agents/skills/code-memory/` or `~/.gemini/antigravity/skills/code-memory/`.
2. Add this instruction to your project's `AGENTIC.md`, `CLAUDE.md`, or system prompt:

```markdown
### Token-Saving Protocol
Before reading files with more than 300 lines, run:
`python scripts/code_memory.py search "<keyword>"`
Use the returned line numbers to view only the relevant lines with surgical range reads.
```

---

## 📄 License
MIT License. Free to use, modify, and share.
