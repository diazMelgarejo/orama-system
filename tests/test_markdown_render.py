"""Tests for platform/windows/markdown_render.py."""
from pathlib import Path
import importlib.util
import sys


def _load_markdown_render():
    win_dir = Path(__file__).resolve().parents[1] / "platform" / "windows"
    path = win_dir / "markdown_render.py"
    spec = importlib.util.spec_from_file_location("test_win_markdown_render", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    inserted = str(win_dir) not in sys.path
    if inserted:
        sys.path.insert(0, str(win_dir))
    try:
        spec.loader.exec_module(mod)
    finally:
        if inserted:
            sys.path.remove(str(win_dir))
    return mod


markdown_to_html = _load_markdown_render().markdown_to_html


def test_markdown_headers_and_code():
    html = markdown_to_html("# Title\n\n**bold** and `code`\n\n```py\nx = 1\n```")
    assert "<h1>Title</h1>" in html
    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    assert "<pre><code>x = 1</code></pre>" in html


def test_markdown_escapes_html_injection():
    html = markdown_to_html("<script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
