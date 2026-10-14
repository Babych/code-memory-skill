#!/usr/bin/env python3
"""
Code Memory: Zero-dependency, 0-VRAM local BM25/IDF & symbol search for AI coding agents.
Features incremental delta-indexing, decorator-aware AST boundary snapping,
and Zero-Hop retrieval for Cloud (Gemini, Claude, GPT) and Local LLMs (Ollama, llama.cpp).

Author: Dmytro Babych (https://github.com/babych/zero-hop-code-skill)
License: MIT (c) 2026 Dmytro Babych
"""

import os
import sys
import json
import math
import re
import hashlib
import subprocess
from pathlib import Path

# Enforce UTF-8 output across Windows and POSIX shells
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

INDEX_FILE_NAME = ".code_index.json"
INDEX_VERSION = 6

DEFAULT_EXTS = {
    ".js", ".ts", ".jsx", ".tsx", ".vue", ".html", ".css",
    ".py", ".sql", ".dart", ".cs", ".go", ".rs", ".java", ".kt",
    ".cpp", ".c", ".h", ".hpp", ".php", ".rb", ".swift"
}

DEFAULT_IGNORE_DIRS = {
    ".git", "node_modules", ".gemini", ".cursor", ".windsurf", ".claude", ".aider", ".agent",
    "dist", "build", "out", "target", "vendor", "coverage",
    ".wrangler", "__pycache__", ".venv", "venv", "env",
    "bin", "obj", ".vs", ".idea", ".dart_tool", ".pub-cache", ".next", ".nuxt"
}

IGNORE_FILE_SUFFIXES = (
    ".min.js", ".min.css", ".bundle.js", ".map",
    ".g.cs", ".designer.cs", ".generated.cs", ".AssemblyInfo.cs",
    ".g.dart", ".freezed.dart", ".gr.dart",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock", "cargo.lock"
)

# 1. Type definitions (class, interface, enum, struct, record, mixin, extension, trait)
TYPE_DEF_PATTERN = re.compile(
    r'^\s*(?:export\s+)?(?:default\s+)?(?:public\s+|private\s+|protected\s+|internal\s+)?'
    r'(?:abstract\s+|sealed\s+|static\s+|partial\s+|base\s+|final\s+|data\s+)*'
    r'(?:class|interface|enum|struct|record|mixin|extension|typedef|trait|impl)\s+([A-Za-z_][A-Za-z0-9_]*)',
    re.MULTILINE
)

# 2. Method / Function definitions across C#, Dart, TS/JS, Python, Go, Rust, Java/Kotlin, C++
FUNC_DEF_PATTERN = re.compile(
    r'^\s*(?:'
    r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)'
    r'|(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)'
    r'|(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)'
    r'|func\s+(?:\([^)]+\)\s*)?([A-Za-z_][A-Za-z0-9_]*)'
    r'|(?:public|private|protected|internal|static|async|override|virtual|extern|fun|Future|Task|Widget|void|int|double|bool|String|var|final|const)\b[^;=\n{}()]*?\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^>]+>)?\s*\('
    r')',
    re.MULTILINE
)

# Robust regex to strip block comments, string literals, and single-line comments before counting braces
STRING_OR_COMMENT_RE = re.compile(
    r'/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//.*?$|#.*?$',
    re.MULTILINE | re.DOTALL
)
LINE_COMMENT_OR_STRING_RE = re.compile(
    r'/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//.*$|#.*$'
)

CONTROL_KEYWORDS = {
    "if", "for", "foreach", "while", "switch", "catch", "using", "lock",
    "return", "throw", "new", "await", "typeof", "nameof", "sizeof", "super", "this"
}

STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "return", "const", "let", "var",
    "function", "class", "public", "private", "protected", "internal", "static", "async",
    "await", "void", "null", "true", "false", "import", "export", "default", "new", "try",
    "catch", "else", "elif", "string", "int", "bool", "boolean", "number", "list", "map"
}


