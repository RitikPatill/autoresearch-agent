# AGENTS.md — Tool schema reference

> **Note:** This file is kept in sync with `TOOL_SCHEMAS` in `src/agent.py`. If you add a tool, update both.

---

## Overview

AutoResearch Agent runs a ReAct (Reason + Act) loop driven by Claude claude-sonnet-4-6 via Anthropic's tool-use API. On each iteration Claude either calls one or more tools or returns a plain-text answer. The loop continues until `finish_report` is called or `depth * 5` iterations are exhausted.

All tool functions live in `src/tools.py`. Their JSON schemas (consumed by the Anthropic API) are declared in `TOOL_SCHEMAS` in `src/agent.py` (lines 26–91).

---

## Tool schemas

### `web_search`

Search DuckDuckGo for a query. Uses DuckDuckGo HTML scraping — no API key required.

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "query": { "type": "string" },
    "max_results": { "type": "integer", "default": 5 }
  },
  "required": ["query"]
}
```

**Returns:** `list[{title: str, url: str, snippet: str}]` serialised as JSON.

**Example return value:**

```json
[
  {
    "title": "Nuclear Fusion Milestone — DOE",
    "url": "https://www.energy.gov/science/nif-achieves-fusion-ignition",
    "snippet": "The National Ignition Facility achieved fusion ignition in December 2022 ..."
  }
]
```

---

### `fetch_page`

Fetch a URL with a headless Playwright browser. Renders JavaScript before extracting text, making it suitable for modern SPAs. Returns cleaned, de-tagged text truncated to 4 000 characters to stay within context budgets.

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "url": { "type": "string" }
  },
  "required": ["url"]
}
```

**Returns:** `str` — cleaned page text, at most 4 000 characters. Returns `"(empty page)"` if the page yields no extractable text.

---

### `extract_facts`

Make a secondary LLM call (claude-haiku-4-5) to distil the most relevant facts from a page's text given the research question. Keeps the main agent context lean by summarising before appending.

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "text": { "type": "string" },
    "question": { "type": "string" }
  },
  "required": ["text", "question"]
}
```

**Returns:** `list[str]` — bullet-point facts serialised as a JSON array.

**Example return value:**

```json
[
  "NIF achieved net energy gain for the first time in December 2022.",
  "Commonwealth Fusion Systems aims to demonstrate net energy with SPARC by 2025.",
  "Private fusion investment exceeded $6 billion globally in 2023."
]
```

---

### `finish_report`

Synthesise all gathered evidence into a final structured Markdown report. Saves the report to `reports/<slug>-<timestamp>.md` and returns the full Markdown string. **This tool must be called exactly once and ends the agent loop.**

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "question": { "type": "string" },
    "summary": {
      "type": "string",
      "description": "2-3 sentence executive summary"
    },
    "sections": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "heading": { "type": "string" },
          "body": { "type": "string" }
        },
        "required": ["heading", "body"]
      }
    },
    "citations": {
      "type": "array",
      "items": { "type": "string" },
      "description": "URLs of sources used"
    }
  },
  "required": ["question", "summary", "sections", "citations"]
}
```

**Returns:** `str` — the full Markdown report. Also writes `reports/<slug>-<timestamp>.md` to disk as a side-effect.

---

## ReAct loop sequence

The typical call sequence for a well-formed research run:

1. **User message** — Claude receives the raw research question as the first user message.
2. **`web_search`** — Claude calls `web_search` with a focused query. The tool returns a ranked list of `{title, url, snippet}` objects.
3. **`fetch_page`** — Claude calls `fetch_page` on the most promising URLs (usually 1–3 per search). Each call returns cleaned page text.
4. **`extract_facts`** — Claude calls `extract_facts` on each fetched page text, passing the original question so the sub-LLM can filter for relevance. Returns bullet-point facts.
5. **Repeat** — Claude may issue further `web_search` / `fetch_page` / `extract_facts` calls until it has visited up to `depth` pages total.
6. **`finish_report`** — Claude calls `finish_report` exactly once with the question, a summary, structured sections (each with inline `[N]` citation markers), and the full list of source URLs. The loop exits and the report is returned to the caller.

The maximum number of loop iterations is `depth * 5`. If `finish_report` is not called within that budget, the agent returns an error string suggesting the user increase `--depth` or refine the question.
