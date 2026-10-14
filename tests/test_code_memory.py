#!/usr/bin/env python3
"""
Unit tests for Zero-Hop Code Skill (code_memory.py).
Zero external dependencies - runs on standard library `unittest`.
"""

import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import code_memory


class TestTokenizer(unittest.TestCase):
    def test_camel_case_and_pascal_case(self):
        tokens = code_memory.tokenize("userAuthenticationService")
        self.assertIn("user", tokens)
        self.assertIn("authentication", tokens)
        self.assertIn("service", tokens)

        tokens_pascal = code_memory.tokenize("OrderProcessingPipeline")
        self.assertIn("order", tokens_pascal)
        self.assertIn("processing", tokens_pascal)
        self.assertIn("pipeline", tokens_pascal)

    def test_acronym_splitting(self):
        tokens = code_memory.tokenize("JWTTokenValidator")
        self.assertIn("jwt", tokens)
        self.assertIn("token", tokens)
        self.assertIn("validator", tokens)

    def test_snake_case_and_kebab(self):
        tokens = code_memory.tokenize("fetch_user_balance-v2")
        self.assertIn("fetch", tokens)
        self.assertIn("user", tokens)
        self.assertIn("balance", tokens)
        self.assertIn("v2", tokens)

    def test_cyrillic_support(self):
        tokens = code_memory.tokenize("обробкаПлатежу_сервіс")
        self.assertIn("обробка", tokens)
        self.assertIn("платежу", tokens)
        self.assertIn("сервіс", tokens)

    def test_stopwords_removal(self):
        tokens_with = code_memory.tokenize("return this string for with", remove_stopwords=True)
        self.assertEqual(tokens_with, [])

        tokens_without = code_memory.tokenize("return this string", remove_stopwords=False)
        self.assertEqual(tokens_without, ["return", "this", "string"])


class TestSymbolExtraction(unittest.TestCase):
    def test_type_definitions(self):
        lines = [
            "export class OrderManager {",
            "interface IUserRepository {",
            "public enum TransactionStatus {",
            "struct Point2D {",
            "record CustomerDto(string Name);",
            "abstract class BaseEngine {",
        ]
        def_indices, line_symbols = code_memory.extract_symbols_and_def_lines(lines)
        self.assertEqual(len(def_indices), 6)
        self.assertIn("ordermanager", line_symbols[0])
        self.assertIn("iuserrepository", line_symbols[1])
        self.assertIn("transactionstatus", line_symbols[2])
        self.assertIn("point2d", line_symbols[3])
        self.assertIn("customerdto", line_symbols[4])
        self.assertIn("baseengine", line_symbols[5])

    def test_multilingual_functions(self):
        lines = [
            "  async def fetch_user_data(user_id: int):",
            "export async function verifyRefreshToken(token: string) {",
            "pub async fn process_queue(&self) -> Result<()> {",
            "func (s *Server) HandleConnection(conn net.Conn) {",
            "public async Task<IActionResult> GetOrderById(int id) {",
            "Widget build(BuildContext context) {",
        ]
        def_indices, line_symbols = code_memory.extract_symbols_and_def_lines(lines)
        self.assertEqual(len(def_indices), 6)
        self.assertIn("fetch_user_data", line_symbols[0])
        self.assertIn("verifyrefreshtoken", line_symbols[1])
        self.assertIn("process_queue", line_symbols[2])
        self.assertIn("handleconnection", line_symbols[3])
        self.assertIn("getorderbyid", line_symbols[4])
        self.assertIn("build", line_symbols[5])

    def test_control_keywords_excluded(self):
        lines = [
            "if (user != null) {",
            "for (int i = 0; i < 10; i++) {",
            "while (true) {",
            "switch (status) {",
        ]
        def_indices, _ = code_memory.extract_symbols_and_def_lines(lines)
        self.assertEqual(len(def_indices), 0)