def tokenize(text, remove_stopwords=True):
    """Splits camelCase, PascalCase, ACRONYMS, snake_case, and multilingual words."""
    # Latin and Cyrillic uppercase/lowercase splitting
    text = re.sub(r'([A-Z\u0410-\u042F]+)([A-Z\u0410-\u042F][a-z\u0430-\u044F])', r'\1 \2', text)
    text = re.sub(r'([a-z0-9\u0430-\u044F])([A-Z\u0410-\u042F])', r'\1 \2', text)
    text = text.replace('_', ' ').replace('-', ' ')
    tokens = re.findall(r'[a-zA-Z0-9\u0400-\u04FF]+', text.lower())
    if remove_stopwords:
        return [t for t in tokens if len(t) > 1 and t not in STOP_WORDS]
    return [t for t in tokens if len(t) > 1]


def extract_symbols_and_def_lines(lines):
    def_lines = set()
    line_symbols = {}

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "/*", "*", "///")):
            continue

        found_names = []
        m_type = TYPE_DEF_PATTERN.match(line)
        if m_type:
            found_names.append(m_type.group(1))

        m_func = FUNC_DEF_PATTERN.match(line)
        if m_func:
            name = next((g for g in m_func.groups() if g is not None), None)
            if name and name not in CONTROL_KEYWORDS:
                found_names.append(name)

        if found_names:
            def_lines.add(idx)
            sym_tokens = []
            for name in found_names:
                sym_tokens.extend(tokenize(name, remove_stopwords=False))
                sym_tokens.append(name.lower())
            line_symbols[idx] = list(set(sym_tokens))

    return sorted(def_lines), line_symbols


def include_leading_decorators(lines, def_idx):
    start = def_idx
    for back in range(1, 4):
        cand = def_idx - back
        if cand < 0:
            break
        s = lines[cand].strip()
        if s.startswith(("@", "[", "///", "/**")) and not s.endswith(";"):
            start = cand
        else:
            break
    return start


def compute_smart_end_line(lines, start_line, def_idx, def_set, is_python=False, min_size=5):
    """
    Finds natural logical boundaries without arbitrary length caps,
    tracking Python indentation or brace balance across comments/strings.
    """
    n_lines = len(lines)
    if start_line >= n_lines:
        return n_lines

    if is_python and def_idx < n_lines:
        base_indent = len(lines[def_idx]) - len(lines[def_idx].lstrip())
        for idx in range(def_idx + 1, n_lines):
            stripped = lines[idx].strip()
            if not stripped or stripped.startswith("#"):
                continue
            curr_indent = len(lines[idx]) - len(lines[idx].lstrip())
            if curr_indent <= base_indent and (idx - start_line) >= 5:
                return include_leading_decorators(lines, idx)
    else:
        brace_balance = 0
        saw_open_brace = False
        def _strip_keep_newlines(m):
            return "\n" * m.group(0).count("\n")
        full_text = "\n".join(lines[start_line:])
        clean_text = STRING_OR_COMMENT_RE.sub(_strip_keep_newlines, full_text)
        clean_lines = clean_text.splitlines()

        for offset, clean_line in enumerate(clean_lines):
            idx = start_line + offset
            if idx >= start_line + 10 and idx in def_set:
                return include_leading_decorators(lines, idx)

            open_c = clean_line.count("{")
            close_c = clean_line.count("}")
            if open_c > 0:
                saw_open_brace = True
            brace_balance += (open_c - close_c)

            if saw_open_brace and brace_balance <= 0 and (idx - start_line) >= 3:
                return idx + 1

    return n_lines


def get_git_state(root_dir="."):
    try:
        head = subprocess.run(
            ["git", "-C", root_dir, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2
        )
        status = subprocess.run(
            ["git", "-C", root_dir, "status", "--porcelain", "-uno"],
            capture_output=True, text=True, timeout=2
        )
        if head.returncode == 0:
            status_digest = hashlib.md5(status.stdout.strip().encode("utf-8")).hexdigest()[:10]
            return f"{head.stdout.strip()}:{status_digest}"
    except Exception:
        pass
    return ""


def iter_source_files(root_dir="."):
    root = Path(root_dir).resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".git")
        ]
        for fname in filenames:
            if fname == INDEX_FILE_NAME:
                continue
            lower_fname = fname.lower()
            if lower_fname.endswith(IGNORE_FILE_SUFFIXES):
                continue
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() in DEFAULT_EXTS:
                yield fpath, root


