---
name: zero-hop-code-skill
description: >-
  Zero-dependency, zero-VRAM local BM25/IDF & AST-boundary codebase search engine.
  MANDATORY FIRST CHOICE before Grep or View on large files (>300 lines), massive HTML
  templates, UI components, multi-word queries, and localization auditing. Returns
  full untruncated method/template slices for immediate single-hop edits.
---

# Zero-Hop Code Skill: Token-Saving Codebase Retrieval

When refactoring or building features in repositories with large files (>300 lines), monolithic HTML/Vue/React templates, or multi-layered architectures, running repetitive `grep` searches or reading whole files exhausts context quotas, slows down prompt processing (TTFT), and degrades reasoning accuracy.

This skill provides a **zero-dependency, 0 MB VRAM, 100% offline BM25/IDF & symbol search engine** that splits `camelCase`/`PascalCase`/`snake_case` identifiers, handles multilingual tokens (Latin and Cyrillic/Ukrainian), and snaps chunks to AST `{ ... }` boundaries and HTML structure.

---

## ⚡ When to Use (MANDATORY: Prefer over multi-call `Grep` + `Read`)
- **Large Files (>300 lines) & Monolithic HTML:** e.g., scanning 5,000-line `index.html` or giant components without reading the whole file into context.
- **UI & Localization Audits:** Finding hardcoded strings, buttons, modals, or missing i18n keys across templates.
- **Multi-word concept or domain queries** (e.g., `"modal export uniform backup button"` or `"jwt refresh token expiry middleware"`).
- **Single-Hop Surgical Edits:** Rank `#1` returns the full untruncated slice (`[TOP MATCH - FULL SLICE]`), allowing an immediate `replace_file_content` / `Edit` without extra `view_file` calls.

---

## 🚫 When NOT to Use
- **Git Diffs & Branch Reviews:** Never index or search the repository for commit/PR reviews. Always use native `git diff`, `git log`, or `git show` directly.
- **Exact File & Line Already Known:** Target known files directly with surgical line reads (`Read` / `view_file`).
- **Small Files (<300 lines):** Read directly without indexing.

---

## 📋 Quick Prompt Snippet (Copy-Paste to Wake Up Any AI)
> *"Use zero-hop code skill (`python scripts/code_memory.py search '<query>'`) to locate the relevant code or template slice in a single hop before making changes."*

---

## 🛠️ Commands & Usage

*(Note: Adjust the script path if installed inside `.claude/skills/code-memory/scripts/code_memory.py` or `.gemini/skills/code-memory/scripts/code_memory.py`)*

### 1. Zero-Hop BM25/IDF Search (HTML, Code & Text — Auto-Indexes!)
You do **not** need to run `index` manually before searching. Running `search` automatically builds `.code_index.json` (excluded via `.git/info/exclude`) on first run and performs a ~0.15s delta refresh whenever files or Git branches change:

```bash
python scripts/code_memory.py search "<functionName, className, HTML tag, or domain keywords>"
```

**Examples:**
- Finding modal markup in a large HTML file:
  ```bash
  python scripts/code_memory.py search "openImportModal uniform fdb"
  ```
- Locating hardcoded text or i18n keys:
  ```bash
  python scripts/code_memory.py search "Завантажити бекап"
  ```
- Finding backend middleware or domain logic:
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

### 3. Exhaustive Call-Site & Symbol References (`refs`)
When renaming a method, modifying an interface, or tracking down all usages across the repository without omissions:
```bash
python scripts/code_memory.py refs "<symbolName>"
```

### 4. File & Codebase Outline (`outline`)
When orienting in an unfamiliar codebase or exploring a file's API surface without reading the full implementation:
```bash
# Outline a single file (class/function signatures with line numbers)
python scripts/code_memory.py outline src/controllers/authController.ts

# Outline all source files in the repository
python scripts/code_memory.py outline
```

### 5. Optional CLI Flags
- `--top <N>` or `-k <N>`: Change number of returned matches (default: `3`).
- `--full`: Expand full brace-aligned slices for **all** top matches instead of just `#1`.
- `--brief`: Show compact 4-line previews for all matches.
- `--path <dir>` or `-p <dir>`: Specify target repository root directory.