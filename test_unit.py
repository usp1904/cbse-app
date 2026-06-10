#!/usr/bin/env python3
"""Unit tests for db.py and server.py core functions.

Usage:
    python3 test_unit.py [-v]
"""
import unittest
import sys
import os
import json
import tempfile
import types

# Mock modules not available in test environment
_fake_mods = {}
for _mod_name in ['fastapi', 'fastapi.responses', 'fastapi.middleware',
                  'fastapi.middleware.cors', 'fastapi.middleware.gzip',
                  'fastapi.middleware.trustedhost', 'pydantic',
                  'rag_engine', 'llm_client', 'chunking', 'data',
                  'ai_services', 'content_enricher', 'gamification',
                  'interactives', 'ai_tutor', 'database']:
    if _mod_name not in sys.modules:
        _m = types.ModuleType(_mod_name)
        # Add common exports for FastAPI/pydantic
        _m.FastAPI = type('FastAPI', (), {})
        _m.Request = type('Request', (), {})
        _m.Response = type('Response', (), {})
        _m.Query = type('Query', (), {})
        _m.HTTPException = type('HTTPException', (Exception,), {})
        _m.JSONResponse = type('JSONResponse', (), {})
        _m.HTMLResponse = type('HTMLResponse', (), {})
        _m.FileResponse = type('FileResponse', (), {})
        _m.PlainTextResponse = type('PlainTextResponse', (), {})
        _m.CORSMiddleware = type('CORSMiddleware', (), {})
        _m.GZipMiddleware = type('GZipMiddleware', (), {})
        _m.TrustedHostMiddleware = type('TrustedHostMiddleware', (), {})
        _m.BaseModel = type('BaseModel', (), {})
        _m.Field = type('Field', (), {})
        sys.modules[_mod_name] = _m
        _fake_mods[_mod_name] = _m


class TestDbTranslation(unittest.TestCase):
    """Test the SQL translation layer in db.py."""

    def setUp(self):
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    def _make_db(self, backend="sqlite"):
        import db
        db._db = None
        db.DATABASE_URL = "sqlite:///:memory:" if backend == "sqlite" else "postgresql://localhost/test"
        instance = db.Database()
        instance.backend = backend
        return instance

    def test_sqlite_passthrough(self):
        inst = self._make_db("sqlite")
        sql = "SELECT * FROM topics WHERE id = ?"
        self.assertEqual(inst._translate_sql(sql), sql)

    def test_postgres_question_mark(self):
        inst = self._make_db("postgresql")
        sql = "SELECT * FROM topics WHERE id = ? AND name = ?"
        result = inst._translate_sql(sql)
        self.assertNotIn("?", result)
        self.assertIn("%s", result)

    def test_postgres_datetime_now(self):
        inst = self._make_db("postgresql")
        sql = "SELECT * FROM xp_events WHERE created_at >= datetime('now','-90 days')"
        result = inst._translate_sql(sql)
        self.assertNotIn("datetime(", result, msg="datetime() should be translated")
        self.assertIn("CURRENT_TIMESTAMP", result)

    def test_postgres_date_now(self):
        inst = self._make_db("postgresql")
        sql = "SELECT * FROM xp_events WHERE created_at >= date('now','-30 days')"
        result = inst._translate_sql(sql)
        self.assertNotIn("date('now'", result)
        self.assertIn("CURRENT_DATE", result)

    def test_postgres_strftime(self):
        inst = self._make_db("postgresql")
        sql = "SELECT strftime('%s', created_at) FROM xp_events"
        result = inst._translate_sql(sql)
        self.assertIn("EXTRACT(EPOCH FROM created_at)", result)

    def test_postgres_random(self):
        inst = self._make_db("postgresql")
        sql = "SELECT * FROM chunks ORDER BY random() LIMIT 5"
        result = inst._translate_sql(sql)
        self.assertNotIn("random()", result)
        self.assertIn("RANDOM()", result)

    def test_postgres_last_insert_rowid(self):
        inst = self._make_db("postgresql")
        sql = "SELECT last_insert_rowid()"
        result = inst._translate_sql(sql)
        self.assertIn("LASTVAL()", result)

    def test_postgres_insert_or_ignore(self):
        inst = self._make_db("postgresql")
        sql = "INSERT OR IGNORE INTO learner (id, name) VALUES (1, 'Test')"
        result = inst._translate_sql(sql)
        self.assertNotIn("OR IGNORE", result)
        self.assertIn("ON CONFLICT DO NOTHING", result)

    def test_postgres_insert_or_replace(self):
        inst = self._make_db("postgresql")
        sql = "INSERT OR REPLACE INTO sessions (token, learner_id) VALUES ('abc', 1)"
        result = inst._translate_sql(sql)
        self.assertNotIn("OR REPLACE", result)
        self.assertIn("ON CONFLICT DO UPDATE SET", result)

    def test_postgres_autoincrement(self):
        inst = self._make_db("postgresql")
        sql = "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)"
        result = inst._translate_sql(sql)
        self.assertNotIn("AUTOINCREMENT", result)
        self.assertIn("SERIAL", result)

    def test_postgres_like(self):
        inst = self._make_db("postgresql")
        sql = "SELECT * FROM topics WHERE title LIKE ?"
        result = inst._translate_sql(sql)
        self.assertIn("ILIKE", result)
        self.assertNotIn(" LIKE ", result)

    def test_postgres_check_id_removed(self):
        inst = self._make_db("postgresql")
        sql = "CREATE TABLE learner (id INTEGER PRIMARY KEY CHECK (id = 1))"
        result = inst._translate_sql(sql)
        self.assertNotIn("CHECK", result)

    def test_split_sql_script_basic(self):
        inst = self._make_db("sqlite")
        script = "SELECT 1; SELECT 2;"
        parts = inst._split_sql_script(script)
        self.assertEqual(len(parts), 2)

    def test_split_sql_script_with_strings(self):
        inst = self._make_db("sqlite")
        script = "INSERT INTO t (v) VALUES ('hello; world'); SELECT 1"
        parts = inst._split_sql_script(script)
        self.assertEqual(len(parts), 2)

    def test_split_sql_script_no_semicolon(self):
        inst = self._make_db("sqlite")
        script = "SELECT 1"
        parts = inst._split_sql_script(script)
        self.assertEqual(len(parts), 1)

    def test_split_sql_script_empty(self):
        inst = self._make_db("sqlite")
        parts = inst._split_sql_script("")
        self.assertEqual(len(parts), 0)

    def test_translate_params_tuple(self):
        inst = self._make_db("postgresql")
        sql, params = inst._translate_params("SELECT * FROM t WHERE id = ?", (1,))
        self.assertIsInstance(params, tuple)

    def test_translate_params_list(self):
        inst = self._make_db("postgresql")
        sql, params = inst._translate_params("SELECT * FROM t WHERE id = ?", [1])
        self.assertIsInstance(params, tuple)


