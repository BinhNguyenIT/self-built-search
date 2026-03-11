from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from urllib.request import Request, urlopen

from searchstack.models import FetchedDocument
from searchstack.utils import normalize_url


def _clean_text(value: str) -> str:
    return " ".join(unescape(value).split())


def _truncate(value: str, limit: int = 280) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


@dataclass
class _HTMLExtractionState:
    title_parts: list[str] = field(default_factory=list)
    heading_parts: list[str] = field(default_factory=list)
    body_parts: list[str] = field(default_factory=list)
    meta_description: str = ""


class HTMLContentExtractor(HTMLParser):
    _SKIP_TAGS = {"script", "style", "noscript", "svg"}
    _BLOCK_TAGS = {
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "p",
        "section",
        "tr",
        "ul",
        "ol",
    }
    _BOILERPLATE_TAGS = {"footer", "form", "header", "nav"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._state = _HTMLExtractionState()
        self._skip_depth = 0
        self._in_title = False
        self._in_heading = False
        self._in_body = False
        self._boilerplate_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)

        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return

        if self._in_body and tag in self._BOILERPLATE_TAGS:
            self._boilerplate_depth += 1
            return

        if tag == "title":
            self._in_title = True
            return

        if tag == "h1":
            self._in_heading = True

        if tag == "body":
            self._in_body = True
            return

        if tag == "meta":
            name = (attr_map.get("name") or attr_map.get("property") or "").lower()
            if name in {"description", "og:description"} and attr_map.get("content"):
                self._state.meta_description = _clean_text(attr_map["content"])
            return

        if self._in_body and tag in self._BLOCK_TAGS:
            self._state.body_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return

        if tag in self._BOILERPLATE_TAGS and self._boilerplate_depth:
            self._boilerplate_depth -= 1
            return

        if tag == "title":
            self._in_title = False
            return

        if tag == "h1":
            self._in_heading = False

        if tag == "body":
            self._in_body = False
            return

        if self._in_body and tag in self._BLOCK_TAGS:
            self._state.body_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._boilerplate_depth:
            return

        if self._in_title:
            self._state.title_parts.append(data)
            return

        if self._in_heading:
            self._state.heading_parts.append(data)

        if self._in_body:
            self._state.body_parts.append(data)

    def extract(
        self,
        html: str,
        url: str,
        status_code: int,
        final_url: str | None = None,
    ) -> FetchedDocument:
        self.feed(html)
        title = _clean_text("".join(self._state.title_parts))
        if not title:
            title = _clean_text("".join(self._state.heading_parts))
        content = _clean_text(" ".join(self._state.body_parts))
        excerpt_source = self._state.meta_description or content
        excerpt = _truncate(excerpt_source)
        return FetchedDocument(
            url=normalize_url(url),
            final_url=normalize_url(final_url or url),
            title=title,
            excerpt=excerpt,
            content=content,
            status_code=status_code,
            content_type="text/html",
        )


class URLFetchAdapter:
    user_agent = "searchstack/0.1 (+https://example.invalid/local-first-search)"

    def fetch(self, url: str) -> FetchedDocument:
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=10) as response:
            status_code = getattr(response, "status", response.getcode())
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="ignore")
            final_url = normalize_url(getattr(response, "url", url))

        if content_type == "text/html":
            extractor = HTMLContentExtractor()
            return extractor.extract(
                body,
                url=url,
                status_code=status_code,
                final_url=final_url,
            )

        cleaned = _clean_text(body)
        return FetchedDocument(
            url=normalize_url(url),
            final_url=final_url,
            title="",
            excerpt=_truncate(cleaned),
            content=cleaned,
            status_code=status_code,
            content_type=content_type,
        )
