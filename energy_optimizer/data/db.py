"""
Database connection helper for Energy Optimizer Agent.
Phase 1: Single file database, per-query connections for thread safety.

Uses DuckDB when available (production), falls back to SQLite (stdlib) for environments
where DuckDB cannot be installed.
"""

import os
import sqlite3

# Try to use DuckDB; fall back to SQLite
try:
    import duckdb
    DB_ENGINE = "duckdb"
except ImportError:
    DB_ENGINE = "sqlite"

import tempfile

DB_FILE = os.environ.get(
    "ENERGY_DB_PATH",
    os.path.join(tempfile.gettempdir(), "energy_optimizer.duckdb" if DB_ENGINE == "duckdb" else "energy_optimizer.db"),
)


def get_conn():
    """Get a new database connection (thread-safe pattern)."""
    if DB_ENGINE == "duckdb":
        return duckdb.connect(DB_FILE)
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn


def query(sql: str, params: list = None) -> list[dict]:
    """Execute a SELECT query and return results as list of dicts."""
    con = get_conn()
    try:
        if DB_ENGINE == "duckdb":
            if params:
                result = con.execute(sql, params)
            else:
                result = con.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        else:
            cursor = con.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    finally:
        con.close()


def query_single(sql: str, params: list = None) -> dict | None:
    """Execute a query and return first row as dict, or None."""
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: list = None):
    """Execute a non-SELECT statement (INSERT, CREATE, etc.)."""
    con = get_conn()
    try:
        if DB_ENGINE == "duckdb":
            if params:
                con.execute(sql, params)
            else:
                con.execute(sql)
        else:
            cursor = con.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            con.commit()
    finally:
        con.close()


def reset_db():
    """Remove the database file entirely (dev reset)."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)


def get_engine_info() -> str:
    """Return which DB engine is active."""
    return f"{DB_ENGINE} (file: {DB_FILE})"
