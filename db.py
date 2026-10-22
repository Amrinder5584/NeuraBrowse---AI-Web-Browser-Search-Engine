"""SQLite data layer: schema, connection handling and all queries.

Every function takes an open connection so it is easy to unit-test.
"""
import os
import sqlite3
import time

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sites (            -- curated local search index
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords    TEXT NOT NULL,
    category    TEXT NOT NULL,
    base_score  REAL NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS searches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    query        TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS search_results (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id INTEGER NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    url       TEXT NOT NULL,
    title     TEXT NOT NULL,
    snippet   TEXT NOT NULL DEFAULT '',
    source    TEXT NOT NULL,
    rank      INTEGER NOT NULL,
    score     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_answers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id  INTEGER NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    answer     TEXT NOT NULL,
    mode       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clicks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    search_id  INTEGER REFERENCES searches(id) ON DELETE SET NULL,
    url        TEXT NOT NULL,
    title      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url        TEXT NOT NULL,
    title      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, url)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pages (            -- reader-mode cache
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    url        TEXT NOT NULL UNIQUE,
    title      TEXT NOT NULL,
    text       TEXT NOT NULL,
    fetched_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_results_search ON search_results(search_id);
CREATE INDEX IF NOT EXISTS idx_clicks_url     ON clicks(url);
CREATE INDEX IF NOT EXISTS idx_searches_user  ON searches(user_id);
"""


# --------------------------------------------------------------------------- setup
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app):
    """Create tables and seed the local index on first run."""
    from seed_data import SITES

    path = app.config["DATABASE"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO sites (url, title, description, keywords, category, base_score) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            SITES,
        )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- users
def create_user(conn, username, password_hash):
    cur = conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash)
    )
    conn.commit()
    return cur.lastrowid


def get_user_by_name(conn, username):
    return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user(conn, user_id):
    return conn.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)).fetchone()


# --------------------------------------------------------------------------- searches
def save_search(conn, user_id, query, results):
    cur = conn.execute(
        "INSERT INTO searches (user_id, query, result_count) VALUES (?, ?, ?)",
        (user_id, query, len(results)),
    )
    search_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO search_results (search_id, url, title, snippet, source, rank, score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (search_id, r["url"], r["title"], r["snippet"], r["source"], i + 1, r["score"])
            for i, r in enumerate(results)
        ],
    )
    conn.commit()
    return search_id


def get_search(conn, search_id):
    row = conn.execute("SELECT * FROM searches WHERE id = ?", (search_id,)).fetchone()
    if row is None:
        return None
    results = conn.execute(
        "SELECT url, title, snippet, source, score FROM search_results "
        "WHERE search_id = ? ORDER BY rank",
        (search_id,),
    ).fetchall()
    return {"id": row["id"], "query": row["query"], "results": [dict(r) for r in results]}


def save_answer(conn, search_id, answer, mode):
    conn.execute(
        "INSERT INTO ai_answers (search_id, answer, mode) VALUES (?, ?, ?)",
        (search_id, answer, mode),
    )
    conn.commit()


# --------------------------------------------------------------------------- feedback signals
def record_click(conn, user_id, url, title, search_id):
    conn.execute(
        "INSERT INTO clicks (user_id, search_id, url, title) VALUES (?, ?, ?, ?)",
        (user_id, search_id, url, title),
    )
    conn.commit()


def click_counts(conn, urls):
    return _count_by_url(conn, "clicks", urls)


def bookmark_counts(conn, urls):
    return _count_by_url(conn, "bookmarks", urls)


def _count_by_url(conn, table, urls):
    if not urls:
        return {}
    marks = ",".join("?" for _ in urls)
    # `table` is only ever one of two internal constants, never user input.
    rows = conn.execute(
        f"SELECT url, COUNT(*) AS n FROM {table} WHERE url IN ({marks}) GROUP BY url", list(urls)
    ).fetchall()
    return {r["url"]: r["n"] for r in rows}


# --------------------------------------------------------------------------- bookmarks
def add_bookmark(conn, user_id, url, title):
    conn.execute(
        "INSERT OR IGNORE INTO bookmarks (user_id, url, title) VALUES (?, ?, ?)",
        (user_id, url, title),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, url, title, created_at FROM bookmarks WHERE user_id = ? AND url = ?",
        (user_id, url),
    ).fetchone()
    return dict(row)


def list_bookmarks(conn, user_id):
    rows = conn.execute(
        "SELECT id, url, title, created_at FROM bookmarks WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_bookmark(conn, user_id, bookmark_id):
    cur = conn.execute(
        "DELETE FROM bookmarks WHERE id = ? AND user_id = ?", (bookmark_id, user_id)
    )
    conn.commit()
    return cur.rowcount > 0


# --------------------------------------------------------------------------- history & chat
def user_history(conn, user_id, limit=50):
    searches = conn.execute(
        "SELECT id, query, result_count, created_at FROM searches "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    visits = conn.execute(
        "SELECT id, url, title, created_at FROM clicks WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return {"searches": [dict(r) for r in searches], "visits": [dict(r) for r in visits]}


def clear_history(conn, user_id):
    conn.execute("DELETE FROM searches WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM clicks WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    conn.commit()


def save_chat(conn, user_id, role, content):
    conn.execute(
        "INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )
    conn.commit()


# --------------------------------------------------------------------------- page cache
def cache_page(conn, url, title, text):
    conn.execute(
        "INSERT INTO pages (url, title, text, fetched_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(url) DO UPDATE SET title = excluded.title, text = excluded.text, "
        "fetched_at = excluded.fetched_at",
        (url, title, text, int(time.time())),
    )
    conn.commit()


def get_cached_page(conn, url, max_age):
    row = conn.execute("SELECT * FROM pages WHERE url = ?", (url,)).fetchone()
    if row is None or time.time() - row["fetched_at"] > max_age:
        return None
    return {"url": row["url"], "title": row["title"], "text": row["text"]}


# --------------------------------------------------------------------------- stats
def stats(conn):
    def one(sql):
        return conn.execute(sql).fetchone()[0]

    top_queries = conn.execute(
        "SELECT query, COUNT(*) AS n FROM searches GROUP BY lower(query) ORDER BY n DESC, id DESC LIMIT 5"
    ).fetchall()
    top_sites = conn.execute(
        "SELECT url, title, COUNT(*) AS n FROM clicks GROUP BY url ORDER BY n DESC LIMIT 5"
    ).fetchall()
    return {
        "users": one("SELECT COUNT(*) FROM users"),
        "searches": one("SELECT COUNT(*) FROM searches"),
        "clicks": one("SELECT COUNT(*) FROM clicks"),
        "indexed_sites": one("SELECT COUNT(*) FROM sites"),
        "cached_pages": one("SELECT COUNT(*) FROM pages"),
        "top_queries": [dict(r) for r in top_queries],
        "top_sites": [dict(r) for r in top_sites],
    }
