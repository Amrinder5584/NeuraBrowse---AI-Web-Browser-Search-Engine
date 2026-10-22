/* NeuraBrowse front end - plain JavaScript, no build step.
   All dynamic text is inserted with textContent / DOM nodes (never innerHTML) to prevent XSS. */
"use strict";

const $ = (sel) => document.querySelector(sel);
const state = { tabs: [], active: null, nextId: 1, user: null, bookmarks: new Map(), chat: [], aiMode: "offline" };

const SUGGESTIONS = ["learn python", "flask backend tutorial", "what is machine learning", "sqlite database", "how does a browser work", "pytest testing"];

/* ---------- small helpers ---------- */
function el(tag, props = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null) node.append(kid);
  return node;
}

async function api(path, options = {}) {
  const opts = { credentials: "same-origin", ...options };
  if (opts.json !== undefined) {
    opts.method = opts.method || "POST";
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(opts.json);
  }
  const res = await fetch(path, opts);
  let data = {};
  try { data = await res.json(); } catch (_) { /* non-JSON response */ }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function toast(message) {
  const t = $("#toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 2600);
}

function host(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch (_) { return url; }
}

/* Render text with **bold** and line breaks safely. */
function richText(container, text) {
  container.textContent = "";
  String(text).split("\n").forEach((line, i, all) => {
    line.split(/\*\*(.+?)\*\*/g).forEach((part, idx) => {
      container.append(idx % 2 ? el("strong", { text: part }) : document.createTextNode(part));
    });
    if (i < all.length - 1) container.append(document.createElement("br"));
  });
}

function looksLikeUrl(v) {
  return /^https?:\/\/\S+$/i.test(v) || /^[^\s/]+\.[a-z]{2,}(\/\S*)?$/i.test(v);
}

function setMode(mode) {
  state.aiMode = mode;
  const badge = $("#modeBadge");
  badge.textContent = mode === "claude" ? "Claude AI" : "Offline mode";
  badge.className = "badge" + (mode === "claude" ? "" : " offline");
}

/* ---------- tabs & navigation ---------- */
function currentTab() { return state.tabs.find((t) => t.id === state.active); }
function currentEntry(tab = currentTab()) { return tab && tab.stack[tab.idx]; }

function newTab(entry = { view: "home" }) {
  const tab = { id: state.nextId++, stack: [], idx: -1 };
  state.tabs.push(tab);
  state.active = tab.id;
  navigate(tab, entry);
}

function closeTab(id) {
  const i = state.tabs.findIndex((t) => t.id === id);
  state.tabs.splice(i, 1);
  if (!state.tabs.length) return newTab();
  if (state.active === id) state.active = state.tabs[Math.min(i, state.tabs.length - 1)].id;
  render();
}

function navigate(tab, entry, push = true) {
  if (push) {
    tab.stack = tab.stack.slice(0, tab.idx + 1);
    tab.stack.push(entry);
    tab.idx = tab.stack.length - 1;
  }
  render();
}

function entryTitle(e) {
  switch (e.view) {
    case "results": return e.query;
    case "page": return e.title || host(e.url);
    case "bookmarks": return "Bookmarks";
    case "history": return "History";
    case "stats": return "Database stats";
    default: return "New tab";
  }
}

function search(query) {
  query = query.trim();
  if (query) navigate(currentTab(), { view: "results", query });
}

function go(input) {
  const v = input.trim();
  if (!v) return;
  if (looksLikeUrl(v)) openPage(/^https?:\/\//i.test(v) ? v : "https://" + v, "", null);
  else search(v);
}

function openPage(url, title, searchId) {
  api("/api/click", { json: { url, title, search_id: searchId } }).catch(() => {});
  navigate(currentTab(), { view: "page", url, title });
}

/* ---------- rendering ---------- */
function render() {
  renderTabs();
  const tab = currentTab();
  const entry = currentEntry(tab);
  $("#omniInput").value = entry.view === "results" ? entry.query : entry.view === "page" ? entry.url : "";
  $("#backBtn").disabled = tab.idx <= 0;
  $("#fwdBtn").disabled = tab.idx >= tab.stack.length - 1;
  updateStar();
  const view = $("#view");
  view.textContent = "";
  const renderers = { home: renderHome, results: renderResults, page: renderPage, bookmarks: renderBookmarks, history: renderHistory, stats: renderStats };
  view.append(renderers[entry.view](entry, tab));
  document.title = entryTitle(entry) + " - NeuraBrowse";
}

function renderTabs() {
  const strip = $("#tabs");
  strip.textContent = "";
  for (const tab of state.tabs) {
    const active = tab.id === state.active;
    strip.append(
      el("div", { class: "tab" + (active ? " active" : ""), role: "tab", "aria-selected": String(active) },
        el("button", { class: "tab-title", text: entryTitle(currentEntry(tab)), title: entryTitle(currentEntry(tab)),
          onclick: () => { state.active = tab.id; render(); } }),
        el("button", { class: "tab-close", "aria-label": "Close tab", text: "×", onclick: () => closeTab(tab.id) })
      )
    );
  }
}

function renderHome() {
  const form = el("form", { onsubmit: (e) => { e.preventDefault(); go(e.target.q.value); } },
    el("input", { name: "q", placeholder: "Search the web or ask the AI anything", "aria-label": "Search", maxlength: "300", autofocus: "" }));
  const chips = el("div", { class: "chips" },
    SUGGESTIONS.map((s) => el("button", { class: "chip", text: s, onclick: () => search(s) })));
  return el("div", { class: "wrap home" },
    el("h1", {}, "Neura", el("span", { text: "Browse" })),
    el("p", { text: "A browser where an AI reads the web with you. Every search is saved to your own database." }),
    form, chips);
}

function renderResults(entry) {
  const wrap = el("div", { class: "wrap" });
  if (!entry.loading && !entry.data && !entry.error) {
    entry.loading = true;
    loadResults(entry);
  }
  if (entry.error) return el("div", { class: "wrap" }, el("div", { class: "error-box", text: entry.error }));
  if (!entry.data) return el("div", { class: "wrap" }, el("p", { class: "meta", text: "Searching..." }));

  const { results, search_id } = entry.data;
  wrap.append(el("p", { class: "meta", text: `${results.length} result${results.length === 1 ? "" : "s"} for "${entry.query}"` }));

  const card = el("section", { class: "ai-card", "aria-label": "AI answer" }, el("h2", { text: "AI answer" }));
  if (entry.answer) {
    const body = el("div", { class: "body" });
    richText(body, entry.answer.text);
    card.append(body);
  } else if (entry.answerError) {
    card.append(el("div", { class: "body", text: entry.answerError }));
  } else {
    card.append(el("div", { class: "skeleton" }), el("div", { class: "skeleton" }), el("div", { class: "skeleton" }));
  }
  wrap.append(card);

  if (!results.length) wrap.append(el("div", { class: "notice", text: "No results. Try different keywords, or paste a web address to open it directly." }));
  results.forEach((r, i) => {
    wrap.append(el("article", { class: "result" },
      el("div", { class: "host" }, host(r.url),
        el("span", { class: "pill", text: r.source }),
        i === 0 ? el("span", { class: "pill top", text: "Top pick" }) : null),
      el("button", { class: "title", text: r.title, onclick: () => openPage(r.url, r.title, search_id) }),
      el("p", { class: "snippet", text: r.snippet })));
  });
  return wrap;
}

async function loadResults(entry) {
  try {
    entry.data = await api("/api/search?q=" + encodeURIComponent(entry.query));
  } catch (e) {
    entry.error = e.message;
  }
  entry.loading = false;
  renderIfVisible(entry);
  if (!entry.data) return;
  try {
    const a = await api("/api/answer", { json: { search_id: entry.data.search_id } });
    entry.answer = { text: a.answer, mode: a.mode };
    setMode(a.mode);
  } catch (e) {
    entry.answerError = "The AI answer is unavailable right now. The results below still work.";
  }
  renderIfVisible(entry);
}

function renderIfVisible(entry) {
  if (currentEntry() === entry) render();
}

function renderPage(entry) {
  const wrap = el("div", { class: "wrap reader" });
  if (!entry.page && !entry.error && !entry.loading) {
    entry.loading = true;
    api("/api/read?url=" + encodeURIComponent(entry.url))
      .then((p) => { entry.page = p; entry.title = p.title; })
      .catch((e) => { entry.error = e.message; })
      .finally(() => { entry.loading = false; renderIfVisible(entry); });
  }
  if (entry.error) {
    return el("div", { class: "wrap" },
      el("div", { class: "error-box", text: entry.error }),
      el("p", {}, el("a", { href: entry.url, target: "_blank", rel: "noopener noreferrer", text: "Open the original site in a new tab" })));
  }
  if (!entry.page) return el("div", { class: "wrap" }, el("p", { class: "meta", text: "Loading page..." }));

  const summaryBox = el("section", { class: "ai-card", hidden: "" }, el("h2", { text: "AI summary" }), el("div", { class: "body" }));
  if (entry.summary) { summaryBox.hidden = false; richText(summaryBox.querySelector(".body"), entry.summary); }
  const sumBtn = el("button", { text: "Summarize with AI", onclick: async (ev) => {
    ev.target.disabled = true;
    ev.target.textContent = "Summarizing...";
    try {
      const s = await api("/api/summarize", { json: { url: entry.url } });
      entry.summary = s.summary;
      setMode(s.mode);
    } catch (e) { toast(e.message); }
    renderIfVisible(entry);
  } });

  wrap.append(
    el("h1", { text: entry.page.title }),
    el("div", { class: "meta", text: host(entry.url) + " - reader view" }),
    el("div", { class: "actions" }, sumBtn,
      el("a", { href: entry.url, target: "_blank", rel: "noopener noreferrer", text: "Open original" })),
    summaryBox);
  const paragraphs = entry.page.text.split("\n\n").filter(Boolean);
  if (!paragraphs.length) wrap.append(el("div", { class: "notice", text: "This page has no readable text (it may need JavaScript). Use Open original." }));
  paragraphs.forEach((p) => wrap.append(el("p", { text: p })));
  return wrap;
}

/* ---------- bookmarks, history, stats ---------- */
function needLogin(message) {
  return el("div", { class: "wrap list" }, el("div", { class: "notice" }, message + " ",
    el("button", { class: "btn", text: "Log in", onclick: () => openAuth("login") })));
}

function renderBookmarks() {
  if (!state.user) return needLogin("Log in to see your bookmarks.");
  const wrap = el("div", { class: "wrap list" }, el("h1", { text: "Bookmarks" }));
  if (!state.bookmarks.size) wrap.append(el("p", { class: "meta", text: "Nothing saved yet. Open a page and press the star." }));
  for (const [url, b] of state.bookmarks) {
    wrap.append(el("div", { class: "row" },
      el("button", { text: b.title || url, onclick: () => navigate(currentTab(), { view: "page", url, title: b.title }) }),
      el("button", { text: "Remove", onclick: () => removeBookmark(url) })));
  }
  return wrap;
}

function renderHistory(entry) {
  if (!state.user) return needLogin("Log in to see your history.");
  const wrap = el("div", { class: "wrap list" }, el("h1", { text: "History" }));
  if (!entry.data && !entry.loading) {
    entry.loading = true;
    api("/api/history").then((d) => (entry.data = d)).catch((e) => toast(e.message))
      .finally(() => { entry.loading = false; renderIfVisible(entry); });
  }
  if (!entry.data) return wrap;
  wrap.append(el("div", { class: "actions" }, el("button", { class: "btn", text: "Clear history", onclick: async () => {
    await api("/api/history", { method: "DELETE" });
    entry.data = null;
    toast("History cleared");
    render();
  } })));
  wrap.append(el("h2", { text: "Searches" }));
  entry.data.searches.forEach((s) => wrap.append(el("div", { class: "row" },
    el("button", { text: s.query, onclick: () => search(s.query) }), el("span", { class: "when", text: s.created_at }))));
  wrap.append(el("h2", { text: "Visited pages" }));
  entry.data.visits.forEach((v) => wrap.append(el("div", { class: "row" },
    el("button", { text: v.title || v.url, onclick: () => navigate(currentTab(), { view: "page", url: v.url, title: v.title }) }),
    el("span", { class: "when", text: v.created_at }))));
  if (!entry.data.searches.length && !entry.data.visits.length) wrap.append(el("p", { class: "meta", text: "History is empty." }));
  return wrap;
}

function renderStats(entry) {
  const wrap = el("div", { class: "wrap list" }, el("h1", { text: "Database stats" }));
  if (!entry.data && !entry.loading) {
    entry.loading = true;
    api("/api/stats").then((d) => (entry.data = d)).catch((e) => toast(e.message))
      .finally(() => { entry.loading = false; renderIfVisible(entry); });
  }
  if (!entry.data) return wrap;
  const d = entry.data;
  const grid = el("div", { class: "grid" });
  [["Users", d.users], ["Searches saved", d.searches], ["Clicks saved", d.clicks], ["Indexed sites", d.indexed_sites], ["Cached pages", d.cached_pages]]
    .forEach(([label, n]) => grid.append(el("div", { class: "stat" }, el("b", { text: String(n) }), el("span", { text: label }))));
  wrap.append(grid, el("h2", { text: "Top searches" }));
  d.top_queries.forEach((q) => wrap.append(el("div", { class: "row" }, el("span", { text: q.query }), el("span", { class: "when", text: q.n + "x" }))));
  wrap.append(el("h2", { text: "Most visited sites" }));
  d.top_sites.forEach((s) => wrap.append(el("div", { class: "row" }, el("span", { text: s.title || s.url }), el("span", { class: "when", text: s.n + "x" }))));
  return wrap;
}

/* ---------- bookmarks logic ---------- */
function updateStar() {
  const entry = currentEntry();
  const btn = $("#starBtn");
  const isPage = entry && entry.view === "page";
  btn.disabled = !isPage;
  const on = isPage && state.bookmarks.has(entry.url);
  btn.classList.toggle("on", on);
  btn.textContent = on ? "★" : "☆";
}

async function toggleBookmark() {
  const entry = currentEntry();
  if (!entry || entry.view !== "page") return;
  if (!state.user) { openAuth("login"); return; }
  try {
    if (state.bookmarks.has(entry.url)) return removeBookmark(entry.url);
    const { bookmark } = await api("/api/bookmarks", { json: { url: entry.url, title: entry.title || "" } });
    state.bookmarks.set(bookmark.url, bookmark);
    toast("Bookmark saved");
  } catch (e) { toast(e.message); }
  updateStar();
}

async function removeBookmark(url) {
  const b = state.bookmarks.get(url);
  if (!b) return;
  try {
    await api("/api/bookmarks/" + b.id, { method: "DELETE" });
    state.bookmarks.delete(url);
    toast("Bookmark removed");
  } catch (e) { toast(e.message); }
  render();
}

async function loadBookmarks() {
  state.bookmarks = new Map();
  if (!state.user) return;
  try {
    const { bookmarks } = await api("/api/bookmarks");
    bookmarks.forEach((b) => state.bookmarks.set(b.url, b));
  } catch (_) { /* ignore */ }
}

/* ---------- auth ---------- */
let authMode = "login";

function openAuth(mode) {
  authMode = mode;
  const reg = mode === "register";
  $("#authTitle").textContent = reg ? "Create account" : "Log in";
  $("#authSubmit").textContent = reg ? "Sign up" : "Log in";
  $("#authSwitch").textContent = reg ? "I already have an account" : "Create an account";
  $("#authPass").autocomplete = reg ? "new-password" : "current-password";
  $("#authError").textContent = "";
  $("#menu").hidden = true;
  const dlg = $("#authDialog");
  if (!dlg.open) dlg.showModal();
  $("#authUser").focus();
}

async function submitAuth(ev) {
  ev.preventDefault();
  try {
    const { user } = await api(authMode === "register" ? "/api/register" : "/api/login",
      { json: { username: $("#authUser").value, password: $("#authPass").value } });
    state.user = user;
    $("#authDialog").close();
    $("#authPass").value = "";
    await loadBookmarks();
    updateUserUi();
    render();
    toast("Welcome, " + user.username);
  } catch (e) {
    $("#authError").textContent = e.message;
  }
}

async function logout() {
  await api("/api/logout", { method: "POST" }).catch(() => {});
  state.user = null;
  state.bookmarks = new Map();
  updateUserUi();
  render();
  toast("Logged out");
}

function updateUserUi() {
  $("#menuUser").textContent = state.user ? "Signed in as " + state.user.username : "Not signed in (searches are anonymous)";
  $("#authItem").textContent = state.user ? "Log out" : "Log in";
}

/* ---------- AI chat panel ---------- */
function addMsg(role, text, sources = []) {
  const box = el("div", { class: "msg " + (role === "user" ? "user" : "ai") });
  if (role === "user") box.textContent = text; else richText(box, text);
  sources.forEach((s) => box.append(el("a", { class: "src", href: s.url, target: "_blank", rel: "noopener noreferrer", text: "→ " + s.title })));
  const log = $("#chatLog");
  log.append(box);
  log.scrollTop = log.scrollHeight;
  return box;
}

async function sendChat(ev) {
  ev.preventDefault();
  const input = $("#chatInput");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  addMsg("user", message);
  const pending = addMsg("ai", "Thinking...");
  try {
    const r = await api("/api/chat", { json: { message, history: state.chat.slice(-6) } });
    state.chat.push({ role: "user", content: message }, { role: "assistant", content: r.reply });
    pending.remove();
    addMsg("ai", r.reply, r.sources);
    setMode(r.mode);
  } catch (e) {
    pending.textContent = e.message;
  }
}

/* ---------- wiring ---------- */
function init() {
  $("#newTab").onclick = () => newTab();
  $("#backBtn").onclick = () => { const t = currentTab(); if (t.idx > 0) { t.idx--; render(); } };
  $("#fwdBtn").onclick = () => { const t = currentTab(); if (t.idx < t.stack.length - 1) { t.idx++; render(); } };
  $("#reloadBtn").onclick = () => {
    const e = currentEntry();
    ["data", "answer", "answerError", "page", "summary", "error", "loading"].forEach((k) => delete e[k]);
    render();
  };
  $("#homeBtn").onclick = () => navigate(currentTab(), { view: "home" });
  $("#omnibox").onsubmit = (e) => { e.preventDefault(); go($("#omniInput").value); $("#omniInput").blur(); };
  $("#omniInput").onfocus = (e) => e.target.select();
  $("#starBtn").onclick = toggleBookmark;
  $("#panelBtn").onclick = () => {
    const panel = $("#panel");
    panel.hidden = !panel.hidden;
    $("#panelBtn").classList.toggle("on", !panel.hidden);
    if (!panel.hidden) {
      if (!$("#chatLog").children.length) addMsg("ai", "Hi! Ask me anything. I search first, then answer from what I find.");
      $("#chatInput").focus();
    }
  };
  $("#chatForm").onsubmit = sendChat;

  $("#menuBtn").onclick = (e) => { e.stopPropagation(); $("#menu").hidden = !$("#menu").hidden; };
  document.addEventListener("click", (e) => { if (!e.target.closest("#menu")) $("#menu").hidden = true; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#menu").hidden = true; });
  $("#menu").onclick = (e) => {
    const act = e.target.dataset && e.target.dataset.act;
    if (!act) return;
    $("#menu").hidden = true;
    if (act === "auth") return state.user ? logout() : openAuth("login");
    navigate(currentTab(), { view: act });
  };

  $("#authForm").onsubmit = submitAuth;
  $("#authSwitch").onclick = () => openAuth(authMode === "login" ? "register" : "login");
  $("#authCancel").onclick = () => $("#authDialog").close();

  newTab();
  api("/health").then((h) => setMode(h.ai_mode)).catch(() => setMode("offline"));
  api("/api/me").then(async (d) => { state.user = d.user; await loadBookmarks(); updateUserUi(); render(); }).catch(updateUserUi);
}

init();
