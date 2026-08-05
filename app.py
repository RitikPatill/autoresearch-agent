"""Streamlit demo UI for AutoResearch Agent — M5."""

import json
import os

import httpx
import streamlit as st

API_BASE = os.environ.get("AUTORESEARCH_API", "http://localhost:8000")

st.set_page_config(page_title="AutoResearch Agent", layout="wide")


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n] + "…"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("AutoResearch Agent")
    st.markdown("Powered by Claude + Playwright")
    depth = st.slider("Pages to visit (depth)", min_value=1, max_value=5, value=3)
    st.info(f"API: `uvicorn src.api:app --reload`\n\nConnecting to: `{API_BASE}`")

# ---------------------------------------------------------------------------
# Main area — Phase 1: query input
# ---------------------------------------------------------------------------

st.title("AutoResearch Agent")
st.markdown("Enter a research question and watch the agent work in real time.")

query = st.text_input(
    "Research question",
    placeholder="e.g. What is the state of nuclear fusion in 2026?",
)
run_btn = st.button("Research", type="primary")

# ---------------------------------------------------------------------------
# Main area — Phase 2: live run
# ---------------------------------------------------------------------------

if run_btn and query.strip():
    col_log, col_report = st.columns([1, 1])

    with col_log:
        st.subheader("Agent steps")
        log_placeholder = st.empty()

    with col_report:
        st.subheader("Report")
        report_placeholder = st.empty()
        report_placeholder.info("Waiting for agent to finish…")

    log_lines: list[str] = []
    report_md: str = ""

    try:
        with httpx.Client(timeout=None) as client:
            with client.stream(
                "GET",
                f"{API_BASE}/research/stream",
                params={"query": query.strip(), "depth": depth},
            ) as resp:
                for raw_line in resp.iter_lines():
                    if not raw_line.startswith("data: "):
                        continue
                    event = json.loads(raw_line[6:])

                    if event["type"] == "tool_call":
                        log_lines.append(
                            f"🔧 **{event['tool']}** `{_truncate(json.dumps(event['input']), 80)}`"
                        )
                    elif event["type"] == "tool_result":
                        log_lines.append(f"   ↳ {_truncate(event['preview'], 70)}")
                    elif event["type"] == "error":
                        with col_log:
                            st.error(event["message"])
                        break
                    elif event["type"] == "done":
                        report_md = event["report_md"]

                    log_placeholder.markdown("\n\n".join(log_lines))

    except httpx.ConnectError:
        st.error(
            f"Cannot reach API at `{API_BASE}`. "
            "Start it with: `uvicorn src.api:app --reload`"
        )
        st.stop()

    # Render final report
    if report_md:
        with col_report:
            report_placeholder.empty()
            st.markdown(report_md)
            filename = query.strip()[:40].replace(" ", "_").lower() + ".md"
            st.download_button(
                label="Download report",
                data=report_md,
                file_name=filename,
                mime="text/markdown",
            )
    else:
        with col_report:
            report_placeholder.warning("No report received.")
