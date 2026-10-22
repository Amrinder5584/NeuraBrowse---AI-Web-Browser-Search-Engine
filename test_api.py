import reader


# --------------------------------------------------------------------------- auth
def test_register_login_logout_flow(client):
    assert client.get("/api/me").get_json()["user"] is None
    r = client.post("/api/register", json={"username": "sam_1", "password": "abcdef"})
    assert r.status_code == 201
    assert client.get("/api/me").get_json()["user"]["username"] == "sam_1"
    client.post("/api/logout")
    assert client.get("/api/me").get_json()["user"] is None
    assert client.post("/api/login", json={"username": "sam_1", "password": "abcdef"}).status_code == 200
    assert client.post("/api/login", json={"username": "sam_1", "password": "wrong"}).status_code == 401


def test_register_validation(client):
    assert client.post("/api/register", json={"username": "a", "password": "abcdef"}).status_code == 400
    assert client.post("/api/register", json={"username": "good_name", "password": "123"}).status_code == 400
    assert client.post("/api/register", json={"username": "bad name!", "password": "abcdef"}).status_code == 400


def test_duplicate_username_conflict(client):
    client.post("/api/register", json={"username": "dupe", "password": "abcdef"})
    assert client.post("/api/register", json={"username": "dupe", "password": "abcdef"}).status_code == 409


def test_password_is_stored_hashed(app, client):
    import sqlite3
    client.post("/api/register", json={"username": "hashme", "password": "plain-text-pw"})
    row = sqlite3.connect(app.config["DATABASE"]).execute(
        "SELECT password_hash FROM users WHERE username='hashme'").fetchone()
    assert "plain-text-pw" not in row[0]


# --------------------------------------------------------------------------- search
def test_search_returns_results_and_saves_to_db(client):
    r = client.get("/api/search", query_string={"q": "python flask"})
    data = r.get_json()
    assert r.status_code == 200 and data["results"] and isinstance(data["search_id"], int)
    stats = client.get("/api/stats").get_json()
    assert stats["searches"] == 1 and stats["top_queries"][0]["query"] == "python flask"


def test_search_validation(client):
    assert client.get("/api/search").status_code == 400
    assert client.get("/api/search", query_string={"q": "   "}).status_code == 400
    assert client.get("/api/search", query_string={"q": "x" * 301}).status_code == 400


def test_search_handles_sql_injection_text(client):
    r = client.get("/api/search", query_string={"q": "'; DROP TABLE sites; --"})
    assert r.status_code == 200
    assert client.get("/api/search", query_string={"q": "sqlite"}).get_json()["results"]


def test_answer_for_search_uses_offline_ai(client):
    sid = client.get("/api/search", query_string={"q": "learn python"}).get_json()["search_id"]
    r = client.post("/api/answer", json={"search_id": sid})
    data = r.get_json()
    assert r.status_code == 200 and data["mode"] == "offline" and "Best site" in data["answer"]


def test_answer_validation(client):
    assert client.post("/api/answer", json={}).status_code == 400
    assert client.post("/api/answer", json={"search_id": 9999}).status_code == 404


def test_chat_reply_has_sources_and_persists_for_user(logged_in):
    r = logged_in.post("/api/chat", json={"message": "what is sqlite", "history": []})
    data = r.get_json()
    assert r.status_code == 200 and data["reply"] and data["sources"]


def test_chat_validation(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 400
    assert client.post("/api/chat", json={"message": "x" * 1001}).status_code == 400


# --------------------------------------------------------------------------- feedback loop
def test_click_feedback_changes_ranking(client):
    first = client.get("/api/search", query_string={"q": "database"}).get_json()
    top, runner_up = first["results"][0]["url"], first["results"][1]["url"]
    for _ in range(8):
        client.post("/api/click", json={"url": runner_up, "title": "x", "search_id": first["search_id"]})
    second = client.get("/api/search", query_string={"q": "database"}).get_json()
    assert second["results"][0]["url"] == runner_up != top


def test_click_rejects_bad_url(client):
    assert client.post("/api/click", json={"url": "javascript:alert(1)"}).status_code == 400


# --------------------------------------------------------------------------- bookmarks / history
def test_bookmarks_require_login(client):
    assert client.get("/api/bookmarks").status_code == 401
    assert client.post("/api/bookmarks", json={"url": "https://a.com"}).status_code == 401


def test_bookmark_crud(logged_in):
    r = logged_in.post("/api/bookmarks", json={"url": "https://www.python.org/", "title": "Py"})
    assert r.status_code == 201
    logged_in.post("/api/bookmarks", json={"url": "https://www.python.org/", "title": "Py"})  # duplicate
    items = logged_in.get("/api/bookmarks").get_json()["bookmarks"]
    assert len(items) == 1
    assert logged_in.delete(f"/api/bookmarks/{items[0]['id']}").status_code == 200
    assert logged_in.delete(f"/api/bookmarks/{items[0]['id']}").status_code == 404


def test_bookmarks_are_private_per_user(app):
    a, b = app.test_client(), app.test_client()
    a.post("/api/register", json={"username": "user_a", "password": "abcdef"})
    b.post("/api/register", json={"username": "user_b", "password": "abcdef"})
    bm = a.post("/api/bookmarks", json={"url": "https://a.com", "title": "a"}).get_json()["bookmark"]
    assert b.get("/api/bookmarks").get_json()["bookmarks"] == []
    assert b.delete(f"/api/bookmarks/{bm['id']}").status_code == 404


def test_history_records_and_clears(logged_in):
    logged_in.get("/api/search", query_string={"q": "python"})
    logged_in.post("/api/click", json={"url": "https://www.python.org/", "title": "Python"})
    h = logged_in.get("/api/history").get_json()
    assert len(h["searches"]) == 1 and len(h["visits"]) == 1
    logged_in.delete("/api/history")
    h = logged_in.get("/api/history").get_json()
    assert h["searches"] == [] and h["visits"] == []


# --------------------------------------------------------------------------- reader
def test_read_rejects_private_and_malformed_urls(client):
    assert client.get("/api/read", query_string={"url": "http://127.0.0.1:5000/"}).status_code == 502
    assert client.get("/api/read", query_string={"url": "notaurl"}).status_code == 400
    assert client.get("/api/read", query_string={"url": "file:///etc/passwd"}).status_code == 400


def test_read_and_summarize_use_cache(client, monkeypatch):
    calls = []

    def fake_fetch(url, timeout, max_bytes, ua):
        calls.append(url)
        return {"url": url, "title": "Demo",
                "text": "This is a long enough sentence to be summarized by the offline model. " * 4}

    monkeypatch.setattr(reader, "fetch_readable", fake_fetch)
    url = "https://example.com/article"
    assert client.get("/api/read", query_string={"url": url}).get_json()["title"] == "Demo"
    s = client.post("/api/summarize", json={"url": url}).get_json()
    assert s["summary"].startswith("- ") and s["mode"] == "offline"
    assert len(calls) == 1  # second call served from the database cache


# --------------------------------------------------------------------------- misc
def test_health_and_index(client):
    assert client.get("/health").get_json() == {"status": "ok", "ai_mode": "offline"}
    assert client.get("/").status_code == 200


def test_unknown_api_route_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.get_json()["error"]