def ensure_git_exclude(root_dir="."):
    """Robustly locates and updates git info/exclude, supporting worktrees and submodules."""
    try:
        res = subprocess.run(
            ["git", "-C", root_dir, "rev-parse", "--git-path", "info/exclude"],
            capture_output=True, text=True, timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            exclude_file = Path(root_dir) / res.stdout.strip()
        else:
            exclude_file = Path(root_dir) / ".git" / "info" / "exclude"

        if exclude_file.parent.exists() or exclude_file.parent.mkdir(parents=True, exist_ok=True):
            content = exclude_file.read_text(encoding="utf-8", errors="ignore") if exclude_file.exists() else ""
            if INDEX_FILE_NAME not in content:
                with exclude_file.open("a", encoding="utf-8") as f:
                    f.write(f"\n{INDEX_FILE_NAME}\n")
    except Exception as e:
        print(f"⚠️ Warning: Could not update git exclude file: {e}", file=sys.stderr)


def chunk_single_file(path, rel_path):
    file_chunks = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"⚠️ Warning: Failed to read {rel_path}: {e}", file=sys.stderr)
        return file_chunks

    lines = content.splitlines()
    n_lines = len(lines)
    if n_lines == 0:
        return file_chunks

    is_python = path.suffix.lower() == ".py"
    def_indices, line_symbols = extract_symbols_and_def_lines(lines)
    def_set = set(def_indices)

    if not def_indices:
        step = 50
        i = 0
        while i < n_lines:
            start_line = i
            end_line = min(n_lines, start_line + 80)
            chunk_lines = lines[start_line:end_line]
            if chunk_lines:
                chunk_text = "\n".join(chunk_lines)
                words = tokenize(chunk_text)
                if words:
                    file_chunks.append({
                        "file": rel_path,
                        "start_line": start_line + 1,
                        "end_line": end_line,
                        "total_lines": n_lines,
                        "truncated": end_line < n_lines,
                        "words": list(set(words)),
                        "symbols": [],
                        "header": chunk_lines[0].strip()[:100]
                    })
            i += step
        return file_chunks

    processed_ranges = []
    for def_idx in def_indices:
        start_line = include_leading_decorators(lines, def_idx)
        if processed_ranges and start_line < processed_ranges[-1]:
            continue

        end_line = compute_smart_end_line(lines, start_line, def_idx, def_set, is_python=is_python)
        processed_ranges.append(end_line)

        chunk_lines = lines[start_line:end_line]
        if chunk_lines:
            chunk_text = "\n".join(chunk_lines)
            words = tokenize(chunk_text)
            if words:
                symbols = []
                for line_idx in range(start_line, end_line):
                    if line_idx in line_symbols:
                        symbols.extend(line_symbols[line_idx])

                all_words = list(set(words).union(set(symbols)))
                file_chunks.append({
                    "file": rel_path,
                    "start_line": start_line + 1,
                    "end_line": end_line,
                    "total_lines": n_lines,
                    "truncated": False,
                    "words": all_words,
                    "symbols": list(set(symbols)),
                    "header": chunk_lines[0].strip()[:100]
                })

    return file_chunks


def build_or_update_index(root_dir=".", force_full=False, quiet=False):
    index_path = Path(root_dir) / INDEX_FILE_NAME
    existing_file_mtimes = {}
    existing_chunks_by_file = {}

    if not force_full and index_path.exists():
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("version") == INDEX_VERSION:
                existing_file_mtimes = raw.get("file_mtimes", {})
                for ch in raw.get("chunks", []):
                    existing_chunks_by_file.setdefault(ch["file"], []).append(ch)
        except Exception:
            pass

    new_file_mtimes = {}
    all_chunks = []
    reindexed_count = 0

    for path, root in iter_source_files(root_dir):
        try:
            stat = path.stat()
            if stat.st_size > 5 * 1024 * 1024:  # Raised threshold to 5MB with warning
                if not quiet:
                    print(f"⚠️ Skipping large file (>5MB): {path.relative_to(root)}", file=sys.stderr)
                continue
            rel_path = path.relative_to(root).as_posix()
            mtime = round(stat.st_mtime, 3)
            new_file_mtimes[rel_path] = mtime

            if not force_full and rel_path in existing_file_mtimes and existing_file_mtimes[rel_path] == mtime:
                all_chunks.extend(existing_chunks_by_file.get(rel_path, []))
            else:
                all_chunks.extend(chunk_single_file(path, rel_path))
                reindexed_count += 1
        except Exception as e:
            if not quiet:
                print(f"⚠️ Error processing {path}: {e}", file=sys.stderr)

    deleted_files = set(existing_file_mtimes.keys()) - set(new_file_mtimes.keys())
    if reindexed_count > 0 or deleted_files or force_full or not index_path.exists():
        meta = {
            "version": INDEX_VERSION,
            "git_state": get_git_state(root_dir),
            "file_mtimes": new_file_mtimes,
            "chunks": all_chunks
        }
        index_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        ensure_git_exclude(root_dir)
        if not quiet:
            print(f"✅ Indexed {len(all_chunks)} chunks across {len(new_file_mtimes)} files ({reindexed_count} updated).")
    elif not quiet:
        print(f"✅ Index is already up-to-date ({len(all_chunks)} chunks).")

    return all_chunks