class TestBoundarySnapping(unittest.TestCase):
    def test_leading_decorators(self):
        lines = [
            "// comment",
            "[HttpPost]",
            "[Authorize]",
            "public IActionResult SubmitOrder() {"
        ]
        start = code_memory.include_leading_decorators(lines, 3)
        self.assertEqual(start, 1)

    def test_python_decorator(self):
        lines = [
            "# helper comment",
            "@app.post('/api/login')",
            "async def login_route():"
        ]
        start = code_memory.include_leading_decorators(lines, 2)
        self.assertEqual(start, 1)

    def test_brace_balancing_with_strings_and_comments(self):
        lines = [
            "function calculateTotal(items) {",
            "    const msg = 'Testing {brace inside string}'; // and {in comment}",
            "    if (items.length > 0) {",
            "        return items.reduce((a, b) => a + b, 0);",
            "    }",
            "    return 0;",
            "}",
            "",
            "function nextFunction() {"
        ]
        def_set = {0, 8}
        end_line = code_memory.compute_smart_end_line(lines, 0, 0, def_set, is_python=False, min_size=5)
        self.assertEqual(end_line, 7)

    def test_python_indentation_snapping(self):
        lines = [
            "def calculate_tax(amount):",
            "    if amount <= 0:",
            "        return 0",
            "    rate = 0.2",
            "    return amount * rate",
            "",
            "def another_helper():",
            "    pass"
        ]
        def_set = {0, 6}
        end_line = code_memory.compute_smart_end_line(lines, 0, 0, def_set, is_python=True, min_size=4)
        self.assertEqual(end_line, 6)


class TestChunkingAndIndexing(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_chunking_definition_anchored(self):
        sample_code = (
            "import os\n\n"
            "class AuthService:\n"
            "    def __init__(self, key):\n"
            "        self.key = key\n\n"
            "    def verify_token(self, token):\n"
            "        if not token:\n"
            "            return False\n"
            "        return token == self.key\n"
        )
        test_file = Path(self.temp_dir) / "auth.py"
        test_file.write_text(sample_code, encoding="utf-8")

        chunks = code_memory.chunk_single_file(test_file, "auth.py")
        self.assertGreaterEqual(len(chunks), 1)

        words_in_chunks = [w for c in chunks for w in c["words"]]
        self.assertIn("verify", words_in_chunks)
        self.assertIn("authservice", words_in_chunks)

    def test_flat_file_fallback(self):
        sample_sql = "\n".join([f"CREATE TABLE table_{i} (id INT, name VARCHAR(50));" for i in range(120)])
        test_file = Path(self.temp_dir) / "schema.sql"
        test_file.write_text(sample_sql, encoding="utf-8")

        chunks = code_memory.chunk_single_file(test_file, "schema.sql")
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]["file"], "schema.sql")

    def test_incremental_delta_indexing(self):
        f1 = Path(self.temp_dir) / "service.py"
        f1.write_text("def service_one():\n    return 'one'\n", encoding="utf-8")

        f2 = Path(self.temp_dir) / "helper.py"
        f2.write_text("def helper_two():\n    return 'two'\n", encoding="utf-8")

        # First build
        chunks1 = code_memory.build_or_update_index(self.temp_dir, force_full=False, quiet=True)
        self.assertEqual(len(chunks1), 2)

        # Re-run without changes -> 0 updates
        chunks2 = code_memory.build_or_update_index(self.temp_dir, force_full=False, quiet=True)
        self.assertEqual(len(chunks2), 2)

        # Update only f1
        f1.write_text("def service_one_modified():\n    return 'one_v2'\n", encoding="utf-8")
        chunks3 = code_memory.build_or_update_index(self.temp_dir, force_full=False, quiet=True)
        self.assertEqual(len(chunks3), 2)

        all_words = [w for c in chunks3 for w in c["words"]]
        self.assertIn("modified", all_words)


class TestZeroHopExtractView(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_path = Path(self.temp_dir) / "example.ts"
        self.code = (
            "export async function verifyToken(token: string) {\n"
            "    const decoded = jwt.verify(token, SECRET);\n"
            "    if (Date.now() >= decoded.exp * 1000) {\n"
            "        throw new Error('Expired');\n"
            "    }\n"
            "    return decoded;\n"
            "}\n"
        )
        self.file_path.write_text(self.code, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_top1_full_slice_preserves_lines_and_line_numbers(self):
        query_tokens = {"token", "expired"}
        view = code_memory.extract_chunk_view(
            self.temp_dir, "example.ts", 1, 7, query_tokens, full_slice=True
        )
        self.assertEqual(len(view), 7)
        self.assertEqual(view[0], (1, "export async function verifyToken(token: string) {"))
        self.assertEqual(view[3], (4, "        throw new Error('Expired');"))

    def test_compact_preview_for_non_top1(self):
        query_tokens = {"expired"}
        view = code_memory.extract_chunk_view(
            self.temp_dir, "example.ts", 1, 7, query_tokens, full_slice=False
        )
        self.assertLessEqual(len(view), 4)
        preview_text = " ".join(t for _, t in view)
        self.assertIn("Expired", preview_text)


if __name__ == "__main__":
    unittest.main()
