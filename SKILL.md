---
name: code-memory
description: >-
  Zero-dependency, zero-VRAM local BM25/IDF & symbol code memory for AI coding assistants.
  Reduces token consumption and prompt processing time by 80-90% via single-hop retrieval
  of brace-aligned code chunks instead of reading entire monolithic files.
---

# Code Memory: Zero-Hop Token-Saving Retrieval for AI Coding Agents

When refactoring or building features in repositories with large files (e.g., monolithic 4,000+ line UI files or 2,000+ line backend services), reading full files exhausts context quotas, slows down prompt processing (TTFT), and degrades LLM reasoning accuracy.

This skill provides a **zero-dependency, 0 MB VRAM, 100% offline BM25/IDF & symbol search engine** running on standard Python.

---

## ⚡ When to Use
- Before reading or editing large files (>300 lines).
- When searching for specific business logic, domain models, state variables, or API handlers across unfamiliar or multi-layered codebases.
- When locating feature implementation sites or call sites across the repository.
- When running fast models (Gemini Flash) or local LLMs (Ollama, LM Studio, llama.cpp) where minimizing context window bloat and tool-call round-trips is critical.

---

## 🚫 When NOT to Use
- **Git Diffs & Branch Reviews:** Do not index or search the repository for commit/PR reviews. Always use native `git diff`, `git log`, or `git show` directly, as changes are already isolated.
- **Exact File & Line Already Known:** Target known files directly with surgical line reads (`view_file`, `head/tail`, or IDE range tools).
- **Small Files (<300 lines):** Read directly without indexing.

---

## 🛠️ Commands & Usage

### 1. Zero-Hop Semantic (BM25/IDF) & Symbol Search (Auto-Indexes!)
You do **not** need to run `index` manually before searching. Running `search` automatically builds `.code_index.json` on first run and transparently refreshes it whenever Git branches, commits, or working tree files change:

```bash
python scripts/code_memory.py search "<functionName, className, or business keywords>"
```

**Example:**
```bash
python scripts/code_memory.py search "jwt refresh token expiry middleware"
```

**Output:**
```text
🔍 Top 3 relevant code locations for: 'jwt refresh token expiry middleware'
====================================================================
📍 src/middleware/auth.ts (Lines 42 - 68 of 210) [Score: 0.82] [TOP MATCH - FULL SLICE]
   L42  | export async function verifyRefreshToken(token: string) {
   L43  |     const decoded = await jwt.verify(token, process.env.JWT_SECRET!);
   L44  |     if (Date.now() >= decoded.exp * 1000) {
   L45  |         throw new TokenExpiredError("Refresh token has expired");
   L46  |     }
   L47  |     return decoded;
   L48  | }
--------------------------------------------------------------------
📍 src/controllers/authController.ts (Lines 112 - 145 of 340) [Score: 0.45]
   L112 | export const refreshSession = async (req: Request, res: Response) => {
   L118 |     const newToken = await refreshUserSession(refreshToken);
--------------------------------------------------------------------
```

### 2. Immediate Zero-Hop Edits
Because the `#1 Top Match` displays the full brace-aligned slice with exact line numbers, the AI agent can execute an atomic edit (`replace_file_content` or diff) immediately without an extra `view_file` round-trip.
