"""NeuraBrowse - AI web browser. Flask application factory + REST API."""
import os
import re
import sqlite3
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

import db as dbm
import reader
from ai import answer_with_fallback, get_ai, summarize_with_fallback
from config import Config
from search import SearchEngine

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
MAX_QUERY = 300
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(overrides=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(ROOT, "frontend", "templates"),
        static_folder=os.path.join(ROOT, "frontend", "static"),
    )
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    dbm.init_db(app)
    app.teardown_appcontext(dbm.close_db)

    # ------------------------------------------------------------------ helpers
    def err(message, status=400):
        return jsonify({"error": message}), status

    def current_user_id():
        return session.get("user_id")

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_user_id() is None:
                return err("Please log in first.", 401)
            return fn(*args, **kwargs)
        return wrapper

    def body():
        return request.get_json(silent=True) or {}

    def valid_http_url(url):
        try:
            p = urlparse(url)
        except ValueError:
            return False
        return p.scheme in ("http", "https") and bool(p.netloc) and len(url) <= 2000

    # ------------------------------------------------------------------ pages
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        ai = get_ai(app.config)
        return jsonify({"status": "ok", "ai_mode": ai.mode})

    # ------------------------------------------------------------------ auth
    @app.post("/api/register")
    def register():
        data = body()
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        if not USERNAME_RE.match(username):
            return err("Username must be 3-30 letters, numbers or underscores.")
        if len(password) < 6:
            return err("Password must be at least 6 characters.")
        conn = dbm.get_db()
        try:
            user_id = dbm.create_user(conn, username, generate_password_hash(password))
        except sqlite3.IntegrityError:
            return err("That username is already taken.", 409)
        session["user_id"] = user_id
        return jsonify({"user": {"id": user_id, "username": username}}), 201

    @app.post("/api/login")
    def login():
        data = body()
        conn = dbm.get_db()
        user = dbm.get_user_by_name(conn, str(data.get("username", "")).strip())
        if user is None or not check_password_hash(user["password_hash"], str(data.get("password", ""))):
            return err("Wrong username or password.", 401)
        session["user_id"] = user["id"]
        return jsonify({"user": {"id": user["id"], "username": user["username"]}})

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/me")
    def me():
        uid = current_user_id()
        if uid is None:
            return jsonify({"user": None})
        user = dbm.get_user(dbm.get_db(), uid)
        if user is None:
            session.clear()
            return jsonify({"user": None})
        return jsonify({"user": {"id": user["id"], "username": user["username"]}})

    # ------------------------------------------------------------------ search + AI
    @app.get("/api/search")
    def search():
        query = request.args.get("q", "").strip()
        if not query:
            return err("Type something to search.")
        if len(query) > MAX_QUERY:
            return err(f"Search is limited to {MAX_QUERY} characters.")
        conn = dbm.get_db()
        results = SearchEngine(conn, app.config).search(query)
        search_id = dbm.save_search(conn, current_user_id(), query, results)
        return jsonify({"search_id": search_id, "query": query, "results": results})

    @app.post("/api/answer")
    def answer():
        search_id = body().get("search_id")
        if not isinstance(search_id, int):
            return err("search_id is required.")
        conn = dbm.get_db()
        search_row = dbm.get_search(conn, search_id)
        if search_row is None:
            return err("Search not found.", 404)
        text, mode, degraded = answer_with_fallback(
            get_ai(app.config), search_row["query"], search_row["results"]
        )
        dbm.save_answer(conn, search_id, text, mode)
        return jsonify({"answer": text, "mode": mode, "degraded": degraded})

    @app.post("/api/chat")
    def chat():
        data = body()
        message = str(data.get("message", "")).strip()
        if not message:
            return err("Message is empty.")
        if len(message) > 1000:
            return err("Message is too long (max 1000 characters).")
        history = [
            {"role": m["role"], "content": str(m["content"])[:2000]}
            for m in data.get("history", [])[-6:]
            if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
        ]
        conn = dbm.get_db()
        results = SearchEngine(conn, app.config).search(message, limit=5)
        text, mode, degraded = answer_with_fallback(get_ai(app.config), message, results, history)
        uid = current_user_id()
        if uid is not None:
            dbm.save_chat(conn, uid, "user", message)
            dbm.save_chat(conn, uid, "assistant", text)
        sources = [{"title": r["title"], "url": r["url"]} for r in results[:3]]
        return jsonify({"reply": text, "mode": mode, "degraded": degraded, "sources": sources})

    @app.post("/api/click")
    def click():
        data = body()
        url = str(data.get("url", ""))
        if not valid_http_url(url):
            return err("Invalid URL.")
        search_id = data.get("search_id")
        dbm.record_click(dbm.get_db(), current_user_id(), url,
                         str(data.get("title", ""))[:300],
                         search_id if isinstance(search_id, int) else None)
        return jsonify({"ok": True})

    # ------------------------------------------------------------------ reader + summarize
    def load_page(url):
        conn = dbm.get_db()
        page = dbm.get_cached_page(conn, url, app.config["PAGE_CACHE_SECONDS"])
        if page is None:
            page = reader.fetch_readable(
                url, app.config["REQUEST_TIMEOUT"], app.config["MAX_PAGE_BYTES"],
                app.config["USER_AGENT"],
            )
            dbm.cache_page(conn, url, page["title"], page["text"])
        return page

    @app.get("/api/read")
    def read_page():
        url = request.args.get("url", "").strip()
        if not valid_http_url(url):
            return err("Enter a full web address starting with http:// or https://")
        try:
            page = load_page(url)
        except reader.FetchError as exc:
            return err(str(exc), 502)
        return jsonify(page)

    @app.post("/api/summarize")
    def summarize():
        url = str(body().get("url", "")).strip()
        if not valid_http_url(url):
            return err("Invalid URL.")
        try:
            page = load_page(url)
        except reader.FetchError as exc:
            return err(str(exc), 502)
        text, mode, degraded = summarize_with_fallback(get_ai(app.config), page["title"], page["text"])
        return jsonify({"summary": text, "mode": mode, "degraded": degraded})

    # ------------------------------------------------------------------ bookmarks
    @app.get("/api/bookmarks")
    @login_required
    def bookmarks_list():
        return jsonify({"bookmarks": dbm.list_bookmarks(dbm.get_db(), current_user_id())})

    @app.post("/api/bookmarks")
    @login_required
    def bookmarks_add():
        data = body()
        url = str(data.get("url", ""))
        if not valid_http_url(url):
            return err("Invalid URL.")
        mark = dbm.add_bookmark(dbm.get_db(), current_user_id(), url, str(data.get("title", ""))[:300])
        return jsonify({"bookmark": mark}), 201

    @app.delete("/api/bookmarks/<int:bookmark_id>")
    @login_required
    def bookmarks_delete(bookmark_id):
        if not dbm.delete_bookmark(dbm.get_db(), current_user_id(), bookmark_id):
            return err("Bookmark not found.", 404)
        return jsonify({"ok": True})

    # ------------------------------------------------------------------ history + stats
    @app.get("/api/history")
    @login_required
    def history_list():
        return jsonify(dbm.user_history(dbm.get_db(), current_user_id()))

    @app.delete("/api/history")
    @login_required
    def history_clear():
        dbm.clear_history(dbm.get_db(), current_user_id())
        return jsonify({"ok": True})

    @app.get("/api/stats")
    def stats():
        return jsonify(dbm.stats(dbm.get_db()))

    # ------------------------------------------------------------------ errors
    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return err("Not found.", 404)
        return "Not found", 404

    @app.errorhandler(405)
    def bad_method(_e):
        return err("Method not allowed.", 405)

    @app.errorhandler(500)
    def server_error(_e):
        return err("Something went wrong on the server.", 500)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=bool(os.environ.get("FLASK_DEBUG")))
