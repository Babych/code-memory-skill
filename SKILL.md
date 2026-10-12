---
name: code-memory
description: >-
  Zero-dependency local vector & symbol code memory for AI coding assistants.
  Reduces token consumption by 80-90% during large codebase refactoring by retrieving
  exact code chunks and line ranges instead of reading entire monolithic files.
---

# Code Memory: Token-Saving Retrieval for AI Coding Agents

When refactoring or vibe-coding in repositories with large files (e.g. monolithic 4,000+ line HTML files or 2,000+ line backends), reading full files exhausts AI context quotas rapidly.

This skill provides a **zero-dependency, 100% offline sparse-vector & symbol search engine** running directly on vanilla Python (no PyTorch, ChromaDB, or API keys required).

---

## ⚡ When to Use
- Before editing or reading large files (>300 lines).
- When searching for specific business logic, state variables, or API handlers.
- When minimizing LLM context tokens and avoiding context degradation.

---

## 🛠️ Commands & Usage

### 1. Build or Refresh Local Index
Scans the current directory and creates a cached chunk index (`.code_index.json`):
```bash
python scripts/code_memory.py index
```

### 2. Semantic & Symbol Search
Finds exact file paths, line ranges, and previews:
```bash
python scripts/code_memory.py search "<functionName or business keyword>"
```

**Example:**
```bash
python scripts/code_memory.py search "jwt refresh token expiry middleware"
```
**Output:**
```text
📍 src/middleware/auth.js (Lines 42 - 78) [Score: 0.315]
   | export async function verifyRefreshToken(token) { ... }
------------------------------------------------------------
📍 src/controllers/authController.js (Lines 112 - 145) [Score: 0.284]
   | const newToken = await refreshUserSession(refreshToken);
```

### 3. Surgical Edits
Once the exact line numbers are located, use surgical file tools (such as `view_file` with `StartLine`/`EndLine` or `replace_file_content`) targeting only that 25-line window, spending ~300 tokens instead of 30,000.
