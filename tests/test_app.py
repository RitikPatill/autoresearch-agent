"""Smoke-test: app.py imports cleanly and _truncate works correctly."""

import importlib.util
import pathlib
import sys
import types


def test_truncate_logic():
    # Patch streamlit before import so module-level st calls are no-ops
    fake_st = types.ModuleType("streamlit")
    for attr in (
        "set_page_config",
        "title",
        "sidebar",
        "columns",
        "text_input",
        "button",
        "slider",
        "empty",
        "subheader",
        "markdown",
        "download_button",
        "error",
        "spinner",
        "expander",
        "stop",
        "info",
        "warning",
    ):
        setattr(fake_st, attr, lambda *a, **kw: None)

    # sidebar needs to work as a context manager
    class _FakeCtx:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def __getattr__(self, name):
            return lambda *a, **kw: None

    fake_st.sidebar = _FakeCtx()
    fake_st.session_state = {}

    sys.modules["streamlit"] = fake_st

    spec = importlib.util.spec_from_file_location("app", pathlib.Path("app.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod._truncate("hello world", 5) == "hello…"
    assert mod._truncate("hi", 10) == "hi"
    assert mod._truncate("exactly5", 8) == "exactly5"
    assert mod._truncate("toolongstring", 7) == "toolong…"