def _extract_from_server(func_names):
    """Extract pure functions from server.py without importing its non-standard deps."""
    import ast, types
    src = open("/home/windows/cbse-app/server.py", "r").read()
    tree = ast.parse(src)
    fns = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in func_names:
            # Build a minimal namespace with required imports
            ns = {
                're': __import__('re'),
                'htmlmod': __import__('html'),
                'random': __import__('random'),
                'json': __import__('json'),
                'hashlib': __import__('hashlib'),
                'os': __import__('os'),
                'time': __import__('time'),
            }
            exec(compile(ast.Module([node], type_ignores=[]), "<ast>", "exec"), ns)
            fns[node.name] = ns[node.name]
    return fns

_server_fns = _extract_from_server({'format_content', 'esc_js', '_build_breadcrumb'})

class TestServerFormatContent(unittest.TestCase):
    """Test the format_content function from server.py."""

    def setUp(self):
        self.fmt = _server_fns['format_content']

    def test_none_input(self):
        self.assertEqual(self.fmt(None), "")

    def test_empty_input(self):
        self.assertEqual(self.fmt(""), "")

    def test_plain_text(self):
        result = self.fmt("hello world")
        self.assertIn("<p>", result)
        self.assertIn("hello world", result)

    def test_math_dollar(self):
        result = self.fmt("Formula: $$E=mc^2$$")
        self.assertIn('class="math"', result)
        self.assertIn("E=mc^2", result)

    def test_image_markdown(self):
        result = self.fmt("![alt](img.png)")
        self.assertIn('<img src="img.png"', result)

    def test_ordered_list(self):
        result = self.fmt("1. First\n2. Second")
        self.assertIn("<ol>", result)
        self.assertIn("<li>First</li>", result)
        self.assertIn("<li>Second</li>", result)
        self.assertIn("</ol>", result)

    def test_unordered_list(self):
        result = self.fmt("- Item 1\n- Item 2")
        self.assertIn("<ul>", result)
        self.assertIn("<li>Item 1</li>", result)
        self.assertIn("</ul>", result)

    def test_heading(self):
        result = self.fmt("# Title")
        self.assertIn("<h3>", result)
        self.assertIn("Title", result)
        self.assertIn("</h3>", result)

    def test_html_escaping(self):
        result = self.fmt("<script>alert('xss')</script>")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)


class TestServerHelpers(unittest.TestCase):
    """Test helper functions from server.py."""

    def setUp(self):
        self.esc_js = _server_fns['esc_js']
        self.bc = _server_fns['_build_breadcrumb']

    def test_esc_js_none(self):
        self.assertEqual(self.esc_js(None), "")

    def test_esc_js_quotes(self):
        result = self.esc_js("it's a test")
        self.assertIn("\\'", result)

    def test_esc_js_newlines(self):
        result = self.esc_js("line1\nline2")
        self.assertIn("\\n", result)
        self.assertNotIn("\n", result)

    def test_breadcrumb_simple(self):
        result = self.bc([("Home", "/"), ("Page", None)])
        self.assertIn("/", result)
        self.assertIn("Home", result)
        self.assertIn("Page", result)


if __name__ == "__main__":
    unittest.main(verbosity=2 if "-v" in sys.argv else 1)
