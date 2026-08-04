"""Smoke tests for src/tools.py (M2)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools import web_search, fetch_page

# ---------------------------------------------------------------------------
# Fake DuckDuckGo HTML with one result div
# ---------------------------------------------------------------------------
_FAKE_DDG_HTML = """
<html><body>
  <div class="result">
    <a class="result__a" href="https://example.com/page">Example Title</a>
    <a class="result__snippet">This is a snippet about the result.</a>
  </div>
</body></html>
"""


# ---------------------------------------------------------------------------
# Unit test: web_search — mocked HTTP
# ---------------------------------------------------------------------------
async def test_web_search_returns_list():
    """web_search parses a fake DDG response and returns list[dict] with correct keys."""
    mock_response = MagicMock()
    mock_response.text = _FAKE_DDG_HTML
    mock_response.raise_for_status = MagicMock()

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        results = await web_search("test query")

    assert isinstance(results, list), "web_search must return a list"
    assert len(results) == 1
    item = results[0]
    assert "title" in item, "each result must have 'title'"
    assert "url" in item, "each result must have 'url'"
    assert "snippet" in item, "each result must have 'snippet'"
    assert item["title"] == "Example Title"
    assert item["url"] == "https://example.com/page"


# ---------------------------------------------------------------------------
# Integration test: fetch_page — real Playwright + network
# Requires: playwright install chromium
# Run with: pytest -x tests/  (skip with: pytest -m "not integration")
# ---------------------------------------------------------------------------
@pytest.mark.integration
async def test_fetch_page_truncates():
    """fetch_page returns a str of length <= 4000 for a live URL."""
    result = await fetch_page("https://example.com")
    assert isinstance(result, str), "fetch_page must return a str"
    assert len(result) <= 4000, f"result too long: {len(result)} chars"
