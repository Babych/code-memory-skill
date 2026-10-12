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
from pathlib import Path

# Enforce UTF-8 output across Windows and POSIX shells
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

INDEX_FILE = Path(".code_index.json")
DEFAULT_EXTS = {".js", ".ts", ".html", ".py", ".sql", ".md", ".json", ".vue", ".jsx", ".tsx", ".css"}
DEFAULT_IGNORE = {".git", "node_modules", ".gemini", "dist", "build", ".wrangler", "__pycache__", ".venv", "venv"}

def tokenize(text):
    """Splits camelCase, snake_case, identifiers, and multilingual words."""
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    tokens = re.findall(r'[a-zA-Z0-9_\u0400-\u04FF]+', text.lower())
    return [t for t in tokens if len(t) > 1]

def build_index(root_dir="."):
    """Recursively scans repository files and builds a lightweight BM25-like chunk index."""
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
                step = 25
                chunk_size = 40
                for i in range(0, max(1, len(lines)), step):
                    chunk_lines = lines[i:i + chunk_size]
                    if not chunk_lines:
                        continue
                    chunk_text = "\n".join(chunk_lines)
                    words = tokenize(chunk_text)
                    if not words:
                        continue
                    chunks.append({
                        "file": str(path.as_posix()),
                        "start_line": i + 1,
                        "end_line": min(len(lines), i + chunk_size),
                        "words": list(set(words)),
                        "preview": "\n".join(chunk_lines[:4])
                    })
            except Exception:
                pass

    INDEX_FILE.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Indexed {len(chunks)} code chunks into {INDEX_FILE} (Ready for fast search).")

def search(query, top_k=5):
    """Performs fast sparse-vector retrieval to return exact file locations and line ranges."""
    if not INDEX_FILE.exists():
        build_index()
    
    try:
        chunks = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to read index: {e}")
        return

    query_tokens = set(tokenize(query))
    if not query_tokens:
        print("❌ Query is empty.")
        return

    scored = []
    for chunk in chunks:
        chunk_words = set(chunk["words"])
        match_count = len(query_tokens.intersection(chunk_words))
        if match_count > 0:
            score = match_count / (math.sqrt(len(chunk_words)) + 1e-5)
            # Boost matches in file path
            for qt in query_tokens:
                if qt in chunk["file"].lower():
                    score += 0.5
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
        print("  python code_memory.py index           (Rebuild local index)")
        print("  python code_memory.py search <query>  (Find exact code chunks and line ranges)")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "index":
        build_index()
    elif cmd == "search":
        q = " ".join(sys.argv[2:])
        search(q)
    else:
        q = " ".join(sys.argv[1:])
        search(q)
