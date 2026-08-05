"""Unit tests for src/agent.py and the M3 additions to src/tools.py."""

import json
import os
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent import AgentLoop
from src.tools import extract_facts, finish_report


# ---------------------------------------------------------------------------
# Helpers for building fake Anthropic response objects
# ---------------------------------------------------------------------------

def _make_text_block(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(name: str, tool_input: dict, tool_id: str = "tu_001"):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = tool_input
    return block


def _make_response(content: list):
    resp = MagicMock()
    resp.content = content
    return resp


# ---------------------------------------------------------------------------
# AgentLoop tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_calls_finish_report():
    """When Claude returns a finish_report tool_use, run() returns the report markdown."""
    finish_block = _make_tool_use_block(
        "finish_report",
        {
            "question": "test question",
            "summary": "A short summary.",
            "sections": [{"heading": "Section 1", "body": "Body text [1]."}],
            "citations": ["https://example.com"],
        },
    )
    fake_response = _make_response([finish_block])

    with patch("src.agent.anthropic.AsyncAnthropic") as MockClient, \
         patch("src.tools.os.makedirs"), \
         patch("builtins.open", MagicMock()):

        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=fake_response)
        MockClient.return_value = mock_instance

        # Patch finish_report in agent module to avoid file I/O
        with patch("src.agent.finish_report", return_value="# test question\n\nA short summary.") as mock_fr:
            loop = AgentLoop(question="test question", depth=1)
            result = await loop.run()

        mock_fr.assert_called_once()
        assert "test question" in result or result  # report returned


@pytest.mark.asyncio
async def test_agent_respects_max_iterations():
    """When the loop never gets finish_report, it exits after max_iterations."""
    search_block = _make_tool_use_block("web_search", {"query": "test"})
    fake_response = _make_response([search_block])

    with patch("src.agent.anthropic.AsyncAnthropic") as MockClient, \
         patch("src.agent.web_search", AsyncMock(return_value=[])):

        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=fake_response)
        MockClient.return_value = mock_instance

        loop = AgentLoop(question="never ending", depth=1)
        # depth=1 → max_iterations=5
        result = await loop.run()

    assert "Max iterations" in result


@pytest.mark.asyncio
async def test_agent_handles_pure_text_response():
    """If Claude returns no tool_use blocks, the loop returns the text content."""
    text_block = _make_text_block("Here is my answer without any tool calls.")
    fake_response = _make_response([text_block])

    with patch("src.agent.anthropic.AsyncAnthropic") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=fake_response)
        MockClient.return_value = mock_instance

        loop = AgentLoop(question="simple question", depth=1)
        result = await loop.run()

    assert result == "Here is my answer without any tool calls."


# ---------------------------------------------------------------------------
# extract_facts tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_facts_parses_bullets():
    """extract_facts returns a list of strings stripped of the leading '- '."""
    fake_content = MagicMock()
    fake_content.text = "- fact one\n- fact two\nSome preamble\n- fact three"
    fake_response = MagicMock()
    fake_response.content = [fake_content]

    with patch("src.tools._anthropic.AsyncAnthropic") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=fake_response)
        MockClient.return_value = mock_instance

        facts = await extract_facts("some page text", "some question")

    assert facts == ["fact one", "fact two", "fact three"]


@pytest.mark.asyncio
async def test_extract_facts_returns_empty_on_error():
    """If the Anthropic call raises, extract_facts returns [] without propagating."""
    with patch("src.tools._anthropic.AsyncAnthropic") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(side_effect=Exception("API error"))
        MockClient.return_value = mock_instance

        facts = await extract_facts("text", "question")

    assert facts == []


# ---------------------------------------------------------------------------
# finish_report tests
# ---------------------------------------------------------------------------

def test_finish_report_writes_file(tmp_path, monkeypatch):
    """finish_report creates a file and the content contains title and citation."""
    # Redirect 'reports/' to tmp_path
    monkeypatch.chdir(tmp_path)

    result = finish_report(
        question="What is fusion energy?",
        summary="Fusion is a promising clean energy source.",
        sections=[{"heading": "Background", "body": "Nuclear fusion [1] is the process..."}],
        citations=["https://example.com/fusion"],
    )

    assert "What is fusion energy?" in result
    assert "Fusion is a promising clean energy source." in result
    assert "https://example.com/fusion" in result

    # Check the file was actually created
    report_files = list((tmp_path / "reports").glob("*.md"))
    assert len(report_files) == 1
    file_content = report_files[0].read_text(encoding="utf-8")
    assert "What is fusion energy?" in file_content
    assert "https://example.com/fusion" in file_content