def extract_chunk_view(root_dir, file_rel_path, start_line, end_line, query_tokens, full_slice=False, fallback_header=""):
    fpath = Path(root_dir) / file_rel_path
    try:
        lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
        chunk_lines = lines[start_line - 1:end_line]
        if not chunk_lines:
            return [(start_line, fallback_header)]

        if full_slice:
            # Preserve full line text without arbitrary length clamping
            return [(start_line + idx, text.rstrip("\r\n")) for idx, text in enumerate(chunk_lines)]

        scored_lines = []
        for idx, text in enumerate(chunk_lines):
            line_num = start_line + idx
            line_tokens = set(tokenize(text, remove_stopwords=False))
            hits = len(query_tokens.intersection(line_tokens))
            scored_lines.append((hits, idx, line_num, text.strip()))

        best_hits, best_idx, _, _ = max(scored_lines, key=lambda x: x[0])

        preview = []
        first_line = chunk_lines[0].strip()
        if first_line:
            preview.append((start_line, first_line[:110]))

        if best_hits > 0:
            win_start = max(1 if first_line else 0, best_idx - 1)
            win_end = min(len(chunk_lines), best_idx + 2)
            for idx in range(win_start, win_end):
                l_text = chunk_lines[idx].strip()
                if l_text:
                    preview.append((start_line + idx, l_text[:110]))
        else:
            for idx in range(1, min(3, len(chunk_lines))):
                l_text = chunk_lines[idx].strip()
                if l_text:
                    preview.append((start_line + idx, l_text[:110]))

        return preview[:4]
    except Exception:
        return [(start_line, fallback_header)]


def search_references(symbol, root_dir="."):
    """
    Finds every occurrence of a symbol across all source files for refactoring safety.
    Guarantees no call site is omitted.
    """
    root = Path(root_dir).resolve()
    symbol_lower = symbol.lower()
    matches = 0

    print(f"\n🔍 All reference occurrences across codebase for: '{symbol}'\n" + "=" * 68)
    for path, _ in iter_source_files(root_dir):
        try:
            rel_path = path.relative_to(root).as_posix()
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for idx, line in enumerate(lines):
                if symbol_lower in line.lower():
                    matches += 1
                    print(f"📍 {rel_path} | L{idx + 1:<4} | {line.strip()[:110]}")
        except Exception:
            pass
    print("=" * 68)
    print(f"Found {matches} reference locations.")


