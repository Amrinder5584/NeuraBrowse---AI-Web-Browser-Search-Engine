import sqlite3

import db as dbm
from search import (LocalIndexProvider, Result, SearchEngine, apply_feedback,
                    normalize_url, tokenize)


def make_conn(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def test_tokenize_drops_stopwords_and_lowercases():
    assert tokenize("How to Learn PYTHON?") == ["learn", "python"]
    assert "the" not in tokenize("the python")


def test_normalize_url_collapses_variants():
    assert normalize_url("https://www.Python.org/") == normalize_url("http://python.org")
    assert normalize_url("https://a.com/x#frag") == normalize_url("https://a.com/x")


def test_local_search_finds_relevant_site(app):
    conn = make_conn(app)
    results = LocalIndexProvider(conn).search("flask python backend", 5)
    assert results, "expected at least one result"
    assert "flask" in results[0].url


def test_local_search_empty_query_returns_nothing(app):
    assert LocalIndexProvider(make_conn(app)).search("the of and", 5) == []


def test_unknown_query_returns_nothing(app):
    assert LocalIndexProvider(make_conn(app)).search("zzzqqqxxx", 5) == []


def test_prefix_matching(app):
    results = LocalIndexProvider(make_conn(app)).search("program", 5)
    assert results


def test_feedback_boosts_clicked_site(app):
    conn = make_conn(app)
    a = Result("https://a.example/", "A", "", "t", 0.50)
    b = Result("https://b.example/", "B", "", "t", 0.52)
    for _ in range(5):
        dbm.record_click(conn, None, "https://a.example/", "A", None)
    ranked = apply_feedback(conn, [a, b])
    assert ranked[0].url == "https://a.example/"


def test_engine_dedupes_and_survives_provider_failure(app):
    class Broken:
        def search(self, q, limit):
            raise RuntimeError("network down")

    class Dup:
        def search(self, q, limit):
            return [Result("https://www.x.com/page/", "X1", "", "d", 0.4),
                    Result("http://x.com/page", "X2", "", "d", 0.9)]

    engine = SearchEngine(make_conn(app), app.config, providers=[Broken(), Dup()])
    out = engine.search("anything")
    assert len(out) == 1
    assert out[0]["title"] == "X2"  # higher score wins
