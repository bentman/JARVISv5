from pathlib import Path

from backend.search.extract import extract_text_from_html


FIXTURE_DIR = Path("tests/fixtures/fetch")


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_extract_simple_article_returns_expected_text_and_title() -> None:
    html = _read_fixture("article_simple.html")
    result = extract_text_from_html(html, max_chars=8000)

    assert result["ok"] is True
    assert result["code"] == "ok"
    assert result["title"] == "Simple Article"
    assert "deterministic article body" in result["text"]
    assert "stable assertions" in result["text"]


def test_extract_nav_heavy_page_keeps_meaningful_body_text() -> None:
    html = _read_fixture("article_with_nav.html")
    result = extract_text_from_html(html, max_chars=8000)

    assert result["ok"] is True
    assert result["code"] == "ok"
    assert "Main Story" in result["text"]
    assert "meaningful body text" in result["text"]
    assert "ignore me" not in result["text"]


def test_extract_empty_input_returns_empty_input_code() -> None:
    result = extract_text_from_html("   ", max_chars=8000)

    assert result["ok"] is False
    assert result["code"] == "empty_input"
    assert result["text"] == ""
    assert result["title"] is None


def test_extract_malformed_html_is_fail_safe() -> None:
    html = _read_fixture("malformed.html")
    result = extract_text_from_html(html, max_chars=8000)

    assert result["code"] in {"ok", "extraction_error"}
    if result["ok"]:
        assert len(result["text"]) > 0
    else:
        assert result["code"] == "extraction_error"


def test_extract_truncation_and_normalization_are_deterministic() -> None:
    html = _read_fixture("article_simple.html")
    result = extract_text_from_html(html, max_chars=64)

    assert result["ok"] is True
    assert result["code"] == "ok"
    assert len(result["text"]) <= 64
    assert "\r" not in result["text"]
    assert "  " not in result["text"]
