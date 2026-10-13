#!/usr/bin/env python3
"""
Code Memory: Zero-dependency local vector & symbol search for AI coding agents.
Optimized for token reduction during large codebase refactoring.
Author: Dmytro Babych (https://github.com/babych/code-memory-skill)
License: MIT (c) 2026 Dmytro Babych
"""

import os
import sys
import json
import math
import re
import subprocess
from pathlib import Path

# Enforce UTF-8 output across Windows and POSIX shells
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

INDEX_FILE = Path(".code_index.json")
DEFAULT_EXTS = {".js", ".ts", ".html", ".py", ".sql", ".md", ".json", ".vue", ".jsx", ".tsx", ".css", ".dart", ".cs"}
DEFAULT_IGNORE = {".git", "node_modules", ".gemini", "dist", "build", ".wrangler", "__pycache__", ".venv", "venv"}

# Common top-level definition starters across Dart, C#, Python, JS/TS, etc.
DEF_PATTERN = re.compile(r'^\s*(class|abstract\s+class|interface|enum|def|function|async\s+function|void|Widget|Future<|Task<|public|private|protected|static|export)\s+([A-Za-z0-9_]+)', re.MULTILINE)

def tokenize(text):
    """Splits camelCase, snake_case, identifiers, and multilingual words."""
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    tokens = re.findall(r'[a-zA-Z0-9_\u0400-\u04FF]+', text.lower())
    return [t for t in tokens if len(t) > 1]

def get_git_head(root_dir="."):
    """Returns current git commit hash if available, else empty string."""
    try:
        res = subprocess.run(
            ["git", "-C", root_dir, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""

def build_index(root_dir="."):
    """Recursively scans repository files and builds an AST-aligned chunk index with git tracking."""
    print(f"[CodeMemory] Scanning codebase at '{root_dir}'...")
    root = Path(root_dir)
    chunks = []
    
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in DEFAULT_EXTS:
            if any(ignored in path.parts for ignored in DEFAULT_IGNORE):
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                n_lines = len(lines)
                if n_lines == 0:
                    continue

                # Locate all definition line indices to snap chunk boundaries
                def_indices = [i for i, line in enumerate(lines) if DEF_PATTERN.match(line)]
                def_set = set(def_indices)

                step = 25
                chunk_size = 45
                i = 0
                while i < n_lines:
                    # Snap chunk start to definition if one is nearby within +/- 4 lines
                    start_line = i
                    for offset in range(-4, 5):
                        candidate = i + offset
                        if 0 <= candidate < n_lines and candidate in def_set:
                            start_line = candidate
                            break

                    end_line = min(n_lines, start_line + chunk_size)
                    chunk_lines = lines[start_line:end_line]
                    if chunk_lines:
                        chunk_text = "\n".join(chunk_lines)
                        words = tokenize(chunk_text)
                        if words:
                            # Extract and tokenize symbol names in this chunk for extra boost
                            symbols = []
                            for m in DEF_PATTERN.finditer(chunk_text):
                                symbols.extend(tokenize(m.group(2)))
                            chunks.append({
                                "file": str(path.as_posix()),
                                "start_line": start_line + 1,
                                "end_line": end_line,
                                "words": list(set(words)),
                                "symbols": list(set(symbols)),
                                "preview": "\n".join(chunk_lines[:3])
                            })
                    i = start_line + step
            except Exception:
                pass

    meta = {
        "git_head": get_git_head(root_dir),
        "chunks": chunks
    }
    INDEX_FILE.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Indexed {len(chunks)} code chunks into {INDEX_FILE} (Ready for fast search).")

def search(query, top_k=5, root_dir="."):
    """Performs fast sparse-vector retrieval with symbol boosting and git branch auto-refresh."""
    current_git_head = get_git_head(root_dir)

    # Check if index exists and is up-to-date with current git branch/commit
    needs_rebuild = not INDEX_FILE.exists()
    chunks = []
    if not needs_rebuild:
        try:
            raw = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "chunks" in raw:
                # If git branch or commit changed, auto-refresh transparently
                if current_git_head and raw.get("git_head") != current_git_head:
                    print("[CodeMemory] Git branch/commit changed. Auto-refreshing index...")
                    needs_rebuild = True
                else:
                    chunks = raw["chunks"]
            elif isinstance(raw, list):
                chunks = raw
        except Exception:
            needs_rebuild = True

    if needs_rebuild:
        build_index(root_dir)
        try:
            raw = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            chunks = raw["chunks"] if isinstance(raw, dict) else raw
        except Exception as e:
            print(f"❌ Failed to read index: {e}")
            return

    query_tokens = set(tokenize(query))
    if not query_tokens:
        print("❌ Query is empty.")
        return

    scored = []
    for chunk in chunks:
        chunk_words = set(chunk.get("words", []))
        chunk_symbols = set(chunk.get("symbols", []))
        
        match_count = len(query_tokens.intersection(chunk_words))
        if match_count > 0:
            score = match_count / (math.sqrt(len(chunk_words)) + 1e-5)
            
            # Massive boost if the query targets an exact defined symbol (class, method)
            symbol_matches = len(query_tokens.intersection(chunk_symbols))
            if symbol_matches > 0:
                score += (symbol_matches * 2.5)

            # Boost matches in file path
            for qt in query_tokens:
                if qt in chunk["file"].lower():
                    score += 0.8
                    
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = scored[:top_k]

    if not results:
        print(f"🔍 No matching code found for: '{query}'")
        return

    print(f"\n🔍 Top {len(results)} relevant code locations for: '{query}'\n" + "="*60)
    for score, item in results:
        print(f"📍 {item['file']} (Lines {item['start_line']} - {item['end_line']}) [Score: {score:.3f}]")
        for line in item['preview'].splitlines()[:3]:
            print(f"   | {line.strip()[:100]}")
        print("-" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Code Memory - Token-Saving Search for AI Agents\n")
        print("Usage:")
        print("  python code_memory.py index [path]          (Rebuild local index)")
        print("  python code_memory.py search <query>        (Find exact code chunks and line ranges)")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    target_dir = sys.argv[2] if len(sys.argv) > 2 and os.path.isdir(sys.argv[2]) else "."
    
    if cmd == "index":
        build_index(target_dir)
    elif cmd == "search":
        q = " ".join(sys.argv[2:])
        search(q, root_dir=".")
    else:
        q = " ".join(sys.argv[1:])
        search(q, root_dir=".")
