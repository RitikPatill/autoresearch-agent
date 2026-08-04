# AutoResearch Agent

> A minimal, locally-runnable AI research agent that turns a natural-language question into a cited Markdown report.

**Status: M2 complete — `web_search` (DuckDuckGo) and `fetch_page` (Playwright) implemented and tested.**

---

## What it does

AutoResearch Agent accepts a plain-English research question, autonomously searches the web using DuckDuckGo, fetches and parses pages with a headless Playwright browser, and synthesises findings into a structured Markdown report with numbered citations. The entire agent loop — plan, search, fetch, extract, synthesise — is orchestrated by Claude claude-sonnet-4-6 via Anthropic's tool-use API. No subscriptions, no GPU, no 10 000-line frameworks required.

## Motivation

Existing research agents either live behind a paywall (Perplexity, You.com) or are buried inside massive orchestration frameworks (LangChain, AutoGPT) that make it impossible to see the underlying ReAct loop. This project shows in roughly 500 lines of clean Python exactly how tool-calling, observation loops, and citation tracking work — making it an ideal portfolio piece for AI/ML and applied LLM engineering roles.

## What works now

| Milestone | Scope | State |
|-----------|-------|-------|
| M1 | Repo scaffold: `src/` layout, `requirements.txt`, `.gitignore`, MIT license, README | **done** |
| M2 | `tools.py` — `web_search`, `fetch_page`; smoke tests in `tests/` | **done** |
| M3 | `agent.py` — ReAct loop with citation tracking | planned |
| M4 | `api.py` — FastAPI `/research` endpoint | planned |
| M5 | Streamlit UI | planned |
| M6 | End-to-end tests, Quickstart polish, Docker image | planned |

M1 delivers a runnable `pip install` baseline. M2 implements the two browser/search tools and their smoke tests.

## Architecture

```
CLI / Streamlit UI
      │
      ▼
 FastAPI /research
      │
      ▼
  AgentLoop (ReAct)
  ├── tool: web_search  (DuckDuckGo scrape, no API key)
  ├── tool: fetch_page  (Playwright → cleaned text)
  ├── tool: extract_facts (LLM sub-call)
  └── tool: finish_report (writes Markdown)
      │
      ▼
  reports/<slug>.md
```

<!-- TODO: replace ASCII diagram with a proper PNG after M3 is complete -->

## Quick start

> Full instructions will be added in M6. The commands below install all dependencies.

```bash
git clone <repo>
cd autoresearch-agent
pip install -r requirements.txt
playwright install chromium
```

## Project structure

```
autoresearch-agent/
├── src/
│   ├── __init__.py      # makes src a Python package
│   ├── agent.py         # ReAct agent loop (stub — M3)
│   ├── tools.py         # web_search, fetch_page (M2 done); extract_facts, finish_report (M3)
│   └── api.py           # FastAPI /research endpoint (stub — M4)
├── tests/
│   ├── __init__.py
│   └── test_tools.py    # smoke tests for web_search and fetch_page
├── reports/             # generated Markdown reports (git-ignored)
│   └── .gitkeep
├── pytest.ini           # asyncio_mode=auto, integration marker
├── requirements.txt     # pinned runtime + test dependencies
├── LICENSE              # MIT
└── README.md
```

**Runtime dependencies** (pinned in `requirements.txt`):

| Package | Role |
|---------|------|
| `anthropic` | Claude API client — tool-use and completions |
| `fastapi` + `uvicorn` | HTTP server for the `/research` endpoint |
| `playwright` | Headless Chromium for page fetching |
| `streamlit` | Optional browser UI |
| `httpx` | Async HTTP client used by tools |
| `beautifulsoup4` | HTML parsing and text extraction |
| `python-multipart` | FastAPI form-data support |

## Running tests

```bash
# Unit tests only (no network or browser required)
pytest -x -m "not integration" tests/

# All tests including integration (requires: playwright install chromium)
pytest -x tests/
```

## Roadmap

- ~~**M1** — repo scaffold: `src/` layout, `requirements.txt`, `.gitignore`, MIT license, README~~ done
- ~~**M2** — implement `web_search` (DuckDuckGo) and `fetch_page` (Playwright); smoke tests~~ done
- **M3** — implement the ReAct agent loop with citation accumulation
- **M4** — wire tools into the FastAPI endpoint; add `/research` POST handler
- **M5** — Streamlit front-end with streaming output
- **M6** — integration tests, Docker image, polished Quickstart

<!-- TODO: link GitHub Issues or a project board here once set up -->

## License

MIT © 2026 Ritik
