from __future__ import annotations

from html.parser import HTMLParser
from typing import Any

from backend.search.fetch_models import ExtractionResult


class _StdlibTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._ignore_depth = 0
        self._title_active = False
        self._title_parts: list[str] = []
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        if tag_name in {"script", "style"}:
            self._ignore_depth += 1
        elif tag_name == "title":
            self._title_active = True

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name in {"script", "style"} and self._ignore_depth > 0:
            self._ignore_depth -= 1
        elif tag_name == "title":
            self._title_active = False

    def handle_data(self, data: str) -> None:
        if self._ignore_depth > 0:
            return
        if self._title_active:
            self._title_parts.append(data)
        self._parts.append(data)

    def get_text_and_title(self) -> tuple[str, str | None]:
        text = "\n".join(self._parts)
        title = "".join(self._title_parts).strip() or None
        return text, title


def _normalize_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in normalized.split("\n"):
        compact = " ".join(line.split())
        if compact:
            lines.append(compact)
    return "\n".join(lines).strip()


def _extract_with_trafilatura(html: str) -> tuple[str, str | None] | None:
    try:
        import trafilatura  # type: ignore
    except Exception:
        return None

    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
    )
    if not extracted:
        return None

    title = None
    try:
        metadata = trafilatura.extract_metadata(html)
        if metadata is not None:
            title = getattr(metadata, "title", None) or None
    except Exception:
        title = None
    return extracted, title


def _extract_with_bs4(html: str) -> tuple[str, str | None] | None:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        return None

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    text = soup.get_text("\n")
    return text, title


def _extract_with_stdlib(html: str) -> tuple[str, str | None]:
    parser = _StdlibTextExtractor()
    parser.feed(html)
    parser.close()
    return parser.get_text_and_title()


def _result(ok: bool, code: str, text: str, title: str | None, meta: dict[str, Any]) -> dict:
    return ExtractionResult(ok=ok, code=code, text=text, title=title, meta=meta).model_dump()


def extract_text_from_html(html: str, *, max_chars: int = 8000) -> dict:
    if html is None or not str(html).strip():
        return _result(False, "empty_input", "", None, {})

    if max_chars <= 0:
        max_chars = 1

    extractors = (
        ("trafilatura", _extract_with_trafilatura),
        ("beautifulsoup", _extract_with_bs4),
        ("stdlib", lambda source: _extract_with_stdlib(source)),
    )

    try:
        for name, extractor in extractors:
            extracted = extractor(html)
            if extracted is None:
                continue
            raw_text, title = extracted
            normalized = _normalize_text(raw_text)
            if not normalized:
                continue

            truncated = normalized[:max_chars]
            return _result(
                True,
                "ok",
                truncated,
                _normalize_text(title) if title else None,
                {
                    "extractor": name,
                    "truncated": len(normalized) > max_chars,
                    "max_chars": int(max_chars),
                },
            )

        return _result(False, "extraction_error", "", None, {"reason": "no text extracted"})
    except Exception:
        return _result(False, "extraction_error", "", None, {"reason": "extraction failed"})
