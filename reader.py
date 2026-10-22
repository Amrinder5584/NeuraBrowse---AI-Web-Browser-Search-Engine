"""Reader mode: fetch a web page safely and extract its readable text.

Because the server downloads whatever URL a user types, we must guard against SSRF
(making the server call internal addresses). Every hop of a redirect chain is re-checked.
"""
import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

MAX_REDIRECTS = 3
MAX_TEXT_CHARS = 20000


class FetchError(Exception):
    pass


def is_safe_url(url):
    """Allow only http(s) URLs whose host resolves exclusively to public IP addresses."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except (socket.gaierror, UnicodeError):
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return True


class _ReadableParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "template"}
    BLOCK = {"p", "h1", "h2", "h3", "li", "blockquote", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.blocks = []
        self._skip_depth = 0
        self._in_title = False
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in self.SKIP:
            self._skip_depth += 1
        elif tag in self.BLOCK:
            self._flush()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in self.SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in self.BLOCK:
            self._flush()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._skip_depth == 0:
            self._buf.append(data)

    def _flush(self):
        text = " ".join("".join(self._buf).split())
        self._buf = []
        if len(text) > 25:  # drop menu crumbs and tiny fragments
            self.blocks.append(text)

    def close(self):
        super().close()
        self._flush()


def extract_readable(html_text):
    parser = _ReadableParser()
    parser.feed(html_text)
    parser.close()
    title = " ".join(parser.title.split()) or "Untitled page"
    text = "\n\n".join(parser.blocks)[:MAX_TEXT_CHARS]
    return title, text


def fetch_readable(url, timeout=8, max_bytes=1_000_000, user_agent="NeuraBrowse/1.0"):
    """Download `url` (following up to 3 safe redirects) and return {url, title, text}."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if not is_safe_url(current):
            raise FetchError("This address is not allowed.")
        try:
            resp = requests.get(current, timeout=timeout, allow_redirects=False, stream=True,
                                headers={"User-Agent": user_agent})
        except requests.RequestException as exc:
            raise FetchError(f"Could not load the page: {exc.__class__.__name__}") from exc
        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                raise FetchError("Bad redirect.")
            current = urljoin(current, location)
            continue
        try:
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "")
            if "html" not in ctype and "text" not in ctype:
                raise FetchError("Reader mode only supports web pages.")
            body = b""
            for chunk in resp.iter_content(65536):
                body += chunk
                if len(body) >= max_bytes:
                    break
        except requests.RequestException as exc:
            raise FetchError(f"Could not load the page: {exc.__class__.__name__}") from exc
        finally:
            resp.close()
        text = body.decode(resp.encoding or "utf-8", errors="replace")
        title, content = extract_readable(text)
        return {"url": current, "title": title, "text": content}
    raise FetchError("Too many redirects.")
