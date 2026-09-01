"""A very small wrapper over the database connection."""
import sqlite3

from config import load_settings


def connect():
    """Open a connection using the configured database path."""
    settings = load_settings()
    conn = sqlite3.connect(settings["db_path"])
    conn.row_factory = sqlite3.Row
    return conn


def execute(sql, params=()):
    """Run a statement that does not return rows."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()
    return cur.lastrowid


def fetch_one(sql, params=()):
    """Return a single row as a dict, or None."""
    conn = connect()
    row = conn.cursor().execute(sql, params).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_all(sql, params=()):
    """Return every matching row as a list of dicts."""
    conn = connect()
    rows = conn.cursor().execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_row(table, values):
    """Insert a mapping of column -> value and return the new row id."""
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    sql = "INSERT INTO {} ({}) VALUES ({})".format(table, columns, placeholders)
    return execute(sql, tuple(values.values()))


def update_row(table, row_id, values):
    """Update one row by id and return the number of columns written."""
    assignments = ", ".join("{} = ?".format(c) for c in values)
    sql = "UPDATE {} SET {} WHERE id = ?".format(table, assignments)
    execute(sql, tuple(values.values()) + (row_id,))
    return len(values)


def delete_row(table, row_id):
    """Delete one row by id."""
    execute("DELETE FROM {} WHERE id = ?".format(table), (row_id,))
    return True
