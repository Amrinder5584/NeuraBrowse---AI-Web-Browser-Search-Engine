"""Search layer: pluggable providers + de-duplication + feedback ranking."""
import html
import math
import re
from dataclasses import asdict, dataclass
from urllib.parse import quote, urlparse

import requests

import db as dbm

STOPWORDS = {
    "a", "an", "the", "is", "are", "of", "to", "in", "on", "for", "and", "or", "how",
    "what", "why", "who", "do", "does", "i", "me", "my", "with", "can", "best", "about",
}


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOPWORDS]


def normalize_url(url):
    """Lower-case host, drop 'www.', fragment and trailing slash so duplicates collapse."""
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/")
    query = f"?{p.query}" if p.query else ""
    return f"{host}{path}{query}"


@dataclass
class Result:
    url: str
    title: str
    snippet: str
    source: str
    score: float

    def to_dict(self):
        return asdict(self)


# --------------------------------------------------------------------------- providers
class LocalIndexProvider:
    """Keyword search over the curated `sites` table (works offline)."""

    name = "local"

    def __init__(self, conn):
        self.conn = conn

    def search(self, query, limit):
        tokens = tokenize(query)
        if not tokens:
            return []
        results = []
        for row in self.conn.execute("SELECT * FROM sites").fetchall():
            title = set(tokenize(row["title"]))
            keywords = set(tokenize(row["keywords"]))
            desc = set(tokenize(row["description"]))
            score = 0.0
            for t in tokens:
                if t in title:
                    score += 3
                if t in keywords:
                    score += 2
                if t in desc:
                    score += 1
                if t not in title | keywords | desc and len(t) >= 4:
                    # light prefix match: "program" matches "programming"
                    if any(w.startswith(t) for w in title | keywords):
                        score += 1
            if score > 0:
                norm = score / (6 * len(tokens))  # 6 = best possible score per token
                results.append(
                    Result(row["url"], row["title"], row["description"], self.name,
                           round(min(norm, 1.0) * row["base_score"], 4))
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


class WikipediaProvider:
    """Real web results with no API key, using the public MediaWiki search API."""

    name = "wikipedia"

    def __init__(self, timeout, user_agent):
        self.timeout = timeout
        self.headers = {"User-Agent": user_agent}

    def search(self, query, limit):
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query,
                    "srlimit": min(limit, 5), "format": "json", "utf8": 1},
            headers=self.headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        out = []
        for i, item in enumerate(resp.json().get("query", {}).get("search", [])):
            snippet = html.unescape(re.sub(r"<[^>]+>", "", item.get("snippet", "")))
            url = "https://en.wikipedia.org/wiki/" + quote(item["title"].replace(" ", "_"))
            out.append(Result(url, item["title"] + " - Wikipedia", snippet + "...",
                              self.name, round(max(0.6 - 0.05 * i, 0.2), 4)))
        return out


class BraveProvider:
    """Full web search through the official Brave Search API (needs BRAVE_API_KEY)."""

    name = "brave"

    def __init__(self, api_key, timeout, user_agent):
        self.api_key = api_key
        self.timeout = timeout
        self.user_agent = user_agent

    def search(self, query, limit):
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": limit},
            headers={"X-Subscription-Token": self.api_key, "Accept": "application/json",
                     "User-Agent": self.user_agent},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        out = []
        for i, item in enumerate(resp.json().get("web", {}).get("results", [])):
            snippet = html.unescape(re.sub(r"<[^>]+>", "", item.get("description", "")))
            out.append(Result(item["url"], item.get("title", item["url"]), snippet,
                              self.name, round(max(0.9 - 0.06 * i, 0.2), 4)))
        return out


# --------------------------------------------------------------------------- ranking
def apply_feedback(conn, results):
    """Boost sites that this browser's users clicked / bookmarked before.

    This is how data stored in our own database improves "best site" ranking.
    """
    urls = [r.url for r in results]
    clicks = dbm.click_counts(conn, urls)
    marks = dbm.bookmark_counts(conn, urls)
    for r in results:
        boost = 0.10 * math.log1p(clicks.get(r.url, 0)) + 0.15 * min(marks.get(r.url, 0), 3)
        r.score = round(r.score + boost, 4)
    results.sort(key=lambda r: r.score, reverse=True)
    return results


# --------------------------------------------------------------------------- engine
class SearchEngine:
    def __init__(self, conn, config, providers=None):
        self.conn = conn
        self.limit = config["MAX_RESULTS"]
        if providers is None:
            providers = [LocalIndexProvider(conn)]
            timeout, ua = config["REQUEST_TIMEOUT"], config["USER_AGENT"]
            if config.get("ENABLE_WIKIPEDIA"):
                providers.append(WikipediaProvider(timeout, ua))
            if config.get("BRAVE_API_KEY"):
                providers.append(BraveProvider(config["BRAVE_API_KEY"], timeout, ua))
        self.providers = providers

    def search(self, query, limit=None):
        limit = limit or self.limit
        merged = {}
        for provider in self.providers:
            try:
                found = provider.search(query, limit)
            except Exception:  # one failing provider must never break the search
                continue
            for r in found:
                key = normalize_url(r.url)
                if key not in merged or r.score > merged[key].score:
                    merged[key] = r
        results = apply_feedback(self.conn, list(merged.values()))
        return [r.to_dict() for r in results[:limit]]
