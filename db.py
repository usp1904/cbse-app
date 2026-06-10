"""Unified database abstraction — supports SQLite (dev) and PostgreSQL (Neon/production).

Set DATABASE_URL to switch:
  sqlite:///cbse_content.db         → SQLite (local dev, default)
  postgresql://user:pass@host/db    → PostgreSQL / Neon (production)
  postgresql+pool://user:pass@host/db  → PostgreSQL with built-in connection pool
"""
import os
import re
import json
import time
import queue
import threading
import functools
import urllib.parse

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///cbse_content.db")


def _parse_db_url(url):
    if url.startswith("sqlite:"):
        path = url.replace("sqlite:///", "").replace("sqlite://", "")
        return {"backend": "sqlite", "path": path}
    elif url.startswith("postgresql"):
        return {"backend": "postgresql", "url": url}
    return {"backend": "sqlite", "path": "cbse_content.db"}


class DatabaseError(Exception):
    pass


class ExecutionResult:
    """Wraps cursor results to provide backward-compatible fetchone/fetchall."""
    def __init__(self, cursor):
        self._cursor = cursor
        self._rows = None
        self._idx = 0

    @classmethod
    def from_pg(cls, rows, description):
        self = cls.__new__(cls)
        self._cursor = None
        self._rows = rows
        self._idx = 0
        self._description = description
        return self

    @property
    def description(self):
        if self._cursor:
            return self._cursor.description
        return self._description

    @property
    def lastrowid(self):
        if self._cursor:
            return self._cursor.lastrowid
        return None

    def fetchone(self):
        if self._rows is not None:
            if self._idx < len(self._rows):
                val = self._rows[self._idx]
                self._idx += 1
                return val
            return None
        if self._cursor:
            return self._cursor.fetchone()
        return None

    def fetchall(self):
        if self._rows is not None:
            return self._rows
        if self._cursor:
            return self._cursor.fetchall()
        return []

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


