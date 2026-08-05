"""Browser and search tools — implemented in M2."""

# NOTE: After `pip install playwright`, run `playwright install chromium` to
# download the Chromium binary required by fetch_page.

import re
import urllib.parse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# DDG HTML class names have been stable for years but could change without
# notice. If web_search returns [] unexpectedly, inspect the raw HTML first.
_DDG_URL = "https://html.duckduckgo.com/html/"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Scrape DuckDuckGo HTML search results.

    Returns a list of dicts with keys: title, url, snippet.
    Returns [] on any HTTP or parse error — never raises.
    """
    params = urllib.parse.urlencode({"q": query})
    url = f"{_DDG_URL}?{params}"
    headers = {"User-Agent": _USER_AGENT}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
    except Exception:
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
        results: list[dict] = []
        for div in soup.find_all("div", class_="result"):
            a_title = div.find("a", class_="result__a")
            a_snippet = div.find("a", class_="result__snippet")
            if not a_title:
                continue
            title = a_title.get_text(strip=True)
            href = a_title.get("href", "")
            snippet = a_snippet.get_text(strip=True) if a_snippet else ""
            results.append({"title": title, "url": href, "snippet": snippet})
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


async def fetch_page(url: str) -> str:
    """Fetch a URL with headless Chromium and return cleaned body text ≤ 4000 chars.

    Returns "" on any error — never raises.
    """
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            text = await page.inner_text("body")
            text = re.sub(r"\s+", " ", text).strip()
            return text[:4000]
    except Exception:
        return ""
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass


import asyncio
import json
import os
import re as _re
import time

import anthropic as _anthropic


async def extract_facts(text: str, question: str) -> list[str]:
    """Extract bullet-point facts relevant to *question* from *text*.

    Makes a sub-call to claude-haiku-4-5-20251001 and parses lines starting
    with "- ".  Returns [] on any error — never raises.
    """
    try:
        client = _anthropic.AsyncAnthropic()
        prompt = (
            f"Research question: {question}\n\n"
            f"Page text:\n{text}\n\n"
            "Extract the most relevant facts from the page text that help answer "
            "the research question. Return ONLY bullet points, one per line, "
            'each starting with "- ". Be concise.'
        )
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text if response.content else ""
        facts = [line[2:].strip() for line in raw.splitlines() if line.startswith("- ")]
        return facts
    except Exception:
        return []


def finish_report(
    question: str,
    summary: str,
    sections: list[dict],
    citations: list[str],
) -> str:
    """Assemble and save a Markdown research report.

    Writes to reports/<slug>-<timestamp>.md (creates dir if absent).
    Returns the full Markdown string.
    """
    timestamp = time.strftime("%Y-%m-%dT%H-%M-%S")
    slug = _re.sub(r"[^\w]+", "-", question.lower())[:60].strip("-")
    filename = f"reports/{slug}-{timestamp}.md"

    lines: list[str] = []
    lines.append(f"# {question}\n")
    lines.append(f"*Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n")
    lines.append("## Summary\n")
    lines.append(f"{summary}\n")
    for section in sections:
        lines.append(f"## {section['heading']}\n")
        lines.append(f"{section['body']}\n")
    if citations:
        lines.append("## References\n")
        for i, url in enumerate(citations, 1):
            lines.append(f"{i}. {url}")

    report_md = "\n".join(lines)

    os.makedirs("reports", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(report_md)

    return report_md
