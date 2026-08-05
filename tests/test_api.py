"""Tests for src/api.py — M4 FastAPI backend."""

import json

import httpx
import pytest

from src.api import app

FIXTURE_REPORT = (
    "# What is fusion?\n\n"
    "Fusion is a promising energy source.\n\n"
    "## Background\n\n"
    "Nuclear fusion [1] combines light nuclei.\n\n"
    "## References\n\n"
    "[1] https://example.com/fusion\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_research_success(mocker):
    """POST /research returns 200 with report_md, citations, and elapsed_s."""
    mocker.patch("src.api.AgentLoop.run", return_value=FIXTURE_REPORT)

    async with _async_client() as client:
        resp = await client.post("/research", json={"query": "What is fusion?", "depth": 1})

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_md"] == FIXTURE_REPORT
    assert body["citations"] == ["https://example.com/fusion"]
    assert isinstance(body["elapsed_s"], float)


@pytest.mark.asyncio
async def test_post_research_error(mocker):
    """POST /research returns 500 with detail when AgentLoop.run raises."""
    mocker.patch("src.api.AgentLoop.run", side_effect=RuntimeError("boom"))

    async with _async_client() as client:
        resp = await client.post("/research", json={"query": "broken query", "depth": 1})

    assert resp.status_code == 500
    assert "boom" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_stream_emits_done(mocker):
    """GET /research/stream SSE body contains a 'done' event with report_md."""
    mocker.patch("src.api.StreamingAgentLoop.run", return_value=FIXTURE_REPORT)

    async with _async_client() as client:
        async with client.stream("GET", "/research/stream?query=test&depth=1") as resp:
            assert resp.status_code == 200
            body = await resp.aread()

    text = body.decode()
    # Find the done event line
    done_events = [
        line[len("data: "):].strip()
        for line in text.splitlines()
        if line.startswith("data: ")
    ]
    done_payloads = [json.loads(e) for e in done_events]
    done = next((p for p in done_payloads if p.get("type") == "done"), None)
    assert done is not None, f"No 'done' event found in SSE body:\n{text}"
    assert done["report_md"] == FIXTURE_REPORT