def search(query, top_k=3, mode="smart", root_dir="."):
    chunks = build_or_update_index(root_dir, force_full=False, quiet=True)

    query_tokens = set(tokenize(query, remove_stopwords=True))
    if not query_tokens:
        query_tokens = set(tokenize(query, remove_stopwords=False))
    if not query_tokens:
        print("❌ Query is empty.")
        return

    n_chunks = max(1, len(chunks))

    doc_freq = {
        qt: sum(1 for c in chunks if qt in c.get("words", []))
        for qt in query_tokens
    }
    idf = {
        qt: math.log(1.0 + (n_chunks - df + 0.5) / (df + 0.5))
        for qt, df in doc_freq.items()
    }

    scored = []
    for chunk in chunks:
        chunk_words = set(chunk.get("words", []))
        chunk_symbols = set(chunk.get("symbols", []))

        matched_words = query_tokens.intersection(chunk_words)
        matched_symbols = query_tokens.intersection(chunk_symbols)

        if matched_words or matched_symbols:
            idf_sum = sum(idf[qt] for qt in matched_words)
            norm = math.sqrt(len(chunk_words)) + 2.0
            score = idf_sum / norm

            if matched_symbols:
                sym_idf_sum = sum(idf.get(qt, 2.0) for qt in matched_symbols)
                score += sym_idf_sum * 1.8

            file_lower = chunk["file"].lower()
            for qt in query_tokens:
                if qt in file_lower:
                    score += idf.get(qt, 1.0) * 0.45

            coverage = len(matched_words.union(matched_symbols)) / len(query_tokens)
            score *= (1.0 + 0.5 * coverage)

            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected = []
    for score, chunk in scored:
        is_overlapping = False
        for _, existing in selected:
            if existing["file"] == chunk["file"]:
                overlap = min(existing["end_line"], chunk["end_line"]) - max(existing["start_line"], chunk["start_line"])
                if overlap > 10:
                    is_overlapping = True
                    break
        if not is_overlapping:
            selected.append((score, chunk))
        if len(selected) >= top_k:
            break

    if not selected:
        print(f"🔍 No matching code found for: '{query}'")
        return

    print(f"\n🔍 Top {len(selected)} relevant code locations for: '{query}'\n" + "=" * 68)
    for rank, (score, item) in enumerate(selected):
        total_l = item.get("total_lines", "?")
        show_full = (mode == "full") or (mode == "smart" and rank == 0)
        tag = " [TOP MATCH - FULL SLICE]" if (mode == "smart" and rank == 0) else ""

        print(
            f"📍 {item['file']} (Lines {item['start_line']} - {item['end_line']} of {total_l})"
            f" [Score: {score:.2f}]{tag}"
        )
        view_lines = extract_chunk_view(
            root_dir, item["file"], item["start_line"], item["end_line"],
            query_tokens, full_slice=show_full, fallback_header=item.get("header", "")
        )
        for line_no, text in view_lines:
            print(f"   L{line_no:<4} | {text}")
        print("-" * 68)


def parse_cli_args(argv):
    top_k = 3
    mode = "smart"
    root_dir = "."
    query_parts = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--top", "-k") and i + 1 < len(argv):
            try:
                top_k = max(1, int(argv[i + 1]))
            except ValueError:
                pass
            i += 2
        elif arg in ("--path", "-p") and i + 1 < len(argv):
            root_dir = argv[i + 1]
            i += 2
        elif arg == "--brief":
            mode = "brief"
            i += 1
        elif arg == "--full":
            mode = "full"
            i += 1
        elif arg == "--smart":
            mode = "smart"
            i += 1
        else:
            query_parts.append(arg)
            i += 1

    return " ".join(query_parts), top_k, mode, root_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Code Memory - Zero-VRAM BM25 & Symbol Search for Cloud & Local AI Agents\n")
        print("Usage:")
        print("  python code_memory.py search <query> [--top 3] [--brief|--full] [--path .]")
        print("  python code_memory.py refs <symbol>")
        print("  python code_memory.py test")
        print("  python code_memory.py index [path]")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "test":
        import unittest
        tests_dir = Path(__file__).resolve().parent.parent / "tests"
        if not tests_dir.exists():
            tests_dir = Path("tests")
        suite = unittest.defaultTestLoader.discover(str(tests_dir), pattern="test_*.py")
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)
    elif cmd == "index":
        target_dir = sys.argv[2] if len(sys.argv) > 2 and os.path.isdir(sys.argv[2]) else "."
        build_or_update_index(target_dir, force_full=True, quiet=False)
    elif cmd == "refs":
        symbol = sys.argv[2] if len(sys.argv) > 2 else ""
        if symbol:
            search_references(symbol)
        else:
            print("❌ Please specify a symbol to find references for.")
    elif cmd == "search":
        q, k, m, r_dir = parse_cli_args(sys.argv[2:])
        search(q, top_k=k, mode=m, root_dir=r_dir)
    else:
        q, k, m, r_dir = parse_cli_args(sys.argv[1:])
        search(q, top_k=k, mode=m, root_dir=r_dir)