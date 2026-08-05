# AutoResearch Agent

> A minimal, locally-runnable AI research agent that turns a natural-language question into a cited Markdown report.

**Status: M5 complete — Streamlit demo UI with live SSE step log and Markdown report panel.**

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
| M3 | `agent.py` — ReAct loop with citation tracking | **done** |
| M4 | `api.py` — FastAPI `/research` endpoint + SSE stream | **done** |
| M5 | Streamlit UI (`app.py`) with live SSE log + Markdown report | **done** |
| M6 | End-to-end tests, Quickstart polish, Docker image | planned |

M1 delivers a runnable `pip install` baseline. M2 implements the two browser/search tools and their smoke tests. M3 adds the full ReAct agent loop: `extract_facts` (LLM sub-call), `finish_report` (Markdown writer), and `AgentLoop` (Claude tool-calling loop). M4 wraps the agent in a FastAPI backend with a synchronous `/research` POST endpoint and a `/research/stream` SSE endpoint for live step-by-step logs. M5 adds `app.py`, a single-page Streamlit UI: query input, depth slider, live agent-step log panel (consuming the SSE stream), and a final rendered Markdown report with a download button.

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

```bash
git clone <repo>
cd autoresearch-agent
pip install -r requirements.txt
playwright install chromium
export ANTHROPIC_API_KEY=sk-ant-...

# Run a research query via CLI
python -m src.agent "What is the state of nuclear fusion in 2026?"

# With custom depth (number of pages to visit)
python -m src.agent "What is quantum computing?" --depth 5

# Start the FastAPI backend (terminal 1)
uvicorn src.api:app --reload

# Start the Streamlit UI (terminal 2)
streamlit run app.py

# POST a research query via the API
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is nuclear fusion?", "depth": 2}'

# Stream live agent steps via SSE
curl -N "http://localhost:8000/research/stream?query=nuclear+fusion&depth=2"
```

The report is saved to `reports/<slug>-<timestamp>.md` and also printed to stdout.

## Project structure

```
autoresearch-agent/
├── app.py               # Streamlit UI (query input, live SSE log, report panel)
├── src/
│   ├── __init__.py      # makes src a Python package
│   ├── agent.py         # ReAct agent loop (AgentLoop, TOOL_SCHEMAS, CLI entry point)
│   ├── tools.py         # web_search, fetch_page, extract_facts, finish_report
│   └── api.py           # FastAPI /research + /research/stream endpoints
├── tests/
│   ├── __init__.py
│   ├── test_tools.py    # smoke tests for web_search and fetch_page
│   ├── test_agent.py    # unit tests for AgentLoop, extract_facts, finish_report
│   ├── test_api.py      # unit tests for FastAPI endpoints (mocked agent)
│   └── test_app.py      # smoke test for app.py (_truncate helper)
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
- ~~**M3** — implement the ReAct agent loop with citation accumulation~~ done
- ~~**M4** — FastAPI `/research` POST + `/research/stream` SSE endpoint~~ done
- ~~**M5** — Streamlit front-end with streaming output~~ done
- **M6** — integration tests, Docker image, polished Quickstart

<!-- TODO: link GitHub Issues or a project board here once set up -->

## License

MIT © 2026 Ritik
