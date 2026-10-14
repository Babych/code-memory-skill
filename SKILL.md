---
name: code-memory
description: >-
  Zero-dependency, zero-VRAM local BM25/IDF & AST-boundary codebase search skill.
  Use before Grep or Read when locating business logic, symbols, or call sites across
  unfamiliar or large files (>300 lines). Returns a full, untruncated brace-aligned
  method slice for the #1 match so you can edit immediately in a single hop.
---

# Code Memory: Zero-Hop Token-Saving Codebase Retrieval

When refactoring or building features in repositories with large files (>300 lines) or multi-layered architectures, running repetitive `grep` searches or reading full files exhausts context quotas, slows down prompt processing (TTFT), and degrades reasoning accuracy.

This skill provides a **zero-dependency, 0 MB VRAM, 100% offline BM25/IDF & symbol search engine** that splits `camelCase`/`PascalCase`/`snake_case` identifiers and snaps chunks to `{ ... }` method/class boundaries (including leading decorators like `[HttpPost]` or `@override`).

---

## ⚡ When to Use (Prefer over multi-call `Grep` + `Read`)
- **Multi-word concept or domain queries** (e.g., `"jwt refresh token expiry middleware"`) where exact strings don't appear on a single line for `grep`.
- **Before reading or editing large files (>300 lines).**
- **When locating feature implementations, domain models, or call sites** across unfamiliar codebases.
- **When minimizing tool-call round-trips:** Rank `#1` returns the full untruncated method slice (`[TOP MATCH - FULL SLICE]`), allowing you to apply an atomic `Edit` / `replace_file_content` immediately without a second `Read`/`view_file` call.

---

## 🚫 When NOT to Use
- **Git Diffs & Branch Reviews:** Never index or search the repository for commit/PR reviews. Always use native `git diff`, `git log`, or `git show` directly.
- **Exact File & Line Already Known:** Target known files directly with surgical line reads (`Read` / `view_file`).
- **Small Files (<300 lines):** Read directly without indexing.

---

## 🛠️ Commands & Usage

*(Note: Adjust the script path if installed inside `.claude/skills/code-memory/scripts/code_memory.py` or `.gemini/skills/code-memory/scripts/code_memory.py`)*

### 1. Zero-Hop BM25/IDF & Symbol Search (Auto-Indexes!)
You do **not** need to run `index` manually before searching. Running `search` automatically builds `.code_index.json` (excluded via `.git/info/exclude`) on first run and performs a ~0.15s delta refresh whenever files or Git branches change:

```bash
python scripts/code_memory.py search "<functionName, className, or domain keywords>"
```

**Example:**
```bash
python scripts/code_memory.py search "jwt refresh token expiry middleware"
```

**Output:**
```text
🔍 Top 3 relevant code locations for: 'jwt refresh token expiry middleware'
====================================================================
📍 src/middleware/auth.ts (Lines 42 - 48 of 210) [Score: 0.82] [TOP MATCH - FULL SLICE]
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
Because `[TOP MATCH - FULL SLICE]` outputs exact, untruncated lines with line numbers (`L42 | ...`), you can execute your edit tool (`Edit` / `replace_file_content`) immediately without calling `Read` / `view_file` first.

### 3. Optional CLI Flags
- `--top <N>` or `-k <N>`: Change number of returned matches (default: `3`).
- `--full`: Expand full brace-aligned slices for **all** top matches instead of just `#1`.
- `--brief`: Show compact 4-line previews for all matches.
- `--path <dir>` or `-p <dir>`: Specify target repository root directory.