class Row(dict):
    """Dict-like row that also supports attribute access (like sqlite3.Row)."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


def _row_factory(columns, values):
    return Row(zip(columns, values)) if columns else None


class Database:
    """Thread-safe database abstraction.

    Usage:
        db = Database.get()
        rows = db.query("SELECT * FROM topics WHERE id = ?", (topic_id,))
        db.execute("UPDATE topics SET title = ? WHERE id = ?", (title, tid))
        last_id = db.insert("INSERT INTO sessions ... VALUES (...)", params)
    """

    _instances = {}
    _lock = threading.Lock()

    def __init__(self, url=None):
        self.url = url or DATABASE_URL
        self.config = _parse_db_url(self.url)
        self.backend = self.config["backend"]
        self._local = threading.local()
        self._pool = None
        self._pool_lock = threading.Lock()
        self._seq = 0
        self._write_queue = queue.Queue()
        self._writer_started = False

    @classmethod
    def get(cls, url=None):
        key = url or DATABASE_URL
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = cls(url)
            return cls._instances[key]

    def _get_sqlite_conn(self):
        import sqlite3
        if not hasattr(self._local, "conn") or self._local.conn is None:
            path = self.config["path"]
            self._local.conn = sqlite3.connect(path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-8000")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    def _row_from_sqlite(self, row, description):
        return Row((d[0], row[d[0]]) for d in description)

    def _get_pg_conn(self):
        if not hasattr(self._local, "pg_conn") or self._local.pg_conn is None:
            import psycopg2
            import psycopg2.extras
            dsn = self.config["url"]
            self._local.pg_conn = psycopg2.connect(dsn, application_name="cbse_app")
            self._local.pg_conn.autocommit = False
        return self._local.pg_conn

    def _translate_sql(self, sql):
        if self.backend == "sqlite":
            return sql
        if self.backend == "postgresql":
            s = sql.strip()
            orig_upper = sql.strip().upper()
            s = re.sub(r"(?<!')datetime\('now','localtime'(?:,'([^']+)')?\)", lambda m: self._pg_now(m), s)
            s = re.sub(r"(?<!')date\('now','localtime'(?:,'([^']+)')?\)", lambda m: self._pg_now(m, date_only=True), s)
            s = re.sub(r"datetime\('now'(?:,'([^']+)')?\)", lambda m: self._pg_now(m), s)
            s = re.sub(r"date\('now'(?:,'([^']+)')?\)", lambda m: self._pg_now(m, date_only=True), s)
            s = re.sub(r"strftime\('%s',\s*([^)]+)\)", r"EXTRACT(EPOCH FROM \1)::bigint", s)
            s = re.sub(r"strftime\('%W',\s*([^)]+)\)", r"EXTRACT(WEEK FROM \1)", s)
            s = re.sub(r"strftime\('%w',\s*([^)]+)\)", r"EXTRACT(DOW FROM \1)", s)
            s = re.sub(r"\bRANDOM\(\)", "RANDOM()", s, flags=re.IGNORECASE)
            s = re.sub(r"\brandom\(\)", "RANDOM()", s, flags=re.IGNORECASE)

            # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
            if "INSERT OR IGNORE INTO" in orig_upper:
                s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s, flags=re.IGNORECASE)
                s = s.rstrip(";") + " ON CONFLICT DO NOTHING"
                if sql.strip().endswith(";"):
                    s += ";"
            # INSERT OR REPLACE → proper ON CONFLICT DO UPDATE SET
            elif "INSERT OR REPLACE INTO" in orig_upper:
                repl_match = re.match(
                    r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES",
                    s, re.IGNORECASE
                )
                if repl_match:
                    cols = [c.strip() for c in repl_match.group(2).split(",")]
                    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)
                    s = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", s, flags=re.IGNORECASE)
                    s = s.rstrip(";") + f" ON CONFLICT DO UPDATE SET {set_clause};"
                else:
                    s = re.sub(r"INSERT OR REPLACE INTO", "INSERT INTO", s, flags=re.IGNORECASE)

            s = re.sub(r"last_insert_rowid\(\)", "LASTVAL()", s, flags=re.IGNORECASE)
            s = re.sub(r"LIKE\s+\?(\s+ESCAPE\s+'[^']*')?", r"ILIKE %s\1", s, flags=re.IGNORECASE)
            s = re.sub(r"(?<!=)\?(?!=)", "%s", s)
            s = s.replace("AUTOINCREMENT", "SERIAL")
            s = re.sub(r"CHECK\s*\(\s*id\s*=\s*1\s*\)", "", s)
            s = re.sub(r"CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP", s, flags=re.IGNORECASE)
            return s
        return sql

    def _pg_now(self, m, date_only=False):
        offset = m.group(1) if m.lastindex and m.group(1) else None
        if date_only:
            base = "CURRENT_DATE"
        else:
            base = "CURRENT_TIMESTAMP"
        if offset:
            parts = offset.strip().split()
            if len(parts) == 2 and parts[1] in ("days", "hours", "minutes", "seconds", "months", "years"):
                return f"{base} + INTERVAL '{parts[0]} {parts[1]}'"
            return base
        return base

    def _split_sql_script(self, script):
        """Split SQL script into statements, respecting string literals."""
        statements = []
        current = []
        in_string = False
        string_char = None
        for ch in script:
            if in_string:
                current.append(ch)
                if ch == string_char and current[-2:-1] != ['\\']:
                    in_string = False
                    string_char = None
            elif ch in ("'", '"'):
                current.append(ch)
                in_string = True
                string_char = ch
            elif ch == ';':
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(ch)
        remaining = ''.join(current).strip()
        if remaining:
            statements.append(remaining)
        return statements

    def _translate_params(self, sql, params):
        if self.backend == "sqlite":
            return sql, params
        if self.backend == "postgresql":
            if params is None:
                return sql, None
            if isinstance(params, (list, tuple)):
                return sql, tuple(params)
            return sql, params

    def execute(self, sql, params=None):
        if params is not None and not isinstance(params, (list, tuple)):
            params = (params,)
        sql = self._translate_sql(sql)
        sql, params = self._translate_params(sql, params)
        try:
            if self.backend == "sqlite":
                conn = self._get_sqlite_conn()
                if params:
                    cur = conn.execute(sql, params)
                else:
                    cur = conn.execute(sql)
                conn.commit()
                return ExecutionResult(cur)
            else:
                conn = self._get_pg_conn()
                with conn.cursor() as cur:
                    if params:
                        cur.execute(sql, params)
                    else:
                        cur.execute(sql)
                    result = list(cur.fetchall()) if cur.description else []
                    conn.commit()
                    return ExecutionResult.from_pg(result, cur.description)
        except Exception as e:
            raise DatabaseError(f"execute failed: {e}\nSQL: {sql}\nParams: {params}") from e

    def executemany(self, sql, params_list):
        if not params_list:
            return
        sql = self._translate_sql(sql)
        try:
            if self.backend == "sqlite":
                conn = self._get_sqlite_conn()
                conn.executemany(sql, params_list)
                conn.commit()
            else:
                conn = self._get_pg_conn()
                with conn.cursor() as cur:
                    for params in params_list:
                        pg_sql, pg_params = self._translate_params(sql, params)
                        cur.execute(pg_sql, pg_params)
                conn.commit()
        except Exception as e:
            raise DatabaseError(f"executemany failed: {e}") from e

    def executescript(self, script):
        if self.backend == "sqlite":
            conn = self._get_sqlite_conn()
            conn.executescript(script)
            conn.commit()
        else:
            for stmt in self._split_sql_script(script):
                if not stmt.strip():
                    continue
                upper = stmt.strip().upper()
                if upper.startswith("CREATE TRIGGER"):
                    continue
                if "VIRTUAL TABLE" in upper or "FTS5" in upper:
                    continue
                if upper.startswith("PRAGMA"):
                    continue
                self.execute(stmt)

    def query(self, sql, params=None):
        if params is not None and not isinstance(params, (list, tuple)):
            params = (params,)
        sql = self._translate_sql(sql)
        sql, params = self._translate_params(sql, params)
        try:
            if self.backend == "sqlite":
                conn = self._get_sqlite_conn()
                if params:
                    cur = conn.execute(sql, params)
                else:
                    cur = conn.execute(sql)
                return [self._row_from_sqlite(row, cur.description) for row in cur.fetchall()]
            else:
                conn = self._get_pg_conn()
                with conn.cursor() as cur:
                    if params:
                        cur.execute(sql, params)
                    else:
                        cur.execute(sql)
                    if cur.description:
                        cols = [d[0] for d in cur.description]
                        return [Row(zip(cols, row)) for row in cur.fetchall()]
                    return []
        except Exception as e:
            raise DatabaseError(f"query failed: {e}\nSQL: {sql}\nParams: {params}") from e

    def query_one(self, sql, params=None):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def insert(self, sql, params=None):
        if params is not None and not isinstance(params, (list, tuple)):
            params = (params,)
        sql = self._translate_sql(sql)
        sql, params = self._translate_params(sql, params)
        try:
            if self.backend == "sqlite":
                conn = self._get_sqlite_conn()
                if params:
                    cur = conn.execute(sql, params)
                else:
                    cur = conn.execute(sql)
                conn.commit()
                return cur.lastrowid
            else:
                conn = self._get_pg_conn()
                if "RETURNING" not in sql.upper():
                    sql += " RETURNING id"
                with conn.cursor() as cur:
                    if params:
                        cur.execute(sql, params)
                    else:
                        cur.execute(sql)
                    conn.commit()
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            raise DatabaseError(f"insert failed: {e}\nSQL: {sql}\nParams: {params}") from e

    def commit(self):
        pass

    def cursor(self):
        return self

    def close(self):
        if self.backend == "sqlite":
            if hasattr(self._local, "conn") and self._local.conn:
                self._local.conn.close()
                self._local.conn = None
        else:
            if hasattr(self._local, "pg_conn") and self._local.pg_conn:
                self._local.pg_conn.close()
                self._local.pg_conn = None

    @property
    def is_postgresql(self):
        return self.backend == "postgresql"

    @property
    def is_sqlite(self):
        return self.backend == "sqlite"

    def count(self, sql, params=None):
        row = self.query_one(sql, params)
        if row:
            vals = list(row.values())
            return vals[0] if vals else 0
        return 0

    def table_exists(self, table_name):
        if self.backend == "sqlite":
            return bool(self.query_one(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            ))
        else:
            return bool(self.query_one(
                "SELECT table_name FROM information_schema.tables WHERE table_name=%s",
                (table_name,)
            ))

_db = None


def get_db():
    global _db
    if _db is None:
        _db = Database.get()
    return _db


def init_db_from_schema(schema_sql, triggers_sql=None):
    db = get_db()
    if db.backend == "sqlite":
        db.executescript(schema_sql)
        if triggers_sql:
            db.executescript(triggers_sql)
    else:
        db.executescript(schema_sql)
    db.execute("INSERT INTO learner (id, name, xp, level, streak, lives, max_lives) "
               "VALUES (1, 'Learner', 0, 1, 0, 5, 5) "
               "ON CONFLICT (id) DO NOTHING") if db.backend == "postgresql" else \
        db.execute("INSERT OR IGNORE INTO learner (id, name, xp, level, streak, lives, max_lives) "
                   "VALUES (1, 'Learner', 0, 1, 0, 5, 5)")


def rebuild_fts(db):
    if db.backend != "sqlite":
        return
    count = db.count("SELECT COUNT(*) FROM chunks")
    fts_count = db.count("SELECT COUNT(*) FROM chunks_fts")
    if count > 0 and fts_count == 0:
        db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
