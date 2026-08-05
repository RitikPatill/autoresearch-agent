"""ReAct agent loop — implemented in M3."""

import asyncio
import json
import sys

import anthropic

from src.tools import extract_facts, fetch_page, finish_report, web_search

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

SYSTEM_PROMPT = """You are an expert research assistant. Your job is to answer a research question thoroughly by using the tools available to you.

Follow this process:
1. Start with web_search to find relevant pages for the research question.
2. Use fetch_page on the most promising URLs from the search results.
3. Use extract_facts on each fetched page to pull out relevant information.
4. Repeat searching and fetching until you have enough evidence (aim for up to the configured number of pages).
5. Call finish_report exactly once with a well-structured report and all source URLs as citations.

When writing sections, use [1], [2], etc. citation markers in the body text that correspond to the index in the citations list (1-based).
Be thorough but concise. Cite every factual claim."""

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "web_search",
        "description": "Search DuckDuckGo. Returns [{title, url, snippet}, ...].",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": "Fetch a URL with a headless browser. Returns cleaned text <= 4000 chars.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "extract_facts",
        "description": "Extract bullet-point facts relevant to the research question from page text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "question": {"type": "string"},
            },
            "required": ["text", "question"],
        },
    },
    {
        "name": "finish_report",
        "description": "Synthesize all evidence into a final report and save it. Call this when done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "summary": {
                    "type": "string",
                    "description": "2-3 sentence executive summary",
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string"},
                            "body": {"type": "string"},
                        },
                        "required": ["heading", "body"],
                    },
                },
                "citations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URLs of sources used",
                },
            },
            "required": ["question", "summary", "sections", "citations"],
        },
    },
]


class AgentLoop:
    def __init__(self, question: str, depth: int = 3) -> None:
        self.question = question
        self.depth = depth
        self.max_iterations = depth * 5
        self.client = anthropic.AsyncAnthropic()
        self.messages: list[dict] = []

    async def run(self) -> str:
        """Run the ReAct loop. Returns the final report markdown (or a fallback string)."""
        self.messages = [{"role": "user", "content": self.question}]

        for _ in range(self.max_iterations):
            response = await self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=self.messages,
            )

            self.messages.append({"role": "assistant", "content": response.content})

            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_blocks:
                # Claude returned a plain text answer — extract and return it
                text_blocks = [b for b in response.content if b.type == "text"]
                return text_blocks[0].text if text_blocks else ""

            # Dispatch all tool calls and collect results
            tool_results = []
            finished_report: str | None = None

            for block in tool_blocks:
                result_str, is_finish = await self._dispatch(block)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    }
                )
                if is_finish:
                    finished_report = result_str

            # All results in a single user message (required by Anthropic API)
            self.messages.append({"role": "user", "content": tool_results})

            if finished_report is not None:
                return finished_report

        return (
            f"Max iterations ({self.max_iterations}) reached without a final report. "
            "Consider increasing --depth or refining the question."
        )

    async def _dispatch(self, block) -> tuple[str, bool]:
        """Route a tool_use block to the correct implementation.

        Returns (result_string, is_finish).
        """
        name = block.name
        inp: dict = block.input

        if name == "web_search":
            results = await web_search(
                query=inp["query"],
                max_results=inp.get("max_results", 5),
            )
            return json.dumps(results), False

        if name == "fetch_page":
            text = await fetch_page(url=inp["url"])
            return text or "(empty page)", False

        if name == "extract_facts":
            facts = await extract_facts(text=inp["text"], question=inp["question"])
            return json.dumps(facts), False

        if name == "finish_report":
            report_md = finish_report(
                question=inp["question"],
                summary=inp["summary"],
                sections=inp["sections"],
                citations=inp["citations"],
            )
            return report_md, True

        return f"Unknown tool: {name}", False


async def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m src.agent <question> [--depth N]")
        sys.exit(1)

    depth = 3
    if "--depth" in args:
        i = args.index("--depth")
        depth = int(args[i + 1])
        args = args[:i] + args[i + 2:]

    question = " ".join(args)
    loop = AgentLoop(question=question, depth=depth)
    report = await loop.run()
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
