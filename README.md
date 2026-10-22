 NeuraBrowse - AI Web Browser & Search Engine

A mini project by **Amrinder Singh Khokhar (Roll No. 455)**.

NeuraBrowse is a browser-style web app with its own search engine, its own database and an AI assistant.
Search anything, get an AI answer, see the best site, and every search, result, click, bookmark and chat
is saved in a local SQLite database. Clicked and bookmarked sites rank higher in later searches.
 Features

- Browser UI: tabs, address/search bar, back / forward / reload / home
- Search engine: local index of 40 sites + Wikipedia (+ Brave Search with an optional key), de-duplication and ranking
- AI answer with a "Best site" pick, plus an AI chat side panel
- Works offline: if there is no AI key or the AI fails, it falls back to a simple extractive summary
- Reader mode and AI page summary
- User accounts, bookmarks and history
- Own SQLite database with 9 tables and a statistics page
- Security: hashed passwords, parameterised SQL, SSRF protection, input validation
- 44 automated tests (pytest)

Tech stack

Python 3, Flask (backend REST API), SQLite (database), HTML / CSS / JavaScript (frontend),
Claude API (optional AI), pytest (testing).

 How to run

Requires Python 3.10 or newer.

```bash
# 1. get the code
git clone https://github.com/<your-username>/NeuraBrowse.git
cd NeuraBrowse

# 2. install requirements
pip install -r requirements.txt

# 3. start the app
python run.py
```

Open **http://127.0.0.1:5000** in your browser. Keep the terminal open while using it (Ctrl+C to stop).

### Optional: real AI answers

Without a key the app runs in offline mode. To use the Claude API, set the key before step 3:

```bash
# Windows (cmd)
set ANTHROPIC_API_KEY=your_key_here

# Linux / macOS
export ANTHROPIC_API_KEY=your_key_here
```

| Variable | Meaning | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Enables real AI answers | not set (offline mode) |
| `AI_MODEL` | AI model name | `claude-sonnet-5-5` |
| `BRAVE_API_KEY` | Enables Brave web search | not set |
| `ENABLE_WIKIPEDIA` | Use Wikipedia results | `1` |
| `DATABASE_PATH` | Database file | `data/browser.db` |

## Run the tests

```bash
python -m pytest
```

Expected: `44 passed`.

## View the database

The data is stored in `data/browser.db` (created on first run). Open it with
[DB Browser for SQLite](https://sqlitebrowser.org), or use the in-app menu: **⋮ → Database stats**.

Project structure

```
backend/    Flask API, database, search, AI and reader modules
frontend/   index.html, style.css, app.js (the browser interface)
tests/      pytest test suite
docs/       full project report (DOCX/PDF), Gantt chart, diagrams, screenshots
run.py      start the app
```

Documentation

The full project report (requirements, architecture, ER diagram, data dictionary, testing, Gantt chart)
is in `docs/NeuraBrowse_Project_Report.pdf`.
Limitations

This is a browser-style web application, not a new rendering engine. Without API keys the search relies on the
local 40-site index and Wikipedia. Offline AI mode only summarises search snippets.
