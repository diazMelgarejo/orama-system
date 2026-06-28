"""Tests for markdown_render.py."""
from orama_system.markdown_render import markdown_to_html


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
