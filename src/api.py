"""FastAPI backend — implemented in M4."""

import asyncio
import json
import re
import time
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent import AgentLoop

app = FastAPI(title="AutoResearch Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ResearchRequest(BaseModel):
    query: str
    depth: int = 3


class ResearchResponse(BaseModel):
    report_md: str
    citations: list[str]
    elapsed_s: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_citations(report_md: str) -> list[str]:
    """Return URLs from numbered citation lines like `[1] https://...`."""
    return re.findall(r"^\[\d+\]\s+(https?://\S+)", report_md, re.MULTILINE)


# ---------------------------------------------------------------------------
# Streaming subclass
# ---------------------------------------------------------------------------


class StreamingAgentLoop(AgentLoop):
    """AgentLoop that emits SSE events onto an asyncio.Queue during _dispatch."""

    def __init__(self, question: str, depth: int, queue: asyncio.Queue) -> None:
        super().__init__(question=question, depth=depth)
        self._queue = queue

    async def _dispatch(self, block) -> tuple[str, bool]:
        await self._queue.put(
            json.dumps({"type": "tool_call", "tool": block.name, "input": block.input})
        )
        result_str, is_finish = await super()._dispatch(block)
        await self._queue.put(
            json.dumps(
                {
                    "type": "tool_result",
                    "tool": block.name,
                    "preview": result_str[:200],
                }
            )
        )
        return result_str, is_finish


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/research", response_model=ResearchResponse)
async def post_research(req: ResearchRequest) -> ResearchResponse:
    t0 = time.monotonic()
    try:
        loop = AgentLoop(question=req.query, depth=req.depth)
        report_md = await loop.run()
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(exc))

    return ResearchResponse(
        report_md=report_md,
        citations=_extract_citations(report_md),
        elapsed_s=round(time.monotonic() - t0, 2),
    )


@app.get("/research/stream")
async def stream_research(query: str, depth: int = 3) -> StreamingResponse:
    queue: asyncio.Queue = asyncio.Queue()

    async def generator() -> AsyncGenerator[str, None]:
        loop = StreamingAgentLoop(question=query, depth=depth, queue=queue)
        task = asyncio.create_task(loop.run())

        try:
            while True:
                # Drain queued events; stop when task is done and queue empty
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    if task.done():
                        break

            # Flush any remaining items enqueued during the last iteration
            while not queue.empty():
                event = queue.get_nowait()
                yield f"data: {event}\n\n"

            report_md = await task
            yield f"data: {json.dumps({'type': 'done', 'report_md': report_md})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            if not task.done():
                task.cancel()

    return StreamingResponse(generator(), media_type="text/event-stream")
