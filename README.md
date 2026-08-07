# AutoResearch Agent

> A local AI agent that takes a research question, browses the web autonomously, and produces a cited markdown report.

<!-- TODO: replace with a 5-10 second demo gif. Record with ScreenToGif on
     Windows or peek on macOS. Save to docs/demo.gif and update path here. -->
![demo](docs/demo.gif)

## What it is

AutoResearch Agent accepts a plain-English research question and returns a structured Markdown report with numbered citations. It orchestrates Claude claude-sonnet-4-6 through a ReAct-style tool-use loop: the model decides when to search the web, which pages to fetch, and when it has gathered enough evidence to synthesise an answer. All page fetching goes through a headless Playwright browser, so JavaScript-rendered content is handled without extra configuration.

The entire agent loop — plan, search, fetch, extract, synthesise — is roughly 500 lines of Python with no framework dependencies beyond the Anthropic SDK. DuckDuckGo HTML search is used for zero-cost web access; no API keys beyond `ANTHROPIC_API_KEY` are required.

## Quickstart

```bash
git clone https://github.com/RitikPatill/autoresearch-agent.git
cd autoresearch-agent

# Install Python dependencies and the headless browser
pip install -r requirements.txt
playwright install chromium

# Provide your Anthropic key
export ANTHROPIC_API_KEY=sk-ant-...

# Run a query from the CLI
python -m src.agent "What is the state of nuclear fusion in 2026?"
```

The report is written to `reports/<slug>.md`.

## Usage

**CLI** — the primary interface:

```bash
python -m src.agent "Your research question here" --depth 3
```

`--depth` controls the maximum number of pages the agent will visit (default: 3).

**API** — start the FastAPI server, then POST a query:

```bash
uvicorn src.api:app --reload

curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is nuclear fusion?", "depth": 2}'

# Stream live agent steps via SSE
curl -N "http://localhost:8000/research/stream?query=nuclear+fusion&depth=2"
```

**Streamlit UI** — visual interface with a live step log and final report panel:

```bash
uvicorn src.api:app --reload   # terminal 1
streamlit run app.py           # terminal 2
```

Open `http://localhost:8501`, enter a question, and watch the agent work in real time.

## Architecture

```
CLI / Streamlit UI
      │
      ▼
 FastAPI /research
      │
      ▼
  AgentLoop (ReAct)
  ├── tool: web_search   (DuckDuckGo scrape, no API key)
  ├── tool: fetch_page   (Playwright → cleaned text)
  ├── tool: extract_facts (LLM sub-call)
  └── tool: finish_report (writes Markdown)
      │
      ▼
  reports/<slug>.md
```

All LLM calls go through the Anthropic Python SDK. The loop runs until the model calls `finish_report` or the depth limit is reached.

## Project structure

```
autoresearch-agent/
├── app.py               # Streamlit UI (query input, live SSE log, report panel)
├── demo.tape            # VHS tape — run `vhs demo.tape` to regenerate demo.gif
├── src/
│   ├── agent.py         # ReAct agent loop, tool schemas, CLI entry point
│   ├── tools.py         # web_search, fetch_page, extract_facts, finish_report
│   └── api.py           # FastAPI /research + /research/stream endpoints
├── tests/
│   ├── test_tools.py    # smoke tests for web_search and fetch_page
│   ├── test_agent.py    # unit tests for AgentLoop, extract_facts, finish_report
│   ├── test_api.py      # unit tests for FastAPI endpoints (mocked agent)
│   └── test_app.py      # smoke test for the Streamlit helper functions
├── reports/             # generated Markdown reports (git-ignored)
├── requirements.txt     # pinned runtime and test dependencies
├── pytest.ini           # asyncio_mode=auto, integration marker
└── LICENSE              # MIT
```

Run unit tests (no network or browser required):

```bash
pytest -x -m "not integration" tests/
```

## Roadmap

- [ ] PDF and local file ingestion as additional source types
- [ ] Persistent memory across sessions via a lightweight vector store
- [ ] Support for local models (Ollama) as a drop-in alternative to the Anthropic SDK
- [ ] Parallel page fetching to reduce wall-clock time on deep queries
- [ ] Structured JSON output mode alongside the Markdown report

## License

MIT — see LICENSE.

---

Built autonomously by [autodev](https://github.com/RitikPatill/autodev),
a multi-agent orchestrator I designed. Each commit in this repo was
authored by me; the implementation work was performed by Sonnet under
the orchestrator's control. Read the orchestrator's README to see how.
